import urllib.parse
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field
from loguru import logger

from core.dependencies import get_session, get_tenant_id, get_current_user_claims
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from ia.usage_service import (
    consultar_uso_mensal, consultar_creditos, solicitar_creditos,
    consultar_uso_hibrido, LIMITES_MENSAIS,
)
from ia.models import IAUso

router = APIRouter(prefix="/ia", tags=["IA — Uso"])


class ResumoCreditosIA(BaseModel):
    limite_plano: Optional[int] = None
    usado_plano: int = 0
    creditos_extras: int = 0
    creditos_extras_disponiveis: int = 0
    creditos_extras_usados: int = 0
    total_disponivel: int = 0


class SolicitarCreditosPayload(BaseModel):
    quantidade: int = Field(..., ge=10, le=10000)


class SolicitarCreditosResponse(BaseModel):
    id: str
    protocolo: str
    quantidade: int
    status: str
    mensagem: str


# ── Precificação centralizada ────────────────────────────────────────────────
# Tabela de preços por faixa (R$/crédito) — mínimo → preço_unitário
_PRECO_POR_CREDITO: list[tuple[int, Decimal]] = [
    (1000, Decimal("0.07")),
    (500,  Decimal("0.08")),
    (200,  Decimal("0.09")),
    (0,    Decimal("0.10")),
]

# Custo médio estimado por crédito em R$ (baseado no custo LLM + infra)
CUSTO_ESTIMADO_CREDITO_IA = Decimal("0.035")

# Margem mínima aceitável (percentual). Checkout abaixo disso é bloqueado.
MARGEM_MINIMA_IA_PERCENTUAL = Decimal("30")

_WHATSAPP_NUMERO = "5511999999999"  # substituir pelo número comercial real


def _calcular_valor(quantidade: int) -> Decimal:
    for minimo, preco_unitario in _PRECO_POR_CREDITO:
        if quantidade >= minimo:
            return (preco_unitario * quantidade).quantize(Decimal("0.01"))
    return (Decimal("0.10") * quantidade).quantize(Decimal("0.01"))


def _calcular_margem(valor_total: Decimal, quantidade: int) -> dict:
    """Retorna custo_estimado, margem_estimada e margem_percentual."""
    custo = (CUSTO_ESTIMADO_CREDITO_IA * quantidade).quantize(Decimal("0.01"))
    margem = (valor_total - custo).quantize(Decimal("0.01"))
    pct = ((margem / valor_total) * 100).quantize(Decimal("0.01")) if valor_total else Decimal("0")
    return {
        "custo_estimado": custo,
        "margem_estimada": margem,
        "margem_percentual": pct,
    }


def _validar_margem(margem_percentual: Decimal) -> None:
    if margem_percentual < MARGEM_MINIMA_IA_PERCENTUAL:
        raise HTTPException(
            status_code=422,
            detail=f"Margem estimada ({margem_percentual}%) abaixo do mínimo permitido ({MARGEM_MINIMA_IA_PERCENTUAL}%).",
        )


def _gerar_link_pagamento(protocolo: str, quantidade: int, valor: Decimal) -> str:
    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    mensagem = (
        f"Olá! Gostaria de finalizar a compra de {quantidade} créditos de IA "
        f"(protocolo {protocolo}). Valor: {valor_fmt}."
    )
    return f"https://wa.me/{_WHATSAPP_NUMERO}?text={urllib.parse.quote(mensagem)}"


class CheckoutPayload(BaseModel):
    quantidade: int = Field(..., ge=10, le=10000)


class CheckoutResponse(BaseModel):
    link_pagamento: str
    valor_estimado: float
    protocolo: str
    custo_estimado: float
    margem_estimada: float
    margem_percentual: float


class ResumoUsoIA(BaseModel):
    # campos originais — backward compat
    plano: Optional[str] = None
    limite_mensal: Optional[int] = None
    usado_mes: int = 0
    restante: Optional[int] = None
    percentual_uso: float = 0.0
    custo_estimado_mes: float = 0.0
    ia_disponivel: bool = False
    # campos híbridos (step 121)
    uso_plano: int = 0
    uso_pacotes: int = 0
    creditos_extras_disponiveis: int = 0
    usando_creditos_extras: bool = False


class RegistroHistoricoIA(BaseModel):
    data: datetime
    origem: str
    status: str
    tokens_entrada: int
    tokens_saida: int
    custo_estimado: Optional[float] = None


def _assinatura_ativa_filter():
    return AssinaturaTenant.status.in_(["ATIVA", "TRIAL"])


async def _get_tier(tenant_id: uuid.UUID, session: AsyncSession, claims: dict) -> str | None:
    tier_str = claims.get("plan_tier")
    if not tier_str:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                _assinatura_ativa_filter(),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            ).limit(1)
        )
        tier_str = (await session.execute(stmt)).scalar_one_or_none()
    return tier_str


