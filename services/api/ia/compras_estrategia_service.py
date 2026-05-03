"""
Serviço de IA para estratégia de compra (Step 168).

Segurança:
- Habilitada por plano (PROFISSIONAL/ENTERPRISE)
- Variável ANTHROPIC_API_KEY obrigatória
- Fallback determinístico em qualquer falha
- IA nunca executa compras — apenas recomenda
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
from ia.insights_service import tenant_tem_ia


async def _persistir_recomendacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    ctx: "ContextoCompra",
    resultado: "EstrategiaCompra",
    usuario_id: uuid.UUID | None,
    item_id: uuid.UUID | None = None,
) -> None:
    """Persiste a recomendação na tabela de auditoria. Silencia falhas."""
    try:
        from ia.models import IAComprasRecomendacao
        rec = IAComprasRecomendacao(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            item_id=item_id,
            solicitacao_id=uuid.UUID(ctx.solicitacao_id) if ctx.solicitacao_id else None,
            estrategia=resultado.estrategia,
            resumo=resultado.resumo,
            justificativas=resultado.justificativas,
            nivel_confianca=resultado.nivel_confianca,
            fonte=resultado.fonte,
            limite_atingido=resultado.limite_atingido,
        )
        session.add(rec)
        await session.flush()
    except Exception as exc:
        logger.warning(f"Falha ao persistir recomendação IA (tenant={tenant_id}): {exc}")


async def _buscar_prompt_ativo(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> str | None:
    """Retorna conteúdo da versão ativa do prompt: tenant > global > None (fallback hardcoded).
    Silencia falhas para não bloquear o fluxo principal.
    """
    try:
        from ia.models import IAPromptVersao
        from sqlalchemy import select, or_

        stmt = (
            select(IAPromptVersao)
            .where(
                IAPromptVersao.contexto == "COMPRAS_ESTRATEGIA",
                IAPromptVersao.ativo == True,  # noqa: E712
                or_(IAPromptVersao.tenant_id == tenant_id, IAPromptVersao.tenant_id.is_(None)),
            )
            .order_by(
                # tenant-specific primeiro; NULL (global) depois
                IAPromptVersao.tenant_id.is_(None),
                IAPromptVersao.created_at.desc(),
            )
            .limit(1)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        return row.conteudo if row else None
    except Exception as exc:
        logger.warning(f"Falha ao buscar prompt ativo (tenant={tenant_id}): {exc}")
        return None


async def _buscar_feedback_negativo(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[dict]:
    """Busca até 5 recomendações recentes avaliadas como não úteis (Step 172).
    Prioriza fonte=IA. Retorna lista vazia se não houver ou em caso de erro.
    Nunca afeta cálculos — apenas enriquece contexto do prompt.
    """
    try:
        from ia.models import IAComprasRecomendacao
        from sqlalchemy import select, desc, case

        stmt = (
            select(
                IAComprasRecomendacao.estrategia,
                IAComprasRecomendacao.resumo,
                IAComprasRecomendacao.feedback_comentario,
                IAComprasRecomendacao.fonte,
            )
            .where(
                IAComprasRecomendacao.tenant_id == tenant_id,
                IAComprasRecomendacao.feedback_util == False,  # noqa: E712
            )
            .order_by(
                # fonte IA primeiro, depois determinístico
                case((IAComprasRecomendacao.fonte == "IA", 0), else_=1),
                desc(IAComprasRecomendacao.created_at),
            )
            .limit(5)
        )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "estrategia": r.estrategia,
                "resumo": r.resumo,
                "comentario": r.feedback_comentario or "",
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning(f"Falha ao buscar feedback negativo: {exc}")
        return []


@dataclass
class ContextoCompra:
    item_nome: str = ""
    solicitacao_id: Optional[str] = None
    quantidade: float = 0.0
    unidade: str = ""
    # Preço ideal
    preco_minimo: Optional[float] = None
    preco_ideal: Optional[float] = None
    preco_maximo: Optional[float] = None
    # Melhor fornecedor
    melhor_fornecedor: Optional[str] = None
    score_melhor: Optional[float] = None
    # Histórico
    ultimo_preco: Optional[float] = None
    preco_medio_historico: Optional[float] = None
    qtd_compras_historicas: int = 0
    # Cotações atuais
    cotacoes: list[dict] = field(default_factory=list)
    # Consistência
    consistencia_melhor_fornecedor: Optional[str] = None


@dataclass
class EstrategiaCompra:
    resumo: str = ""
    estrategia: str = "Negociar"  # Comprar agora | Negociar | Aguardar
    justificativas: list[str] = field(default_factory=list)
    nivel_confianca: float = 0.7
    fonte: str = "IA"
    ia_disponivel: bool = True
    limite_atingido: bool = False


def _fallback_deterministico(ctx: ContextoCompra) -> EstrategiaCompra:
    """Lógica determinística quando IA não está disponível."""
    justificativas = []
    estrategia = "Negociar"
    confianca = 0.65

    # Verifica se há cotações
    if not ctx.cotacoes:
        return EstrategiaCompra(
            resumo="Sem cotações disponíveis para análise. Solicite ao menos uma cotação antes de decidir.",
            estrategia="Aguardar",
            justificativas=["Nenhuma cotação registrada para este item"],
            nivel_confianca=0.5,
            fonte="DETERMINISTICO",
        )

    # Menor preço das cotações atuais
    precos_atuais = [c.get("valor_unitario", 0) for c in ctx.cotacoes if c.get("valor_unitario")]
    menor_preco_atual = min(precos_atuais) if precos_atuais else None

    if menor_preco_atual and ctx.preco_ideal:
        if menor_preco_atual <= ctx.preco_ideal:
            estrategia = "Comprar agora"
            justificativas.append(f"Preço atual (R$ {menor_preco_atual:.2f}) está dentro da faixa ideal")
            confianca = 0.82
        elif menor_preco_atual <= ctx.preco_maximo:
            estrategia = "Negociar"
            justificativas.append(f"Preço acima do ideal (R$ {ctx.preco_ideal:.2f}) mas abaixo do máximo")
            confianca = 0.70
        else:
            estrategia = "Aguardar"
            justificativas.append(f"Preço acima do máximo recomendado (R$ {ctx.preco_maximo:.2f})")
            confianca = 0.75

    if ctx.melhor_fornecedor:
        justificativas.append(f"Fornecedor recomendado: {ctx.melhor_fornecedor}")

    if ctx.consistencia_melhor_fornecedor == "ESTAVEL":
        justificativas.append("Fornecedor com histórico de preço estável")
        confianca = min(confianca + 0.05, 0.95)

    if not justificativas:
        justificativas = ["Análise baseada nos dados disponíveis"]

    resumo = (
        f"Recomendamos '{estrategia}' para {ctx.item_nome}. "
        f"{'Preço dentro da faixa ideal detectada.' if estrategia == 'Comprar agora' else 'Avalie negociar melhores condições com o fornecedor.'}"
    )

    return EstrategiaCompra(
        resumo=resumo,
        estrategia=estrategia,
        justificativas=justificativas[:4],
        nivel_confianca=round(confianca, 2),
        fonte="DETERMINISTICO",
    )


def _montar_prompt(
    ctx: ContextoCompra,
    feedback_negativo: list[dict] | None = None,
    template: str | None = None,
) -> str:
    cotacoes_fmt = [
        {"fornecedor": c.get("fornecedor_nome"), "preco_unitario": c.get("valor_unitario"), "prazo_dias": c.get("prazo_entrega_dias")}
        for c in ctx.cotacoes[:5]
    ]
    dados = {
        "item": ctx.item_nome,
        "quantidade_solicitada": f"{ctx.quantidade} {ctx.unidade}",
        "faixa_preco_referencia": {
            "minimo": ctx.preco_minimo,
            "ideal": ctx.preco_ideal,
            "maximo": ctx.preco_maximo,
        },
        "melhor_fornecedor_historico": ctx.melhor_fornecedor,
        "score_melhor_fornecedor": ctx.score_melhor,
        "preco_medio_historico": ctx.preco_medio_historico,
        "ultimo_preco_pago": ctx.ultimo_preco,
        "compras_anteriores": ctx.qtd_compras_historicas,
        "consistencia_melhor_fornecedor": ctx.consistencia_melhor_fornecedor,
        "cotacoes_atuais": cotacoes_fmt,
    }

    feedback_block = ""
    if feedback_negativo:
        itens = "\n".join(
            f'- Estratégia "{f["estrategia"]}": "{f["resumo"]}"'
            + (f' (comentário: {f["comentario"]})' if f.get("comentario") else "")
            for f in feedback_negativo
        )
        feedback_block = f"""
