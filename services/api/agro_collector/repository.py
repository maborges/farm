"""Repositório de séries históricas de mercado e retenção de artefatos forenses."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgroDataSource, AgroIngestionArtifact, AgroMarketObservation


@dataclass(frozen=True, slots=True)
class MarketObservationRecord:
    """Projeção leve de observação publicada com metadados da fonte."""

    id: uuid.UUID
    source_id: uuid.UUID
    source_slug: str
    sigla_fonte: str
    nome_fonte: str
    tipo_licenca: str
    prioridade_exibicao: int
    atribuicao_obrigatoria: str | None
    commodity_id: str
    uf: str
    praca: str
    tipo_preco: str
    periodicidade: str
    data_referencia: date
    valor: float
    moeda: str
    unidade: str
    variacao_pct: float | None
    documento_oficial: str | None
    documento_hash_sha256: str
    registro_origem: str | None
    url_principal: str
    max_defasagem_dias: int
    publicado_em: datetime


async def purge_expired_artifacts(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    """Expurga binários gzip vencidos mantendo hash SHA-256 e metadados forenses.

    Args:
        session: Sessão SQLAlchemy ativa.
        now: Referência UTC opcional para testes determinísticos.

    Returns:
        Quantidade de artefatos expurgados nesta execução.
    """
    ref_now = now or datetime.now(timezone.utc)  # noqa: UP017
    stmt = (
        update(AgroIngestionArtifact)
        .where(
            AgroIngestionArtifact.retencao_ate < ref_now,
            AgroIngestionArtifact.conteudo_comprimido.is_not(None),
        )
        .values(conteudo_comprimido=None, expurgado_em=ref_now)
        .execution_options(synchronize_session=False)
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)


class AgroMarketRepository:
    """Acesso resiliente às observações publicadas do coletor multi-fonte."""

    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session

    async def obter_ultimo_valor(
        self,
        source_id: uuid.UUID,
        commodity_id: str,
        uf: str,
        praca: str,
    ) -> Decimal | None:
        """Busca o valor publicado mais recente para comparação estatística.

        Args:
            source_id: ID da fonte em ``agro_data_sources``.
            commodity_id: ID canônico da commodity.
            uf: Sigla da UF.
            praca: Nome da praça ou média estadual.

        Returns:
            Último ``Decimal`` publicado ou ``None`` se inexistente.
        """
        if self.session is None:
            return None
        stmt = (
            select(AgroMarketObservation.valor)
            .where(
                AgroMarketObservation.source_id == source_id,
                AgroMarketObservation.commodity_id == commodity_id,
                AgroMarketObservation.uf == uf,
                AgroMarketObservation.praca == praca,
                AgroMarketObservation.ativo.is_(True),
            )
            .order_by(AgroMarketObservation.data_referencia.desc())
            .limit(1)
        )
        val = (await self.session.execute(stmt)).scalar_one_or_none()
        return Decimal(str(val)) if val is not None else None

    async def upsert_market_observation(
        self,
        *,
        source_id: uuid.UUID,
        run_id: uuid.UUID,
        staging_id: uuid.UUID | None,
        payload: dict[str, Any],
    ) -> AgroMarketObservation:
        """Insere ou atualiza observação pela chave natural única da série.

        Args:
            source_id: ID da fonte emissora.
            run_id: ID da execução atual.
            staging_id: ID da linha correspondente em ``agro_staging_observations``.
            payload: Campos normalizados e validados pelos guardrails.

        Returns:
            Instância ORM persistida em ``agro_market_observations``.
        """
        if self.session is None:
            raise ValueError("Sessão SQLAlchemy obrigatória para upsert de observação.")

        stmt = select(AgroMarketObservation).where(
            AgroMarketObservation.source_id == source_id,
            AgroMarketObservation.commodity_id == payload["commodity_id"],
            AgroMarketObservation.uf == payload["uf"],
            AgroMarketObservation.praca == payload["praca"],
            AgroMarketObservation.data_referencia == payload["data_referencia"],
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)  # noqa: UP017

        if existing is not None:
            existing.run_id = run_id
            existing.staging_id = staging_id
            existing.tipo_preco = payload["tipo_preco"]
            existing.periodicidade = payload["periodicidade"]
            existing.valor = payload["valor"]
            existing.moeda = payload["moeda"]
            existing.unidade = payload["unidade"]
            existing.valor_original = payload["valor_original"]
            existing.unidade_original = payload["unidade_original"]
            existing.transformacao_aplicada = payload["transformacao_aplicada"]
            existing.variacao_anterior_abs = payload["variacao_anterior_abs"]
            existing.variacao_anterior_pct = payload["variacao_anterior_pct"]
            existing.documento_oficial = payload["documento_oficial"]
            existing.documento_hash_sha256 = payload["documento_hash_sha256"]
            existing.registro_origem = payload["registro_origem"]
            existing.publicado_em = now
            existing.ativo = True
            return existing

        obs = AgroMarketObservation(
            source_id=source_id,
            run_id=run_id,
            staging_id=staging_id,
            publicado_em=now,
            ativo=True,
            **payload,
        )
        self.session.add(obs)
        return obs

    async def listar_ultimas_observacoes(
        self,
        *,
        uf: str | None = None,
        commodity_ids: Sequence[str] | None = None,
        tipo_licenca_in: Sequence[str] | None = None,
    ) -> list[MarketObservationRecord]:
        """Retorna a última cotação ativa por ``(source, commodity_id, uf, praca)``.

        Args:
            uf: Filtro opcional por sigla estadual.
            commodity_ids: Filtro opcional por lista de commodities canônicas.
            tipo_licenca_in: Filtro opcional por tipos de licença permitidos.

        Returns:
            Lista ordenada de ``MarketObservationRecord``. Retorna ``[]`` graciosamente se
            as tabelas ainda não existirem em bancos legados/SQLite parciais.
        """
        if self.session is None:
            return []

        conditions = [AgroMarketObservation.ativo.is_(True), AgroDataSource.ativo.is_(True)]
        if uf:
            conditions.append(AgroMarketObservation.uf == uf.upper())
        if commodity_ids:
            conditions.append(AgroMarketObservation.commodity_id.in_(list(commodity_ids)))
        if tipo_licenca_in:
            conditions.append(AgroDataSource.tipo_licenca.in_(list(tipo_licenca_in)))

        stmt = (
            select(AgroMarketObservation, AgroDataSource)
            .join(AgroDataSource, AgroMarketObservation.source_id == AgroDataSource.id)
            .where(and_(*conditions))
            .order_by(
                AgroMarketObservation.data_referencia.desc(),
                AgroDataSource.prioridade_exibicao.asc(),
                AgroMarketObservation.publicado_em.desc(),
            )
        )
        try:
            rows = (await self.session.execute(stmt)).all()
        except (OperationalError, ProgrammingError):
            return []

        seen_series: set[tuple[uuid.UUID, str, str, str]] = set()
        results: list[MarketObservationRecord] = []
        for obs, src in rows:
            series_key = (obs.source_id, obs.commodity_id, obs.uf, obs.praca)
            if series_key in seen_series:
                continue
            seen_series.add(series_key)
            results.append(
                MarketObservationRecord(
                    id=obs.id,
                    source_id=obs.source_id,
                    source_slug=src.slug,
                    sigla_fonte=src.sigla,
                    nome_fonte=src.nome,
                    tipo_licenca=src.tipo_licenca,
                    prioridade_exibicao=int(src.prioridade_exibicao),
                    atribuicao_obrigatoria=src.atribuicao_obrigatoria,
                    commodity_id=obs.commodity_id,
                    uf=obs.uf,
                    praca=obs.praca,
                    tipo_preco=obs.tipo_preco,
                    periodicidade=obs.periodicidade,
                    data_referencia=obs.data_referencia,
                    valor=float(obs.valor),
                    moeda=obs.moeda,
                    unidade=obs.unidade,
                    variacao_pct=(
                        float(obs.variacao_anterior_pct)
                        if obs.variacao_anterior_pct is not None
                        else None
                    ),
                    documento_oficial=obs.documento_oficial,
                    documento_hash_sha256=obs.documento_hash_sha256,
                    registro_origem=obs.registro_origem,
                    url_principal=src.url_principal,
                    max_defasagem_dias=int(src.max_defasagem_dias),
                    publicado_em=obs.publicado_em,
                )
            )
        return results