@router.get("/uso/resumo", response_model=ResumoUsoIA)
async def resumo_uso_ia(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    tier = await _get_tier(tenant_id, session, claims)
    uso = await consultar_uso_mensal(tenant_id, session)
    hibrido = await consultar_uso_hibrido(tenant_id, tier, session)
    limite = LIMITES_MENSAIS.get(tier or "")
    usado = uso["total_chamadas"]
    ia_disponivel = limite is not None

    return ResumoUsoIA(
        plano=tier,
        limite_mensal=limite,
        usado_mes=usado,
        restante=max(0, limite - usado) if limite is not None else None,
        percentual_uso=round(usado / limite * 100, 1) if limite else 0.0,
        custo_estimado_mes=round(uso["custo_estimado_usd"], 4),
        ia_disponivel=ia_disponivel,
        uso_plano=hibrido["uso_plano"],
        uso_pacotes=hibrido["uso_pacotes"],
        creditos_extras_disponiveis=hibrido["creditos_extras_disponiveis"],
        usando_creditos_extras=hibrido["usando_creditos_extras"],
    )


@router.get("/uso/historico", response_model=list[RegistroHistoricoIA])
async def historico_uso_ia(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(IAUso)
        .where(IAUso.tenant_id == tenant_id)
        .order_by(desc(IAUso.created_at))
        .limit(limit)
    )
    registros = list((await session.execute(stmt)).scalars().all())
    return [
        RegistroHistoricoIA(
            data=r.created_at,
            origem=r.origem,
            status=r.status,
            tokens_entrada=r.tokens_entrada,
            tokens_saida=r.tokens_saida,
            custo_estimado=float(r.custo_estimado) if r.custo_estimado is not None else None,
        )
        for r in registros
    ]


@router.get("/creditos", response_model=ResumoCreditosIA)
async def resumo_creditos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    tier = await _get_tier(tenant_id, session, claims)
    dados = await consultar_creditos(tenant_id, tier, session)
    return ResumoCreditosIA(**dados)


@router.post("/creditos/solicitar", response_model=SolicitarCreditosResponse, status_code=201)
async def solicitar_creditos_ia(
    body: SolicitarCreditosPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    pacote = await solicitar_creditos(tenant_id, body.quantidade, session)

    solicitacao = SolicitacaoComercial(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        tipo="CREDITOS_IA",
        origem="ia_creditos_adicionais",
        detalhes={"quantidade": body.quantidade, "pacote_id": str(pacote.id)},
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(solicitacao)
    await session.commit()

    protocolo = f"IA-{str(solicitacao.id)[:8].upper()}"
    logger.bind(
        event="upgrade_intention_created",
        tenant_id=str(tenant_id),
        tipo="CREDITOS_IA",
        origem="ia_creditos_adicionais",
        quantidade=body.quantidade,
        solicitacao_id=str(solicitacao.id),
    ).info("upgrade_intention_created")

    return SolicitarCreditosResponse(
        id=str(pacote.id),
        protocolo=protocolo,
        quantidade=pacote.quantidade_creditos,
        status=pacote.status,
        mensagem=f"Solicitação registrada com protocolo {protocolo}. Nossa equipe entrará em contato em breve.",
    )


@router.post("/creditos/checkout", response_model=CheckoutResponse, status_code=200)
async def checkout_creditos_ia(
    body: CheckoutPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Gera link de pagamento para créditos de IA e atualiza a solicitação comercial."""
    valor = _calcular_valor(body.quantidade)
    margem_info = _calcular_margem(valor, body.quantidade)
    _validar_margem(margem_info["margem_percentual"])

    # Busca solicitação ABERTA mais recente do tenant
    stmt = (
        select(SolicitacaoComercial)
        .where(
            SolicitacaoComercial.tenant_id == tenant_id,
            SolicitacaoComercial.tipo == "CREDITOS_IA",
            SolicitacaoComercial.status == "ABERTA",
        )
        .order_by(desc(SolicitacaoComercial.created_at))
        .limit(1)
    )
    solicitacao = (await session.execute(stmt)).scalar_one_or_none()

    detalhes_economicos = {
        "quantidade": body.quantidade,
        "valor_total": str(valor),
        "custo_estimado": str(margem_info["custo_estimado"]),
        "margem_estimada": str(margem_info["margem_estimada"]),
        "margem_percentual": str(margem_info["margem_percentual"]),
    }

    # Cria solicitação se não existir (checkout direto sem solicitar antes)
    if not solicitacao:
        usuario_id_str = claims.get("sub")
        usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
        solicitacao = SolicitacaoComercial(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            tipo="CREDITOS_IA",
            origem="ia_creditos_checkout",
            detalhes=detalhes_economicos,
            status="ABERTA",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(solicitacao)
        await session.flush()
    else:
        solicitacao.detalhes = {**(solicitacao.detalhes or {}), **detalhes_economicos}

    protocolo = f"IA-{str(solicitacao.id)[:8].upper()}"
    link = _gerar_link_pagamento(protocolo, body.quantidade, valor)

    solicitacao.valor_estimado = valor
    solicitacao.link_pagamento = link
    solicitacao.status_pagamento = "PENDENTE"
    solicitacao.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.bind(
        event="checkout_initiated",
        tenant_id=str(tenant_id),
        protocolo=protocolo,
        quantidade=body.quantidade,
        valor=str(valor),
        margem_percentual=str(margem_info["margem_percentual"]),
    ).info("checkout_initiated")

    return CheckoutResponse(
        link_pagamento=link,
        valor_estimado=float(valor),
        protocolo=protocolo,
        custo_estimado=float(margem_info["custo_estimado"]),
        margem_estimada=float(margem_info["margem_estimada"]),
        margem_percentual=float(margem_info["margem_percentual"]),
    )
