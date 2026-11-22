"""Orquestrador transacional do coletor com lock distribuído, deduplicação e loops."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .collectors import CollectorContext, get_collector_for_source
from .contracts import CollectorRunSummary
from .fetcher import SafeHttpFetcher, compress_artifact
from .guardrails import validate_observation
from .models import (
    AgroDataSource,
    AgroIngestionArtifact,
    AgroIngestionRun,
    AgroStagingObservation,
)
from .notifier import notify_collector_event
from .repository import AgroMarketRepository, purge_expired_artifacts
from .seed_sources import ensure_default_sources
from .sentinel import run_sentinel_discovery

_LOCAL_LOCKS: dict[str, asyncio.Lock] = {}
REDIS_EVENTS_CHANNEL = "agro:config:events"
LOCK_TTL_SEC = 600


def _local_lock_for(slug: str) -> asyncio.Lock:
    lock = _LOCAL_LOCKS.get(slug)
    if lock is None:
        lock = asyncio.Lock()
        _LOCAL_LOCKS[slug] = lock
    return lock


@asynccontextmanager
async def _distributed_lock(redis_client: Any | None, slug: str):
    key = f"agro:collector:lock:{slug}"
    token = uuid.uuid4().hex
    redis_acquired = False
    if redis_client is not None:
        try:
            redis_acquired = bool(
                await redis_client.set(key, token, nx=True, ex=LOCK_TTL_SEC)
            )
            if not redis_acquired:
                raise RuntimeError(f"Lock distribuído ativo para fonte '{slug}'.")
        except RuntimeError:
            raise
        except Exception as exc:
            logger.debug(f"[agro_collector] fallback para lock local em '{slug}': {exc}")

    local_lock = _local_lock_for(slug)
    async with local_lock:
        try:
            yield
        finally:
            if redis_acquired and redis_client is not None:
                try:
                    current = await redis_client.get(key)
                    if isinstance(current, bytes):
                        current = current.decode("utf-8", errors="ignore")
                    if current == token:
                        await redis_client.delete(key)
                except Exception:
                    logger.debug(f"[agro_collector] erro ao liberar lock redis '{key}'")


async def _publish_invalidation_event(redis_client: Any | None, slug: str, publicados: int) -> None:
    if publicados <= 0:
        return
    try:
        from public_mercado.precos_publicos_service import get_precos_service

        get_precos_service().invalidate_cache()
    except Exception:
        logger.debug("[agro_collector] erro ao invalidar cache L1 local")

    if redis_client is None:
        return
    try:
        payload = json.dumps(
            {
                "event": "agro_market_observations_updated",
                "source_slug": slug,
                "publicados": publicados,
                "at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            }
        )
        await redis_client.publish(REDIS_EVENTS_CHANNEL, payload)
    except Exception as exc:
        logger.debug(f"[agro_collector] falha best-effort no Pub/Sub Redis: {exc}")


async def _get_last_successful_run(
    session: AsyncSession,
    source_id: uuid.UUID,
) -> AgroIngestionRun | None:
    stmt = (
        select(AgroIngestionRun)
        .where(
            AgroIngestionRun.source_id == source_id,
            AgroIngestionRun.status.in_(["SUCESSO", "PARCIAL", "QUARENTENA"]),
        )
        .order_by(AgroIngestionRun.iniciado_em.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


class AgroCollectorOrchestrator:
    """Executa fontes homologadas respeitando compliance, deduplicação e quarentena."""

    def __init__(
        self,
        session_factory: Any,
        *,
        fetcher: SafeHttpFetcher | None = None,
        redis_client: Any | None = None,
        ia_callable: Callable[..., Awaitable[str]] | None = None,
        send_email_fn: Callable[[str, str, str], Awaitable[Any]] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.fetcher = fetcher or SafeHttpFetcher()
        self.redis_client = redis_client
        self.ia_callable = ia_callable
        self.send_email_fn = send_email_fn

    async def dry_run_source(
        self,
        source: AgroDataSource,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Executa coleta + guardrails sem gravar ou publicar dados no banco.

        Args:
            source: Instância de ``AgroDataSource`` a testar.
            session: Sessão somente leitura usada para consultar último preço ativo.

        Returns:
            Dicionário compatível com ``CollectorDryRunResponse``.

        Raises:
            ValueError: Se a fonte for ``LINK_HOMOLOGADO_APENAS``.
        """
        if source.tipo_licenca == "LINK_HOMOLOGADO_APENAS":
            raise ValueError(
                f"Fonte '{source.slug}' é LINK_HOMOLOGADO_APENAS e não permite coleta."
            )
        collector = get_collector_for_source(source)
        ctx = CollectorContext(
            source=source,
            fetcher=self.fetcher,
            ia_callable=self.ia_callable,
        )
        payload = await collector.collect(ctx)
        repo = AgroMarketRepository(session)
        itens_preview: list[dict[str, Any]] = []
        for raw in payload.observations:
            prev_val = await repo.obter_ultimo_valor(
                source.id, raw.commodity_id, raw.uf, raw.praca
            )
            validated = validate_observation(
                raw,
                previous_valor=prev_val,
                max_variacao_pct=source.max_variacao_pct,
                max_defasagem_dias=int(source.max_defasagem_dias),
                raw_text=payload.raw_text_for_evidence,
            )
            itens_preview.append(
                {
                    "commodity_id": raw.commodity_id,
                    "uf": raw.uf,
                    "praca": raw.praca,
                    "data_referencia": raw.data_referencia,
                    "valor_normalizado": validated.valor_normalizado,
                    "unidade_normalizada": validated.unidade_normalizada,
                    "trecho_evidencia": raw.trecho_evidencia,
                    "flags_anomalia": validated.flags_anomalia,
                    "bloqueado_para_publicacao": validated.bloqueado_para_publicacao,
                }
            )
        return {
            "source_slug": source.slug,
            "url_efetiva": payload.fetch_result.url_efetiva,
            "sha256_bruto": payload.fetch_result.sha256,
            "modelo_ia": payload.modelo_ia,
            "tokens_entrada": payload.tokens_entrada,
            "tokens_saida": payload.tokens_saida,
            "custo_estimado_usd": payload.custo_estimado_usd,
            "total_extraidos": len(itens_preview),
            "itens": itens_preview,
        }

    async def run_source_by_slug(
        self,
        slug: str,
        *,
        trigger_tipo: str = "AGENDADO",
        executado_por: str | None = "background-worker",
        force: bool = False,
    ) -> CollectorRunSummary:
        """Executa o ciclo completo de coleta, validação e publicação para uma fonte.

        Args:
            slug: Identificador da fonte em ``agro_data_sources``.
            trigger_tipo: ``AGENDADO``, ``MANUAL`` ou ``REPROCESSAMENTO``.
            executado_por: Identificação do iniciador para trilha forense.
            force: Quando ``True``, reprocessa mesmo se SHA-256 coincidir com run anterior.

        Returns:
            ``CollectorRunSummary`` com contadores e status final da execução.

        Raises:
            ValueError: Se a fonte não existir ou for ``LINK_HOMOLOGADO_APENAS``.
        """
        async with _distributed_lock(self.redis_client, slug):
            async with self.session_factory() as session:
                await ensure_default_sources(session)
                source = (
                    await session.execute(select(AgroDataSource).where(AgroDataSource.slug == slug))
                ).scalar_one_or_none()
                if source is None:
                    raise ValueError(f"Fonte '{slug}' não cadastrada em agro_data_sources.")
                if source.tipo_licenca == "LINK_HOMOLOGADO_APENAS":
                    raise ValueError(
                        f"Fonte '{slug}' é LINK_HOMOLOGADO_APENAS e não pode ser coletada."
                    )

                return await self._execute_locked(
                    session,
                    source,
                    trigger_tipo=trigger_tipo,
                    executado_por=executado_por,
                    force=force,
                )

    async def _handle_failure_sentinel_and_notify(
        self,
        session: AsyncSession,
        source: AgroDataSource,
        run: AgroIngestionRun,
        erro_resumo: str,
    ) -> dict[str, Any] | None:
        suggestion: dict[str, Any] | None = None
        if int(source.falhas_consecutivas) >= 3:
            try:
                suggestion = await run_sentinel_discovery(
                    source, self.fetcher, ia_callable=self.ia_callable
                )
            except Exception as sent_exc:
                logger.debug(f"[agro_collector] erro no Sentinela de '{source.slug}': {sent_exc}")
            run.sugestao_sentinela = suggestion
            await notify_collector_event(
                session=session,
                source=source,
                event_kind="FALHA_CONSECUTIVA",
                summary_lines=[
                    f"Falhas consecutivas: {source.falhas_consecutivas}",
                    f"Erro registrado: {erro_resumo}",
                ],
                redis_client=self.redis_client,
                send_email_fn=self.send_email_fn,
            )
            if suggestion:
                await notify_collector_event(
                    session=session,
                    source=source,
                    event_kind="SUGESTAO_SENTINELA",
                    summary_lines=[
                        f"Nova URL sugerida: {suggestion['url_sugerida']}",
                        f"Evidência: {suggestion['evidencia']}",
                    ],
                    redis_client=self.redis_client,
                    send_email_fn=self.send_email_fn,
                )
        return suggestion

    async def _execute_locked(
        self,
        session: AsyncSession,
        source: AgroDataSource,
        *,
        trigger_tipo: str,
        executado_por: str | None,
        force: bool,
    ) -> CollectorRunSummary:
        started_at = datetime.now(timezone.utc)  # noqa: UP017
        prev_run = await _get_last_successful_run(session, source.id)
        collector = get_collector_for_source(source)
        ctx = CollectorContext(
            source=source,
            fetcher=self.fetcher,
            last_etag=prev_run.etag if prev_run and not force else None,
            last_modified=prev_run.last_modified if prev_run and not force else None,
            ia_callable=self.ia_callable,
        )

        run = AgroIngestionRun(
            id=uuid.uuid4(),
            source_id=source.id,
            status="FALHA",
            trigger_tipo=trigger_tipo,
            executado_por=executado_por,
            iniciado_em=started_at,
        )
        session.add(run)

        try:
            payload = await collector.collect(ctx)
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)  # noqa: UP017
            run.status = "FALHA"
            run.erro_resumo = str(exc)[:1000]
            run.finalizado_em = finished_at
            source.ultima_execucao_em = finished_at
            source.falhas_consecutivas = int(source.falhas_consecutivas) + 1
            source.proximo_ciclo_em = finished_at + timedelta(
                seconds=int(source.cron_ou_intervalo_seg)
            )
            suggestion = await self._handle_failure_sentinel_and_notify(
                session, source, run, run.erro_resumo
            )
            await session.commit()
            return CollectorRunSummary(
                run_id=run.id,
                source_slug=source.slug,
                status="FALHA",
                erro_resumo=run.erro_resumo,
                sugestao_sentinela=suggestion,
            )

        fetch_res = payload.fetch_result
        run.url_efetiva = fetch_res.url_efetiva
        run.http_status = fetch_res.http_status
        run.etag = fetch_res.etag
        run.last_modified = fetch_res.last_modified
        run.sha256_bruto = fetch_res.sha256 or None
        run.tamanho_bytes = fetch_res.tamanho_bytes
        run.modelo_ia = payload.modelo_ia
        run.tokens_entrada = int(payload.tokens_entrada)
        run.tokens_saida = int(payload.tokens_saida)
        run.custo_estimado_usd = payload.custo_estimado_usd

        unchanged = fetch_res.not_modified or (
            not force
            and prev_run is not None
            and bool(fetch_res.sha256)
            and prev_run.sha256_bruto == fetch_res.sha256
        )
        if unchanged:
            finished_at = datetime.now(timezone.utc)  # noqa: UP017
            run.status = "SKIPPED_UNCHANGED"
            run.skipped_unchanged = True
            run.finalizado_em = finished_at
            source.ultima_execucao_em = finished_at
            source.ultimo_sucesso_em = finished_at
            source.falhas_consecutivas = 0
            source.proximo_ciclo_em = finished_at + timedelta(
                seconds=int(source.cron_ou_intervalo_seg)
            )
            await session.commit()
            return CollectorRunSummary(
                run_id=run.id,
                source_slug=source.slug,
                status="SKIPPED_UNCHANGED",
                skipped_unchanged=True,
            )

        await session.flush()
        if fetch_res.content:
            compressed = compress_artifact(fetch_res.content)
            session.add(
                AgroIngestionArtifact(
                    run_id=run.id,
                    source_id=source.id,
                    filename=fetch_res.filename,
                    sha256=fetch_res.sha256,
                    content_type=fetch_res.content_type,
                    compressao="gzip",
                    conteudo_comprimido=compressed,
                    tamanho_original_bytes=len(fetch_res.content),
                    tamanho_comprimido_bytes=len(compressed),
                    retencao_ate=started_at + timedelta(days=365),
                )
            )

        repo = AgroMarketRepository(session)
        extraidos = len(payload.observations)
        publicados = 0
        quarentena = 0
        rejeitados = 0
        structural_reject_flags = frozenset(
            {
                "FLAG_COMMODITY_INVALIDA",
                "FLAG_UF_INVALIDA",
                "FLAG_VALOR_INVALIDO",
                "FLAG_DATA_FUTURA",
                "FLAG_EVIDENCIA_NAO_CONFERE",
            }
        )

        for raw in payload.observations:
            prev_val = await repo.obter_ultimo_valor(
                source.id, raw.commodity_id, raw.uf, raw.praca
            )
            validated = validate_observation(
                raw,
                previous_valor=prev_val,
                max_variacao_pct=source.max_variacao_pct,
                max_defasagem_dias=int(source.max_defasagem_dias),
                raw_text=payload.raw_text_for_evidence,
            )
            is_structural_reject = any(
                f in structural_reject_flags for f in validated.flags_anomalia
            )
            if is_structural_reject:
                status_revisao = "REJEITADO"
                rejeitados += 1
            elif (
                source.auto_publish_policy == "SEMPRE_REVISAO_HUMANA"
                or validated.bloqueado_para_publicacao
            ):
                status_revisao = "PENDENTE_REVISAO"
                quarentena += 1
            else:
                status_revisao = "AUTO_APROVADO"
                publicados += 1

            staging = AgroStagingObservation(
                id=uuid.uuid4(),
                run_id=run.id,
                source_id=source.id,
                commodity_id=raw.commodity_id,
                uf=raw.uf,
                praca=raw.praca,
                tipo_preco=raw.tipo_preco,
                periodicidade=raw.periodicidade,
                data_referencia=raw.data_referencia,
                valor_normalizado=validated.valor_normalizado,
                moeda=raw.moeda,
                unidade_normalizada=validated.unidade_normalizada,
                valor_original=raw.valor_original,
                unidade_original=raw.unidade_original,
                fator_conversao=validated.fator_conversao,
                transformacao_aplicada=validated.transformacao_aplicada,
                trecho_evidencia=raw.trecho_evidencia,
                registro_origem=raw.registro_origem,
                confianca_extracao=raw.confianca_extracao,
                flags_anomalia=validated.flags_anomalia,
                status_revisao=status_revisao,
            )
            session.add(staging)
            await session.flush()

            if status_revisao == "AUTO_APROVADO":
                await repo.upsert_market_observation(
                    source_id=source.id,
                    run_id=run.id,
                    staging_id=staging.id,
                    payload={
                        "commodity_id": raw.commodity_id,
                        "uf": raw.uf,
                        "praca": raw.praca,
                        "tipo_preco": raw.tipo_preco,
                        "periodicidade": raw.periodicidade,
                        "data_referencia": raw.data_referencia,
                        "valor": validated.valor_normalizado,
                        "moeda": raw.moeda,
                        "unidade": validated.unidade_normalizada,
                        "valor_original": raw.valor_original,
                        "unidade_original": raw.unidade_original,
                        "transformacao_aplicada": validated.transformacao_aplicada,
                        "variacao_anterior_abs": validated.variacao_anterior_abs,
                        "variacao_anterior_pct": validated.variacao_anterior_pct,
                        "documento_oficial": raw.documento_oficial or fetch_res.url_efetiva,
                        "documento_hash_sha256": fetch_res.sha256,
                        "registro_origem": raw.registro_origem,
                    },
                )

        if publicados > 0 and quarentena == 0 and rejeitados == 0:
            run_status = "SUCESSO"
        elif publicados > 0:
            run_status = "PARCIAL"
        elif quarentena > 0:
            run_status = "QUARENTENA"
        else:
            run_status = "FALHA"

        finished_at = datetime.now(timezone.utc)  # noqa: UP017
        run.status = run_status
        run.total_extraidos = extraidos
        run.total_publicados = publicados
        run.total_quarentena = quarentena
        run.total_rejeitados = rejeitados
        run.finalizado_em = finished_at

        source.ultima_execucao_em = finished_at
        source.proximo_ciclo_em = finished_at + timedelta(seconds=int(source.cron_ou_intervalo_seg))
        if run_status == "FALHA":
            source.falhas_consecutivas = int(source.falhas_consecutivas) + 1
            suggestion = await self._handle_failure_sentinel_and_notify(
                session,
                source,
                run,
                run.erro_resumo or "Nenhuma observação válida extraída.",
            )
        else:
            suggestion = None
            source.ultimo_sucesso_em = finished_at
            source.falhas_consecutivas = 0

        if quarentena > 0:
            await notify_collector_event(
                session=session,
                source=source,
                event_kind="QUARENTENA_PENDENTE",
                summary_lines=[
                    f"Itens extraídos: {extraidos}",
                    f"Aguardando revisão humana: {quarentena}",
                    f"Publicados automaticamente: {publicados}",
                ],
                redis_client=self.redis_client,
                send_email_fn=self.send_email_fn,
            )

        await session.commit()
        await _publish_invalidation_event(self.redis_client, source.slug, publicados)
        return CollectorRunSummary(
            run_id=run.id,
            source_slug=source.slug,
            status=run_status,
            skipped_unchanged=False,
            total_extraidos=extraidos,
            total_publicados=publicados,
            total_quarentena=quarentena,
            total_rejeitados=rejeitados,
            sugestao_sentinela=suggestion,
        )

    async def run_due_sources(self) -> list[CollectorRunSummary]:
        """Identifica fontes ativas vencidas e executa coleta em sequência controlada."""
        now = datetime.now(timezone.utc)  # noqa: UP017
        async with self.session_factory() as session:
            await ensure_default_sources(session)
            await session.commit()
            rows = (
                await session.execute(
                    select(AgroDataSource.slug).where(
                        AgroDataSource.ativo.is_(True),
                        AgroDataSource.tipo_licenca != "LINK_HOMOLOGADO_APENAS",
                    )
                )
            ).scalars().all()
            due_check_rows = (
                await session.execute(
                    select(AgroDataSource).where(AgroDataSource.slug.in_(list(rows)))
                )
            ).scalars().all()
            due_slugs = [
                src.slug
                for src in due_check_rows
                if src.proximo_ciclo_em is None or src.proximo_ciclo_em <= now
            ]

        summaries: list[CollectorRunSummary] = []
        for slug in due_slugs:
            try:
                summary = await self.run_source_by_slug(slug, trigger_tipo="AGENDADO")
                summaries.append(summary)
            except Exception as exc:
                logger.warning(f"[agro_collector] fonte '{slug}' ignorada no ciclo: {exc}")
        return summaries


