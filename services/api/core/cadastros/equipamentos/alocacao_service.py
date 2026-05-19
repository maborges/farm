from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva

from .models import Equipamento, EquipamentoAlocacao


@dataclass(frozen=True)
class EquipamentoUnidadeOperacional:
    equipamento_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID | None
    source: str
    alocacao_id: uuid.UUID | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log_invalid_context(event: str, **extra) -> None:
    logger.warning(event, **{key: str(value) if isinstance(value, uuid.UUID) else value for key, value in extra.items()})


async def _validar_equipamento(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
) -> Equipamento:
    equipamento = (
        await session.execute(
            select(Equipamento).where(
                Equipamento.id == equipamento_id,
                Equipamento.tenant_id == tenant_id,
                Equipamento.ativo == True,
            )
        )
    ).scalars().first()
    if not equipamento:
        _log_invalid_context(
            "frota_equipamento_tenant_mismatch",
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
        )
        raise EntityNotFoundError("Equipamento não encontrado para o tenant.")
    return equipamento


async def _validar_unidade_produtiva(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    unidade = (
        await session.execute(
            select(UnidadeProdutiva.id).where(
                UnidadeProdutiva.id == unidade_produtiva_id,
                UnidadeProdutiva.tenant_id == tenant_id,
                UnidadeProdutiva.ativo == True,
            )
        )
    ).scalar_one_or_none()
    if unidade is None:
        _log_invalid_context(
            "frota_alocacao_up_tenant_mismatch",
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        raise BusinessRuleError("Unidade produtiva da alocação não localizada ou inacessível.")


async def get_equipamento_unidade_operacional(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    expected_unidade_produtiva_id: uuid.UUID | None = None,
    momento: datetime | None = None,
) -> EquipamentoUnidadeOperacional:
    """Resolve a UP operacional de um equipamento.

    Ordem de resolução:
    1. alocação ativa em `equipamento_alocacoes`;
    2. fallback legado `cadastros_equipamentos.unidade_produtiva_id`.
    """
    equipamento = await _validar_equipamento(session, tenant_id=tenant_id, equipamento_id=equipamento_id)
    ref = momento or _now()

    stmt = (
        select(EquipamentoAlocacao)
        .where(
            EquipamentoAlocacao.tenant_id == tenant_id,
            EquipamentoAlocacao.equipamento_id == equipamento_id,
            EquipamentoAlocacao.status == "ATIVA",
            EquipamentoAlocacao.data_inicio <= ref,
            (EquipamentoAlocacao.data_fim.is_(None) | (EquipamentoAlocacao.data_fim >= ref)),
        )
        .order_by(
            EquipamentoAlocacao.principal.desc(),
            EquipamentoAlocacao.data_inicio.desc(),
            EquipamentoAlocacao.created_at.desc(),
        )
        .limit(1)
    )
    alocacao = (await session.execute(stmt)).scalars().first()

    if alocacao:
        unidade_id = alocacao.unidade_produtiva_id
        source = "alocacao"
        alocacao_id = alocacao.id
    else:
        unidade_id = equipamento.unidade_produtiva_id
        source = "legado"
        alocacao_id = None

    if expected_unidade_produtiva_id and unidade_id != expected_unidade_produtiva_id:
        _log_invalid_context(
            "frota_equipamento_up_mismatch",
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            expected_unidade_produtiva_id=expected_unidade_produtiva_id,
            actual_unidade_produtiva_id=unidade_id,
            source=source,
        )
        raise BusinessRuleError("Equipamento não está alocado na unidade produtiva esperada.")

    return EquipamentoUnidadeOperacional(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_id,
        source=source,
        alocacao_id=alocacao_id,
    )


async def criar_equipamento_alocacao(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    principal: bool = True,
    status: str = "ATIVA",
    observacao: str | None = None,
    responsavel_id: uuid.UUID | None = None,
    encerrar_alocacoes_ativas: bool = False,
) -> EquipamentoAlocacao:
    await _validar_equipamento(session, tenant_id=tenant_id, equipamento_id=equipamento_id)
    await _validar_unidade_produtiva(session, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id)

    inicio = data_inicio or _now()
    if data_fim and data_fim < inicio:
        raise BusinessRuleError("Data fim da alocação não pode ser anterior à data início.")

    if encerrar_alocacoes_ativas:
        alocacoes_ativas = (
            await session.execute(
                select(EquipamentoAlocacao).where(
                    EquipamentoAlocacao.tenant_id == tenant_id,
                    EquipamentoAlocacao.equipamento_id == equipamento_id,
                    EquipamentoAlocacao.status == "ATIVA",
                    EquipamentoAlocacao.data_fim.is_(None),
                )
            )
        ).scalars().all()
        for alocacao in alocacoes_ativas:
            alocacao.data_fim = inicio
            alocacao.status = "ENCERRADA"
            session.add(alocacao)

    alocacao = EquipamentoAlocacao(
        tenant_id=tenant_id,
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=inicio,
        data_fim=data_fim,
        principal=principal,
        status=status,
        observacao=observacao,
        responsavel_id=responsavel_id,
    )
    session.add(alocacao)
    await session.flush()
    return alocacao
