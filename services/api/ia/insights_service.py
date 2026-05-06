"""
Camada opcional de IA para enriquecimento textual do resumo financeiro.

Segurança:
- Habilitada por plano do tenant (PROFISSIONAL ou ENTERPRISE)
- Variável IA_ENABLED=true necessária adicionalmente (custo controlado)
- Fallback para resumo determinístico em qualquer falha
- IA nunca recalcula valores — apenas reescreve texto com base em dados fornecidos
- Sem alucinação: prompt proíbe inventar números
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from ia import usage_service as _usage_svc


@dataclass
class ContextoSafra:
    total_custos: float
    categoria_dominante: Optional[str]
    margem: Optional[float]
    variacao_mensal_pct: Optional[float]
    alertas: list[str] = field(default_factory=list)
    recomendacoes: list[str] = field(default_factory=list)
    plano_acoes: list[str] = field(default_factory=list)


@dataclass
class ResumoConsultivo:
    resumo: str
    recomendacoes: list[str]
    nivel_confianca: str  # ALTO | MEDIO | BAIXO
    fonte: str           # IA | DETERMINISTICO
    ia_disponivel: bool = False  # True se o plano do tenant inclui IA
    limite_atingido: bool = False  # True se cota mensal esgotada


def _ia_globalmente_habilitada() -> bool:
    return os.getenv("IA_ENABLED", "false").lower() in ("true", "1", "yes")


async def tenant_tem_ia(tenant_id: uuid.UUID, session: AsyncSession) -> bool:
    """Verifica se o tenant tem plano PROFISSIONAL ou ENTERPRISE (acesso à IA)."""
    from sqlalchemy import select
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from core.constants import PlanTier

    try:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        tier_str = result.scalar_one_or_none()
        if not tier_str:
            return False
        tier = PlanTier(tier_str)
        return tier >= PlanTier.PROFISSIONAL
    except Exception as exc:
        logger.warning(f"Falha ao verificar tier do tenant {tenant_id}: {exc}")
        return False


def _resumo_deterministico(ctx: ContextoSafra) -> ResumoConsultivo:
    """Resumo baseado em regras — sempre disponível como fallback."""
    fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    partes: list[str] = []
    if ctx.total_custos == 0:
        partes.append("Nenhum custo registrado nesta safra ainda.")
    else:
        partes.append(f"Sua safra acumula {fmt(ctx.total_custos)} em custos.")
        if ctx.categoria_dominante:
            partes.append(f"A maior concentração está em {ctx.categoria_dominante}.")
        if ctx.margem is not None:
            if ctx.margem >= 0:
                partes.append(f"O cenário base apresenta margem positiva de {fmt(ctx.margem)}.")
            else:
                partes.append(f"O cenário base apresenta margem negativa de {fmt(abs(ctx.margem))}.")
        if ctx.variacao_mensal_pct is not None and abs(ctx.variacao_mensal_pct) > 10:
            sinal = "aumentaram" if ctx.variacao_mensal_pct > 0 else "reduziram"
            partes.append(f"Os custos {sinal} {abs(ctx.variacao_mensal_pct):.1f}% no último período.")

    recs = ctx.recomendacoes[:3] or ["Revisar custos por categoria", "Comparar cenários econômicos"]

    return ResumoConsultivo(
        resumo=" ".join(partes),
        recomendacoes=recs,
        nivel_confianca="ALTO",
        fonte="DETERMINISTICO",
    )


def _montar_prompt(ctx: ContextoSafra) -> str:
    fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    dados = {
        "total_custos": fmt(ctx.total_custos) if ctx.total_custos else "Sem custos",
        "categoria_dominante": ctx.categoria_dominante or "não identificada",
        "margem": fmt(ctx.margem) if ctx.margem is not None else "não calculada",
        "variacao_mensal": f"{ctx.variacao_mensal_pct:.1f}%" if ctx.variacao_mensal_pct is not None else "não disponível",
        "alertas": ctx.alertas[:3],
        "recomendacoes_base": ctx.recomendacoes[:3],
        "plano_acoes": ctx.plano_acoes[:3],
    }

    return f"""Você é um consultor agrícola especializado em análise financeira de safras brasileiras.

Com base APENAS nos dados abaixo, produza um resumo consultivo profissional em português.

REGRAS OBRIGATÓRIAS:
- Não invente números, valores ou percentuais que não estejam nos dados
- Use apenas os valores fornecidos
- Tom: consultivo, direto, útil ao produtor rural
- Resumo: máximo 3 frases fluentes e naturais
- Recomendações: máximo 3 itens concisos e acionáveis