FEEDBACKS NEGATIVOS RECENTES (recomendações avaliadas como não úteis pelo gestor):
{itens}

INSTRUÇÃO: Evite repetir padrões de recomendação semelhantes aos acima. Se os dados apontarem para a mesma direção, ajuste a justificativa para ser mais específica e acionável.
"""

    dados_json = json.dumps(dados, ensure_ascii=False, indent=2)

    # Usa template versionado se disponível; substitui placeholders se presentes
    if template:
        try:
            return template.format(
                dados=dados_json,
                feedback_block=feedback_block.strip(),
            )
        except (KeyError, ValueError):
            # Template com placeholders incompatíveis → fallback hardcoded
            logger.warning("Template versionado com placeholders inválidos — usando prompt hardcoded")

    return f"""Você é um especialista em compras agrícolas no mercado brasileiro.

Com base APENAS nos dados abaixo, gere uma estratégia de compra objetiva.

REGRAS OBRIGATÓRIAS:
- Não invente preços ou fornecedores fora dos dados
- Estratégia deve ser exatamente uma de: "Comprar agora", "Negociar", "Aguardar"
- Justificativas: máximo 4 itens diretos e acionáveis
- nivel_confianca: número entre 0 e 1 (ex: 0.85)
- Tom: direto, prático, voltado ao gestor de compras rural
{feedback_block}
DADOS:
{dados_json}