def _get_worker_session_factory() -> Any:
    from core.database import async_session_maker, catalog_admin_async_session_maker

    return catalog_admin_async_session_maker or async_session_maker


def _build_optional_redis_client() -> Any | None:
    try:
        from redis.asyncio import Redis

        from core.config import settings

        if settings.redis_url:
            return Redis.from_url(settings.redis_url)
    except Exception:
        return None
    return None


async def run_agro_collector_loop() -> None:
    """Loop contínuo do coletor multi-fonte executado dentro do ``background-worker``."""
    orchestrator = AgroCollectorOrchestrator(
        session_factory=_get_worker_session_factory(),
        redis_client=_build_optional_redis_client(),
    )
    while True:
        try:
            summaries = await orchestrator.run_due_sources()
            for item in summaries:
                logger.info(
                    f"[agro_collector] slug={item.source_slug} status={item.status} "
                    f"pub={item.total_publicados} quar={item.total_quarentena}"
                )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[agro_collector] erro no loop principal: {exc}")
        await asyncio.sleep(1800)


async def run_artifact_retention_loop() -> None:
    """Loop semanal que expurga artefatos gzip vencidos (> 12 meses) mantendo SHA-256."""
    session_factory = _get_worker_session_factory()
    while True:
        try:
            async with session_factory() as session:
                purged = await purge_expired_artifacts(session)
                if purged:
                    await session.commit()
                    logger.info(f"[agro_collector] artefatos gzip expurgados: {purged}")
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[agro_collector] erro no expurgo de artefatos: {exc}")
        await asyncio.sleep(86400)
