"""Serviço administrativo do Backoffice para fontes, execuções, sentinela e quarentena."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.admin_audit_service import AdminAuditService, resolve_admin_identity

from .backoffice_schemas import (
    CollectorBulkReviewRequest,
    CollectorBulkReviewResponse,
    CollectorDryRunObservationItem,
    CollectorDryRunResponse,
    CollectorRunItem,
    CollectorRunsListResponse,
    CollectorSourceCreateRequest,
    CollectorSourceItem,
    CollectorSourcesListResponse,
    CollectorSourceUpdateRequest,
    CollectorStagingItem,
    CollectorStagingListResponse,
)
from .contracts import CollectorRunSummary
from .fetcher import (
    SafeHttpFetcher,
    UnsafeSourceUrlError,
    compute_sha256,
    decompress_artifact,
    validate_source_url,
)
from .models import (
    AgroDataSource,
    AgroIngestionArtifact,
    AgroIngestionRun,
    AgroStagingObservation,
)
from .orchestrator import AgroCollectorOrchestrator, _publish_invalidation_event
from .repository import AgroMarketRepository
from .seed_sources import ensure_default_sources

RUN_COOLDOWN_SEC = 30
DRY_RUN_COOLDOWN_SEC = 10
_RATE_LIMIT_MEMORY: dict[str, datetime] = {}

_UNAPPROVABLE_FLAGS = frozenset(
    {
        "FLAG_COMMODITY_INVALIDA",
        "FLAG_UF_INVALIDA",
        "FLAG_VALOR_INVALIDO",
        "FLAG_DATA_FUTURA",
        "FLAG_EVIDENCIA_NAO_CONFERE",
    }
)


def reset_collector_rate_limits() -> None:
    """Limpa estado em memória do rate limit administrativo (uso em testes)."""
    _RATE_LIMIT_MEMORY.clear()


async def _enforce_rate_limit(
    action_key: str,
    cooldown_sec: int,
    *,
    redis_client: Any | None = None,
) -> None:
    now = datetime.now(timezone.utc)  # noqa: UP017
    if redis_client is not None:
        try:
            ok = bool(await redis_client.set(action_key, "1", nx=True, ex=cooldown_sec))
            if not ok:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Aguarde {cooldown_sec}s antes de disparar esta ação novamente.",
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Redis rate-limit indisponível (%s); usando memória local.", exc
            )

    last = _RATE_LIMIT_MEMORY.get(action_key)
    if last is not None and (now - last) < timedelta(seconds=cooldown_sec):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Aguarde {cooldown_sec}s antes de disparar esta ação novamente.",
        )
    _RATE_LIMIT_MEMORY[action_key] = now


def _validate_urls_or_422(
    url_principal: str,
    url_indice: str | None,
    whitelist: list[str],
) -> None:
    clean_whitelist = [str(w).strip().lower() for w in whitelist if str(w).strip()]
    if not clean_whitelist:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dominios_whitelist deve conter ao menos um domínio HTTPS válido.",
        )
    try:
        validate_source_url(url_principal, clean_whitelist, resolve_dns=False)
        if url_indice:
            validate_source_url(url_indice, clean_whitelist, resolve_dns=False)
    except UnsafeSourceUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"URL insegura ou fora da whitelist: {exc}",
        ) from exc


def _reuse_session_factory(session: AsyncSession) -> Any:
    @asynccontextmanager
    async def _ctx():
        yield session

    return _ctx


def _to_source_item(src: AgroDataSource, pending_count: int) -> CollectorSourceItem:
    return CollectorSourceItem(
        id=src.id,
        domain=src.domain,  # type: ignore[arg-type]
        slug=src.slug,
        nome=src.nome,
        sigla=src.sigla,
        tipo_licenca=src.tipo_licenca,  # type: ignore[arg-type]
        termo_autorizacao_ref=src.termo_autorizacao_ref,
        atribuicao_obrigatoria=src.atribuicao_obrigatoria,
        uf_padrao=src.uf_padrao,
        praca_padrao=src.praca_padrao,
        dominios_whitelist=list(src.dominios_whitelist or []),
        url_principal=src.url_principal,
        url_indice=src.url_indice,
        estrategia_coleta=src.estrategia_coleta,  # type: ignore[arg-type]
        config_extrator=dict(src.config_extrator or {}),
        cron_ou_intervalo_seg=int(src.cron_ou_intervalo_seg),
        auto_publish_policy=src.auto_publish_policy,  # type: ignore[arg-type]
        max_variacao_pct=src.max_variacao_pct,
        max_defasagem_dias=int(src.max_defasagem_dias),
        prioridade_exibicao=int(src.prioridade_exibicao),
        ativo=bool(src.ativo),
        falhas_consecutivas=int(src.falhas_consecutivas),
        ultima_execucao_em=src.ultima_execucao_em,
        ultimo_sucesso_em=src.ultimo_sucesso_em,
        proximo_ciclo_em=src.proximo_ciclo_em,
        pendentes_revisao=pending_count,
    )


class CollectorBackofficeService:
    """Regras administrativas auditadas do agente coletor de dados agropecuários."""

    async def list_sources(self, session: AsyncSession) -> CollectorSourcesListResponse:
        """Lista todas as fontes configuradas com contagem de quarentena pendente."""
        sources = await ensure_default_sources(session)
        await session.commit()

        pending_stmt = (
            select(AgroStagingObservation.source_id, func.count(AgroStagingObservation.id))
            .where(AgroStagingObservation.status_revisao == "PENDENTE_REVISAO")
            .group_by(AgroStagingObservation.source_id)
        )
        counts = {row[0]: int(row[1]) for row in (await session.execute(pending_stmt)).all()}
        items = [_to_source_item(src, counts.get(src.id, 0)) for src in sources]
        return CollectorSourcesListResponse(
            sources=items,
            total=len(items),
            pendentes_quarentena_total=sum(counts.values()),
        )

    async def create_source(
        self,
        session: AsyncSession,
        payload: CollectorSourceCreateRequest,
        admin_claims: dict[str, Any],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CollectorSourceItem:
        """Cadastra nova fonte governamental ou parceira autorizada com auditoria."""
        existing = (
            await session.execute(
                select(AgroDataSource).where(AgroDataSource.slug == payload.slug)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe fonte cadastrada com slug '{payload.slug}'.",
            )

        _validate_urls_or_422(
            payload.url_principal, payload.url_indice, payload.dominios_whitelist
        )
        source = AgroDataSource(
            id=uuid.uuid4(),
            domain=payload.domain,
            slug=payload.slug,
            nome=payload.nome,
            sigla=payload.sigla,
            tipo_licenca=payload.tipo_licenca,
            termo_autorizacao_ref=payload.termo_autorizacao_ref,
            atribuicao_obrigatoria=payload.atribuicao_obrigatoria,
            uf_padrao=payload.uf_padrao.upper(),
            praca_padrao=payload.praca_padrao,
            dominios_whitelist=[w.strip().lower() for w in payload.dominios_whitelist],
            url_principal=payload.url_principal,
            url_indice=payload.url_indice,
            estrategia_coleta=payload.estrategia_coleta,
            config_extrator=payload.config_extrator,
            cron_ou_intervalo_seg=payload.cron_ou_intervalo_seg,
            auto_publish_policy=payload.auto_publish_policy,
            max_variacao_pct=payload.max_variacao_pct,
            max_defasagem_dias=payload.max_defasagem_dias,
            prioridade_exibicao=payload.prioridade_exibicao,
            ativo=payload.ativo,
        )
        session.add(source)
        await session.flush()

        admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_id,
            admin_email=admin_email,
            acao="CREATE",
            entidade="agro_data_sources",
            entidade_id=source.id,
            descricao=f"Cadastro de fonte '{source.slug}' ({source.tipo_licenca})",
            dados_novos={"slug": source.slug, "url_principal": source.url_principal},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        return _to_source_item(source, 0)

    async def update_source(
        self,
        session: AsyncSession,
        source_id: uuid.UUID,
        payload: CollectorSourceUpdateRequest,
        admin_claims: dict[str, Any],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CollectorSourceItem:
        """Atualiza configurações operacionais de fonte existente validando whitelist."""
        source = (
            await session.execute(select(AgroDataSource).where(AgroDataSource.id == source_id))
        ).scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=404, detail="Fonte não encontrada.")

        updates = payload.model_dump(exclude_none=True)
        next_licenca = updates.get("tipo_licenca", source.tipo_licenca)
        next_termo = updates.get("termo_autorizacao_ref", source.termo_autorizacao_ref)
        if next_licenca == "PARCEIRO_AUTORIZADO" and not (next_termo and str(next_termo).strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="termo_autorizacao_ref é obrigatório para PARCEIRO_AUTORIZADO.",
            )

        next_whitelist = list(updates.get("dominios_whitelist", source.dominios_whitelist))
        next_url = str(updates.get("url_principal", source.url_principal))
        next_indice = updates.get("url_indice", source.url_indice)
        _validate_urls_or_422(next_url, next_indice, next_whitelist)

        anterior = {"url_principal": source.url_principal, "ativo": source.ativo}
        for key, value in updates.items():
            if key == "uf_padrao" and isinstance(value, str):
                value = value.upper()
            elif key == "dominios_whitelist" and isinstance(value, list):
                value = [str(w).strip().lower() for w in value]
            setattr(source, key, value)

        admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_id,
            admin_email=admin_email,
            acao="UPDATE",
            entidade="agro_data_sources",
            entidade_id=source.id,
            descricao=f"Atualização administrativa da fonte '{source.slug}'",
            dados_anteriores=anterior,
            dados_novos=updates,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        pending = (
            await session.execute(
                select(func.count(AgroStagingObservation.id)).where(
                    AgroStagingObservation.source_id == source.id,
                    AgroStagingObservation.status_revisao == "PENDENTE_REVISAO",
                )
            )
        ).scalar_one()
        return _to_source_item(source, int(pending or 0))

    async def test_dry_run(
        self,
        session: AsyncSession,
        source_id: uuid.UUID,
        *,
        fetcher: SafeHttpFetcher | None = None,
        ia_callable: Callable[..., Awaitable[str]] | None = None,
        redis_client: Any | None = None,
    ) -> CollectorDryRunResponse:
        """Executa Testar Coleta (Dry-Run) sem alterar série publicada."""
        await _enforce_rate_limit(
            f"agro:collector:ratelimit:dryrun:{source_id}",
            DRY_RUN_COOLDOWN_SEC,
            redis_client=redis_client,
        )
        source = (
            await session.execute(select(AgroDataSource).where(AgroDataSource.id == source_id))
        ).scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=404, detail="Fonte não encontrada.")

        orchestrator = AgroCollectorOrchestrator(
            _reuse_session_factory(session),
            fetcher=fetcher,
            redis_client=redis_client,
            ia_callable=ia_callable,
        )
        try:
            raw_res = await orchestrator.dry_run_source(source, session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Falha no teste de coleta: {exc}",
            ) from exc

        return CollectorDryRunResponse(
            source_slug=raw_res["source_slug"],
            url_efetiva=raw_res["url_efetiva"],
            sha256_bruto=raw_res["sha256_bruto"],
            modelo_ia=raw_res["modelo_ia"],
            tokens_entrada=raw_res["tokens_entrada"],
            tokens_saida=raw_res["tokens_saida"],
            custo_estimado_usd=raw_res["custo_estimado_usd"],
            total_extraidos=raw_res["total_extraidos"],
            itens=[CollectorDryRunObservationItem(**item) for item in raw_res["itens"]],
        )

    async def trigger_run(
        self,
        session: AsyncSession,
        source_id: uuid.UUID,
        admin_claims: dict[str, Any],
        *,
        fetcher: SafeHttpFetcher | None = None,
        ia_callable: Callable[..., Awaitable[str]] | None = None,
        redis_client: Any | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CollectorRunSummary:
        """Dispara coleta manual auditada com rate limit administrativo."""
        await _enforce_rate_limit(
            f"agro:collector:ratelimit:run:{source_id}",
            RUN_COOLDOWN_SEC,
            redis_client=redis_client,
        )
        source = (
            await session.execute(select(AgroDataSource).where(AgroDataSource.id == source_id))
        ).scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=404, detail="Fonte não encontrada.")

        admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
        orchestrator = AgroCollectorOrchestrator(
            _reuse_session_factory(session),
            fetcher=fetcher,
            redis_client=redis_client,
            ia_callable=ia_callable,
        )
        try:
            summary = await orchestrator.run_source_by_slug(
                source.slug,
                trigger_tipo="MANUAL",
                executado_por=admin_email,
                force=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_id,
            admin_email=admin_email,
            acao="MANUAL_RUN",
            entidade="agro_ingestion_runs",
            entidade_id=summary.run_id,
            descricao=f"Execução manual disparada para '{source.slug}': {summary.status}",
            dados_novos={
                "source_slug": source.slug,
                "status": summary.status,
                "publicados": summary.total_publicados,
                "quarentena": summary.total_quarentena,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        return summary

    async def list_runs(
        self,
        session: AsyncSession,
        *,
        source_id: uuid.UUID | None = None,
        run_status: str | None = None,
        limit: int = 50,
    ) -> CollectorRunsListResponse:
        """Lista histórico de execuções do coletor com estado dos artefatos."""
        stmt = (
            select(AgroIngestionRun, AgroDataSource.slug, AgroDataSource.sigla)
            .join(AgroDataSource, AgroIngestionRun.source_id == AgroDataSource.id)
            .order_by(AgroIngestionRun.iniciado_em.desc())
            .limit(min(max(limit, 1), 200))
        )
        if source_id is not None:
            stmt = stmt.where(AgroIngestionRun.source_id == source_id)
        if run_status:
            stmt = stmt.where(AgroIngestionRun.status == run_status)

        rows = (await session.execute(stmt)).all()
        run_ids = [r[0].id for r in rows]
        artifact_map: dict[uuid.UUID, AgroIngestionArtifact] = {}
        if run_ids:
            art_stmt = select(AgroIngestionArtifact).where(
                AgroIngestionArtifact.run_id.in_(run_ids)
            )
            for art in (await session.execute(art_stmt)).scalars().all():
                artifact_map[art.run_id] = art

        items: list[CollectorRunItem] = []
        for run, slug, sigla in rows:
            art = artifact_map.get(run.id)
            items.append(
                CollectorRunItem(
                    id=run.id,
                    source_id=run.source_id,
                    source_slug=slug,
                    source_sigla=sigla,
                    status=run.status,  # type: ignore[arg-type]
                    trigger_tipo=run.trigger_tipo,  # type: ignore[arg-type]
                    executado_por=run.executado_por,
                    url_efetiva=run.url_efetiva,
                    http_status=run.http_status,
                    sha256_bruto=run.sha256_bruto,
                    tamanho_bytes=run.tamanho_bytes,
                    skipped_unchanged=bool(run.skipped_unchanged),
                    modelo_ia=run.modelo_ia,
                    tokens_entrada=int(run.tokens_entrada),
                    tokens_saida=int(run.tokens_saida),
                    custo_estimado_usd=run.custo_estimado_usd,
                    total_extraidos=int(run.total_extraidos),
                    total_publicados=int(run.total_publicados),
                    total_quarentena=int(run.total_quarentena),
                    total_rejeitados=int(run.total_rejeitados),
                    erro_resumo=run.erro_resumo,
                    sugestao_sentinela=run.sugestao_sentinela,
                    has_artifact=art is not None,
                    artifact_expurgado=bool(
                        art is not None
                        and (art.expurgado_em is not None or art.conteudo_comprimido is None)
                    ),
                    iniciado_em=run.iniciado_em,
                    finalizado_em=run.finalizado_em,
                )
            )
        return CollectorRunsListResponse(runs=items, total=len(items))

    async def download_run_artifact(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> tuple[bytes, str, str, str]:
        """Recupera e valida bytes originais de ``agro_ingestion_artifacts``."""
        art = (
            await session.execute(
                select(AgroIngestionArtifact).where(AgroIngestionArtifact.run_id == run_id)
            )
        ).scalar_one_or_none()
        if art is None:
            raise HTTPException(status_code=404, detail="Artefato não encontrado para esta run.")
        if art.expurgado_em is not None or art.conteudo_comprimido is None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Conteúdo binário expurgado após janela de retenção de 12 meses.",
            )
        raw_bytes = decompress_artifact(art.conteudo_comprimido)
        if compute_sha256(raw_bytes) != art.sha256:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha de integridade SHA-256 ao descomprimir artefato forense.",
            )
        return (
            raw_bytes,
            art.filename,
            art.content_type or "application/octet-stream",
            art.sha256,
        )

    async def apply_sentinel_suggestion(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        justificativa: str,
        admin_claims: dict[str, Any],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CollectorSourceItem:
        """Aplica URL sugerida pelo Sentinela após validação de whitelist e auditoria."""
        run = (
            await session.execute(select(AgroIngestionRun).where(AgroIngestionRun.id == run_id))
        ).scalar_one_or_none()
        if run is None or not isinstance(run.sugestao_sentinela, dict):
            raise HTTPException(
                status_code=404,
                detail="Sugestão do Sentinela não encontrada para esta execução.",
            )
        suggested_url = str(run.sugestao_sentinela.get("url_sugerida") or "").strip()
        if not suggested_url:
            raise HTTPException(status_code=422, detail="Sugestão do Sentinela sem URL válida.")

        source = (
            await session.execute(
                select(AgroDataSource).where(AgroDataSource.id == run.source_id)
            )
        ).scalar_one_or_none()
        if source is None:
            raise HTTPException(status_code=404, detail="Fonte associada não encontrada.")

        _validate_urls_or_422(suggested_url, source.url_indice, list(source.dominios_whitelist))

        anterior = {"url_principal": source.url_principal}
        source.url_principal = suggested_url
        source.falhas_consecutivas = 0
        updated_sugg = dict(run.sugestao_sentinela)
        updated_sugg["aplicada_em"] = datetime.now(timezone.utc).isoformat()  # noqa: UP017
        run.sugestao_sentinela = updated_sugg

        admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_id,
            admin_email=admin_email,
            acao="APPLY_SENTINEL",
            entidade="agro_data_sources",
            entidade_id=source.id,
            descricao=f"Aplicada URL do Sentinela para '{source.slug}': {justificativa}",
            dados_anteriores=anterior,
            dados_novos={"url_principal": suggested_url, "run_id": str(run_id)},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.commit()
        return _to_source_item(source, 0)

    async def list_staging(
        self,
        session: AsyncSession,
        *,
        status_revisao: str = "PENDENTE_REVISAO",
        source_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> CollectorStagingListResponse:
        """Lista fila de revisão com trecho literal de evidência e referência anterior."""
        stmt = (
            select(AgroStagingObservation, AgroDataSource.slug, AgroDataSource.sigla)
            .join(AgroDataSource, AgroStagingObservation.source_id == AgroDataSource.id)
            .order_by(AgroStagingObservation.created_at.desc())
            .limit(min(max(limit, 1), 300))
        )
        if status_revisao != "TODOS":
            stmt = stmt.where(AgroStagingObservation.status_revisao == status_revisao)
        if source_id is not None:
            stmt = stmt.where(AgroStagingObservation.source_id == source_id)

        rows = (await session.execute(stmt)).all()
        repo = AgroMarketRepository(session)
        pendentes_total = (
            await session.execute(
                select(func.count(AgroStagingObservation.id)).where(
                    AgroStagingObservation.status_revisao == "PENDENTE_REVISAO"
                )
            )
        ).scalar_one()

        items: list[CollectorStagingItem] = []
        for stg, slug, sigla in rows:
            ultimo = await repo.obter_ultimo_valor(
                stg.source_id, stg.commodity_id, stg.uf, stg.praca
            )
            var_pct: Decimal | None = None
            if ultimo is not None and ultimo > 0:
                var_pct = (
                    ((stg.valor_normalizado - ultimo) / ultimo) * Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            items.append(
                CollectorStagingItem(
                    id=stg.id,
                    run_id=stg.run_id,
                    source_id=stg.source_id,
                    source_slug=slug,
                    source_sigla=sigla,
                    commodity_id=stg.commodity_id,
                    uf=stg.uf,
                    praca=stg.praca,
                    tipo_preco=stg.tipo_preco,
                    periodicidade=stg.periodicidade,
                    data_referencia=stg.data_referencia,
                    valor_normalizado=stg.valor_normalizado,
                    moeda=stg.moeda,
                    unidade_normalizada=stg.unidade_normalizada,
                    valor_original=stg.valor_original,
                    unidade_original=stg.unidade_original,
                    fator_conversao=stg.fator_conversao,
                    transformacao_aplicada=stg.transformacao_aplicada,
                    trecho_evidencia=stg.trecho_evidencia,
                    registro_origem=stg.registro_origem,
                    confianca_extracao=stg.confianca_extracao,
                    flags_anomalia=list(stg.flags_anomalia or []),
                    status_revisao=stg.status_revisao,  # type: ignore[arg-type]
                    ultimo_valor_ativo=ultimo,
                    variacao_contra_ativo_pct=var_pct,
                    revisado_em=stg.revisado_em,
                    justificativa_revisao=stg.justificativa_revisao,
                    created_at=stg.created_at,
                )
            )

        return CollectorStagingListResponse(
            items=items,
            total=len(items),
            pendentes_total=int(pendentes_total or 0),
        )

    async def review_staging_item(
        self,
        session: AsyncSession,
        staging_id: uuid.UUID,
        *,
        aprovar: bool,
        justificativa: str,
        admin_claims: dict[str, Any],
        redis_client: Any | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        commit: bool = True,
    ) -> CollectorStagingItem:
        """Aprova ou rejeita um item auditado da quarentena (nunca edita preço)."""
        stg = (
            await session.execute(
                select(AgroStagingObservation).where(AgroStagingObservation.id == staging_id)
            )
        ).scalar_one_or_none()
        if stg is None:
            raise HTTPException(status_code=404, detail="Observação em quarentena não encontrada.")
        if stg.status_revisao != "PENDENTE_REVISAO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Observação já revisada com status '{stg.status_revisao}'.",
            )
        if aprovar and any(f in _UNAPPROVABLE_FLAGS for f in (stg.flags_anomalia or [])):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Item com falha estrutural ou evidência divergente não pode ser aprovado.",
            )

        source = (
            await session.execute(select(AgroDataSource).where(AgroDataSource.id == stg.source_id))
        ).scalar_one()
        run = (
            await session.execute(select(AgroIngestionRun).where(AgroIngestionRun.id == stg.run_id))
        ).scalar_one()
        admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
        now = datetime.now(timezone.utc)  # noqa: UP017

        stg.status_revisao = "APROVADO" if aprovar else "REJEITADO"
        stg.revisado_por = admin_id
        stg.revisado_em = now
        stg.justificativa_revisao = justificativa

        if aprovar:
            repo = AgroMarketRepository(session)
            prev_val = await repo.obter_ultimo_valor(
                stg.source_id, stg.commodity_id, stg.uf, stg.praca
            )
            var_abs: Decimal | None = None
            var_pct: Decimal | None = None
            if prev_val is not None and prev_val > 0:
                var_abs = (stg.valor_normalizado - prev_val).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                var_pct = ((var_abs / prev_val) * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            await repo.upsert_market_observation(
                source_id=stg.source_id,
                run_id=stg.run_id,
                staging_id=stg.id,
                payload={
                    "commodity_id": stg.commodity_id,
                    "uf": stg.uf,
                    "praca": stg.praca,
                    "tipo_preco": stg.tipo_preco,
                    "periodicidade": stg.periodicidade,
                    "data_referencia": stg.data_referencia,
                    "valor": stg.valor_normalizado,
                    "moeda": stg.moeda,
                    "unidade": stg.unidade_normalizada,
                    "valor_original": stg.valor_original,
                    "unidade_original": stg.unidade_original,
                    "transformacao_aplicada": stg.transformacao_aplicada,
                    "variacao_anterior_abs": var_abs,
                    "variacao_anterior_pct": var_pct,
                    "documento_oficial": run.url_efetiva or source.url_principal,
                    "documento_hash_sha256": run.sha256_bruto or "",
                    "registro_origem": stg.registro_origem,
                },
            )

        await AdminAuditService.log_action(
            session=session,
            admin_id=admin_id,
            admin_email=admin_email,
            acao="APPROVE" if aprovar else "REJECT",
            entidade="agro_staging_observations",
            entidade_id=stg.id,
            descricao=f"Revisão humana ({stg.status_revisao}): {justificativa}",
            dados_novos={
                "commodity_id": stg.commodity_id,
                "uf": stg.uf,
                "valor_normalizado": str(stg.valor_normalizado),
                "status_revisao": stg.status_revisao,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if commit:
            await session.commit()
            if aprovar:
                await _publish_invalidation_event(redis_client, source.slug, 1)

        return CollectorStagingItem(
            id=stg.id,
            run_id=stg.run_id,
            source_id=stg.source_id,
            source_slug=source.slug,
            source_sigla=source.sigla,
            commodity_id=stg.commodity_id,
            uf=stg.uf,
            praca=stg.praca,
            tipo_preco=stg.tipo_preco,
            periodicidade=stg.periodicidade,
            data_referencia=stg.data_referencia,
            valor_normalizado=stg.valor_normalizado,
            moeda=stg.moeda,
            unidade_normalizada=stg.unidade_normalizada,
            valor_original=stg.valor_original,
            unidade_original=stg.unidade_original,
            fator_conversao=stg.fator_conversao,
            transformacao_aplicada=stg.transformacao_aplicada,
            trecho_evidencia=stg.trecho_evidencia,
            registro_origem=stg.registro_origem,
            confianca_extracao=stg.confianca_extracao,
            flags_anomalia=list(stg.flags_anomalia or []),
            status_revisao=stg.status_revisao,  # type: ignore[arg-type]
            revisado_em=stg.revisado_em,
            justificativa_revisao=stg.justificativa_revisao,
            created_at=stg.created_at,
        )

    async def bulk_review_staging(
        self,
        session: AsyncSession,
        payload: CollectorBulkReviewRequest,
        admin_claims: dict[str, Any],
        *,
        redis_client: Any | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CollectorBulkReviewResponse:
        """Aprova ou rejeita em lote múltiplas observações auditadas."""
        aprovar = payload.acao == "APROVAR"
        aprovados = 0
        rejeitados = 0
        for stg_id in payload.staging_ids:
            await self.review_staging_item(
                session,
                stg_id,
                aprovar=aprovar,
                justificativa=payload.justificativa,
                admin_claims=admin_claims,
                redis_client=redis_client,
                ip_address=ip_address,
                user_agent=user_agent,
                commit=False,
            )
            if aprovar:
                aprovados += 1
            else:
                rejeitados += 1

        await session.commit()
        if aprovados > 0:
            await _publish_invalidation_event(redis_client, "bulk_review", aprovados)
        return CollectorBulkReviewResponse(
            processados=len(payload.staging_ids),
            aprovados=aprovados,
            rejeitados=rejeitados,
        )


collector_backoffice_service = CollectorBackofficeService()