Responda em JSON com exatamente este formato:
{{
  "resumo": "frase única objetiva sobre a decisão",
  "estrategia": "Comprar agora" | "Negociar" | "Aguardar",
  "justificativas": ["motivo 1", "motivo 2", "motivo 3"],
  "nivel_confianca": 0.85
}}"""


async def _chamar_ia(
    ctx: ContextoCompra,
    feedback_negativo: list[dict] | None = None,
    prompt_template: str | None = None,
) -> EstrategiaCompra:
    """Chama Anthropic Claude. Lança exceção se falhar."""
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    prompt = _montar_prompt(ctx, feedback_negativo or [], template=prompt_template)

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
    start = content.find("{")
    end = content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    estrategia_valida = parsed.get("estrategia", "Negociar")
    if estrategia_valida not in ("Comprar agora", "Negociar", "Aguardar"):
        estrategia_valida = "Negociar"

    return EstrategiaCompra(
        resumo=parsed.get("resumo", ""),
        estrategia=estrategia_valida,
        justificativas=parsed.get("justificativas", [])[:4],
        nivel_confianca=float(parsed.get("nivel_confianca", 0.75)),
        fonte="IA",
    )


async def gerar_estrategia_compra(
    ctx: ContextoCompra,
    *,
    tenant_id: uuid.UUID | None = None,
    session: AsyncSession | None = None,
    tier: str | None = None,
    usuario_id: uuid.UUID | None = None,
    item_id: uuid.UUID | None = None,
) -> EstrategiaCompra:
    """
    Ponto de entrada principal.
    1. Verifica plano do tenant
    2. Verifica limite mensal
    3. Chama IA; fallback determinístico em qualquer falha
    4. Registra uso
    """
    verificar_limite_ia = _usage_svc.verificar_limite_ia
    registrar_uso_ia = _usage_svc.registrar_uso_ia

    # 1. Verifica plano
    ia_plano = False
    tier_value: str | None = tier
    if tenant_id and session:
        ia_plano = await tenant_tem_ia(tenant_id, session)
        if ia_plano and not tier_value:
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
        resultado = _fallback_deterministico(ctx)
        resultado.ia_disponivel = False
        if tenant_id and session:
            await _persistir_recomendacao(session, tenant_id, ctx, resultado, usuario_id, item_id)
        return resultado

    ia_enabled = os.getenv("IA_ENABLED", "false").lower() == "true"
    if not ia_enabled:
        resultado = _fallback_deterministico(ctx)
        resultado.ia_disponivel = False
        if tenant_id and session:
            await _persistir_recomendacao(session, tenant_id, ctx, resultado, usuario_id, item_id)
        return resultado

    # 2. Verifica limite mensal
    fonte_consumo = "PLANO"
    if tenant_id and session and tier_value:
        pode_usar, fonte_consumo = await verificar_limite_ia(tenant_id, tier_value, session)
        if not pode_usar:
            if session and tenant_id:
                await registrar_uso_ia(session, tenant_id, "estrategia_compra", "FALLBACK", usuario_id=usuario_id)
            resultado = _fallback_deterministico(ctx)
            resultado.ia_disponivel = True
            resultado.limite_atingido = True
            if tenant_id and session:
                await _persistir_recomendacao(session, tenant_id, ctx, resultado, usuario_id, item_id)
            return resultado

    # 3. Chama IA
    modelo = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    feedback_negativo: list[dict] = []
    prompt_template: str | None = None
    if tenant_id and session:
        feedback_negativo = await _buscar_feedback_negativo(session, tenant_id)
        prompt_template = await _buscar_prompt_ativo(session, tenant_id)
    try:
        resultado = await _chamar_ia(ctx, feedback_negativo, prompt_template=prompt_template)
        resultado.ia_disponivel = True
        if tenant_id and session:
            if fonte_consumo == "PACOTE":
                await _usage_svc.consumir_credito_pacote(tenant_id, session)
            await registrar_uso_ia(
                session, tenant_id, "estrategia_compra", "SUCESSO",
                modelo=modelo, usuario_id=usuario_id, fonte_consumo=fonte_consumo,
            )
            await _persistir_recomendacao(session, tenant_id, ctx, resultado, usuario_id, item_id)
        return resultado
    except Exception as exc:
        logger.warning(f"IA estrategia_compra falhou, usando fallback: {exc}")
        resultado = _fallback_deterministico(ctx)
        resultado.ia_disponivel = True
        if tenant_id and session:
            await registrar_uso_ia(session, tenant_id, "estrategia_compra", "ERRO",
                                   modelo=modelo, usuario_id=usuario_id)
            await _persistir_recomendacao(session, tenant_id, ctx, resultado, usuario_id, item_id)
        return resultado
