"""
Rastreio e controle de uso de IA por tenant.
Suporta limite do plano + créditos extras por pacote.
Não implementa cobrança — apenas rastreio e limite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PlanTier
from ia.models import IAUso, IACreditosPacote

# Limite mensal de chamadas bem-sucedidas de IA por tier
LIMITES_MENSAIS: dict[str, int] = {
    PlanTier.PROFISSIONAL.value: 100,
    PlanTier.ENTERPRISE.value: 1000,
}

CUSTO_POR_TOKEN_ENTRADA = Decimal("0.00000025")
CUSTO_POR_TOKEN_SAIDA = Decimal("0.00000125")


def _inicio_mes() -> datetime:
    agora = datetime.now(timezone.utc)
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _uso_mensal_plano(tenant_id: uuid.UUID, session: AsyncSession) -> int:
    """Conta usos de IA via PLANO no mês corrente."""
    stmt = (
        select(func.count(IAUso.id))
        .where(
            IAUso.tenant_id == tenant_id,
            IAUso.status == "SUCESSO",
            IAUso.fonte_consumo == "PLANO",
            IAUso.created_at >= _inicio_mes(),
        )
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def creditos_extras_ativos(tenant_id: uuid.UUID, session: AsyncSession) -> int:
    """Retorna total de créditos extras disponíveis (não expirados, não esgotados)."""
    agora = datetime.now(timezone.utc)
    stmt = (
        select(
            func.sum(IACreditosPacote.quantidade_creditos - IACreditosPacote.creditos_usados)
        )
        .where(
            IACreditosPacote.tenant_id == tenant_id,
            IACreditosPacote.status == "ATIVO",
            and_(
                (IACreditosPacote.expira_em == None) | (IACreditosPacote.expira_em > agora)
            ),
        )
    )
    result = (await session.execute(stmt)).scalar_one()
    return int(result or 0)


async def creditos_extras_usados(tenant_id: uuid.UUID, session: AsyncSession) -> int:
    """Retorna total de créditos de pacotes já consumidos."""
    stmt = (
        select(func.count(IAUso.id))
        .where(
            IAUso.tenant_id == tenant_id,
            IAUso.status == "SUCESSO",
            IAUso.fonte_consumo == "PACOTE",
        )
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def verificar_limite_ia(
    tenant_id: uuid.UUID,
    tier: str,
    session: AsyncSession,
) -> tuple[bool, str]:
    """
    Retorna (pode_usar, fonte) onde fonte é 'PLANO' ou 'PACOTE'.
    Lógica: usa plano primeiro; se plano esgotado, usa créditos extras.
    """
    limite = LIMITES_MENSAIS.get(tier)
    if limite is None:
        return False, "PLANO"

    uso_plano = await _uso_mensal_plano(tenant_id, session)
    if uso_plano < limite:
        return True, "PLANO"

    # Plano esgotado — verifica créditos extras
    extras = await creditos_extras_ativos(tenant_id, session)
    if extras > 0:
        return True, "PACOTE"

    return False, "PLANO"


async def consumir_credito_pacote(tenant_id: uuid.UUID, session: AsyncSession) -> bool:
    """Incrementa creditos_usados no pacote mais antigo ativo. Retorna True se consumiu."""
    agora = datetime.now(timezone.utc)
    stmt = (
        select(IACreditosPacote)
        .where(
            IACreditosPacote.tenant_id == tenant_id,
            IACreditosPacote.status == "ATIVO",
            and_(
                (IACreditosPacote.expira_em == None) | (IACreditosPacote.expira_em > agora)
            ),
            IACreditosPacote.creditos_usados < IACreditosPacote.quantidade_creditos,
        )
        .order_by(IACreditosPacote.adquirido_em)
        .limit(1)
    )
    pacote = (await session.execute(stmt)).scalar_one_or_none()
    if not pacote:
        return False

    pacote.creditos_usados += 1
    if pacote.creditos_usados >= pacote.quantidade_creditos:
        pacote.status = "ESGOTADO"
    await session.flush()
    return True


async def consultar_creditos(tenant_id: uuid.UUID, tier: str | None, session: AsyncSession) -> dict:
    """Retorna resumo combinado de limite do plano + créditos extras."""
    limite = LIMITES_MENSAIS.get(tier or "")
    uso_plano = await _uso_mensal_plano(tenant_id, session) if limite else 0
    extras_disponiveis = await creditos_extras_ativos(tenant_id, session)
    extras_usados = await creditos_extras_usados(tenant_id, session)

    return {
        "limite_plano": limite,
        "usado_plano": uso_plano,
        "creditos_extras": extras_disponiveis + extras_usados,  # total adquirido
        "creditos_extras_disponiveis": extras_disponiveis,
        "creditos_extras_usados": extras_usados,
        "total_disponivel": (
            max(0, (limite or 0) - uso_plano) + extras_disponiveis
        ),
    }


async def solicitar_creditos(
    tenant_id: uuid.UUID,
    quantidade: int,
    session: AsyncSession,
) -> IACreditosPacote:
    """Registra intenção comercial de créditos extras. Sem pagamento."""
    pacote = IACreditosPacote(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        quantidade_creditos=quantidade,
        creditos_usados=0,
        origem="SOLICITACAO",
        status="ATIVO",
    )
    session.add(pacote)
    await session.flush()
    logger.info(f"Solicitação de {quantidade} créditos de IA para tenant={tenant_id}")
    return pacote


async def consultar_uso_hibrido(
    tenant_id: uuid.UUID,
    tier: str | None,
    session: AsyncSession,
) -> dict:
    """Retorna breakdown de consumo por fonte (PLANO vs PACOTE) para o mês corrente."""
    limite = LIMITES_MENSAIS.get(tier or "")
    uso_plano = await _uso_mensal_plano(tenant_id, session) if limite is not None else 0
    uso_pacotes = await creditos_extras_usados(tenant_id, session)
    extras_disponiveis = await creditos_extras_ativos(tenant_id, session)
    plano_esgotado = limite is not None and uso_plano >= limite
    usando_creditos_extras = plano_esgotado and (uso_pacotes > 0 or extras_disponiveis > 0)

    return {
        "uso_plano": uso_plano,
        "uso_pacotes": uso_pacotes,
        "creditos_extras_disponiveis": extras_disponiveis,
        "usando_creditos_extras": usando_creditos_extras,
    }


async def consultar_uso_mensal(
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    """Retorna resumo de uso de IA no mês corrente."""
    inicio_mes = _inicio_mes()
    stmt = (
        select(
            func.count(IAUso.id).label("total"),
            func.sum(IAUso.tokens_entrada).label("tokens_entrada"),
            func.sum(IAUso.tokens_saida).label("tokens_saida"),
            func.sum(IAUso.custo_estimado).label("custo_total"),
        )
        .where(
            IAUso.tenant_id == tenant_id,
            IAUso.created_at >= inicio_mes,
        )
    )
    row = (await session.execute(stmt)).one()
    return {
        "total_chamadas": int(row.total or 0),
        "tokens_entrada": int(row.tokens_entrada or 0),
        "tokens_saida": int(row.tokens_saida or 0),
        "custo_estimado_usd": float(row.custo_total or 0),
        "mes_referencia": inicio_mes.strftime("%Y-%m"),
    }


async def registrar_uso_ia(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    origem: str,
    status: str,
    modelo: Optional[str] = None,
    tokens_entrada: int = 0,
    tokens_saida: int = 0,
    usuario_id: Optional[uuid.UUID] = None,
    fonte_consumo: Optional[str] = None,
) -> None:
    """Persiste um registro de uso. Silencia erros para não quebrar o fluxo principal."""
    try:
        custo = None
        if tokens_entrada or tokens_saida:
            custo = (
                Decimal(tokens_entrada) * CUSTO_POR_TOKEN_ENTRADA
                + Decimal(tokens_saida) * CUSTO_POR_TOKEN_SAIDA
            )
        session.add(IAUso(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            origem=origem,
            modelo=modelo,
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            custo_estimado=custo,
            status=status,
            fonte_consumo=fonte_consumo,
        ))
        await session.flush()
    except Exception as exc:
        logger.warning(f"Falha ao registrar uso de IA (tenant={tenant_id}): {exc}")