DADOS DA SAFRA:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Responda em JSON com exatamente este formato:
{{
  "resumo": "texto em português",
  "recomendacoes": ["ação 1", "ação 2", "ação 3"]
}}"""


async def gerar_resumo_consultivo(
    ctx: ContextoSafra,
    *,
    tenant_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
    tier: str | None = None,
    usuario_id: uuid.UUID | None = None,
) -> ResumoConsultivo:
    """
    Ponto de entrada principal.
    1. Verifica plano do tenant (PROFISSIONAL/ENTERPRISE exigido)
    2. Verifica flag global IA_ENABLED
    3. Verifica limite mensal de uso
    4. Tenta IA; fallback determinístico em qualquer falha
    5. Registra uso (SUCESSO | ERRO | FALLBACK)
    """
    verificar_limite_ia = _usage_svc.verificar_limite_ia
    registrar_uso_ia = _usage_svc.registrar_uso_ia

    # 1. Verifica plano
    ia_plano = False
    tier_value: str | None = tier
    if tenant_id and session:
        ia_plano = await tenant_tem_ia(tenant_id, session)
        if ia_plano and not tier_value:
            # Descobre o tier para verificar limite
            try:
                from sqlalchemy import select
                from core.models.billing import AssinaturaTenant, PlanoAssinatura
                stmt = (
                    select(PlanoAssinatura.plan_tier)
                    .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                    .where(
                        AssinaturaTenant.tenant_id == tenant_id,
                        AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                        AssinaturaTenant.tipo_assinatura == "TENANT",
                    ).limit(1)
                )
                tier_value = (await session.execute(stmt)).scalar_one_or_none()
            except Exception:
                pass

    if not ia_plano:
        logger.bind(
            event="monetization_blocked", surface="ia.resumo_consultivo",
            feature="ia_resumo", tenant_id=str(tenant_id) if tenant_id else None,
            reason="insufficient_tier",
        ).info("monetization_blocked")
        resultado = _resumo_deterministico(ctx)
        resultado.ia_disponivel = False
        return resultado

    if not _ia_globalmente_habilitada():
        resultado = _resumo_deterministico(ctx)
        resultado.ia_disponivel = False
        return resultado

    # 2. Verifica limite mensal (plano + créditos extras)
    fonte_consumo = "PLANO"
    if tenant_id and session and tier_value:
        pode_usar, fonte_consumo = await verificar_limite_ia(tenant_id, tier_value, session)
        if not pode_usar:
            logger.bind(
                event="ia_limite_atingido", tenant_id=str(tenant_id), tier=tier_value,
            ).info("ia_limite_atingido")
            if session and tenant_id:
                await registrar_uso_ia(session, tenant_id, "resumo_consultivo", "FALLBACK",
                                       usuario_id=usuario_id)
            resultado = _resumo_deterministico(ctx)
            resultado.ia_disponivel = True
            resultado.limite_atingido = True
            return resultado

    # 3. Chama IA
    modelo = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    try:
        resultado = await _chamar_ia(ctx)
        resultado.ia_disponivel = True
        if tenant_id and session:
            # Consome crédito do pacote se a fonte for PACOTE
            if fonte_consumo == "PACOTE":
                await _usage_svc.consumir_credito_pacote(tenant_id, session)
            await registrar_uso_ia(
                session, tenant_id, "resumo_consultivo", "SUCESSO",
                modelo=modelo, usuario_id=usuario_id, fonte_consumo=fonte_consumo,
            )
        return resultado
    except Exception as exc:
        logger.warning(f"IA falhou, usando fallback determinístico: {exc}")
        if tenant_id and session:
            await registrar_uso_ia(session, tenant_id, "resumo_consultivo", "ERRO",
                                   modelo=modelo, usuario_id=usuario_id)
        resultado = _resumo_deterministico(ctx)
        resultado.nivel_confianca = "MEDIO"
        resultado.ia_disponivel = True
        return resultado



async def _chamar_ia(ctx: ContextoSafra) -> ResumoConsultivo:
    """Chama Anthropic Claude via API. Requer ANTHROPIC_API_KEY no ambiente."""
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    prompt = _montar_prompt(ctx)
    model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()

    content = resp.json()["content"][0]["text"].strip()

    # Extrai JSON da resposta (pode vir com texto extra)
    start = content.find("{")
    end = content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    resumo = str(parsed.get("resumo", "")).strip()
    recs = [str(r) for r in parsed.get("recomendacoes", []) if r][:3]

    if not resumo:
        raise ValueError("IA retornou resumo vazio")

    return ResumoConsultivo(
        resumo=resumo,
        recomendacoes=recs,
        nivel_confianca="ALTO",
        fonte="IA",
    )


class IAInsightsService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def obter_alertas(self, safra_id: uuid.UUID) -> list[dict]:
        """Recupera alertas inteligentes ativos (não visualizados ou ignorados) da safra."""
        from sqlalchemy import select, and_
        from ia.models import IAAlertaHistorico

        stmt = (
            select(IAAlertaHistorico)
            .where(
                and_(
                    IAAlertaHistorico.tenant_id == self.tenant_id,
                    IAAlertaHistorico.safra_id == safra_id,
                    IAAlertaHistorico.visualizado_em == None,
                    IAAlertaHistorico.ignorado == False,
                    IAAlertaHistorico.acao_executada == False
                )
            )
            .order_by(IAAlertaHistorico.created_at.desc())
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        return [
            {
                "id": r.id,
                "tipo": r.tipo_alerta,
                "titulo": r.titulo,
                "descricao": r.mensagem,
                "nivel": r.gravidade,
                "created_at": r.created_at,
                "link": r.parametros_json.get("link") if r.parametros_json else None
            }
            for r in rows
        ]
