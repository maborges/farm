"""
Step 184 — IA Analisa o Resultado da Safra (DRE Intelligence).

Este serviço interpreta os dados da DRE Operacional e gera insights consultivos.
"""
from __future__ import annotations
import json
import os
import uuid
from dataclasses import dataclass, field
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from ia import usage_service as _usage_svc
from ia.insights_service import tenant_tem_ia, _ia_globalmente_habilitada

@dataclass
class ContextoDRE:
    receita_bruta: float
    custos_operacionais: float
    resultado_operacional: float
    margem_percentual: float
    breakdown_custos: list[dict] = field(default_factory=list)
    breakdown_receitas: list[dict] = field(default_factory=list)

@dataclass
class AnaliseDREIA:
    resumo: str
    pontos_positivos: list[str]
    pontos_atencao: list[str]
    recomendacoes: list[str]
    nivel_confianca: float
    fonte: str           # IA | DETERMINISTICO
    ia_disponivel: bool = False
    limite_atingido: bool = False

@dataclass
class ContextoSimulacao:
    receita_real: float
    custos_real: float
    resultado_real: float
    margem_real: float
    receita_simulada: float
    custos_simulados: float
    resultado_simulado: float
    margem_simulada: float
    ajuste_receita_pct: float
    ajuste_custos_pct: float

@dataclass
class AnaliseSimulacaoIA:
    impacto: str
    riscos: list[str]
    recomendacoes: list[str]
    nivel_confianca: float
    fonte: str = "IA"
    ia_disponivel: bool = False
    limite_atingido: bool = False

def _analise_deterministica(ctx: ContextoDRE) -> AnaliseDREIA:
    """Fallback determinístico baseado em regras simples."""
    resumo = f"A safra resultou em um resultado operacional de R$ {ctx.resultado_operacional:,.2f}."
    
    positivos = []
    if ctx.margem_percentual > 20:
        positivos.append("Margem operacional saudável (acima de 20%)")
    if ctx.receita_bruta > 0:
        positivos.append("Geração de receita confirmada")
        
    atencao = []
    if ctx.margem_percentual < 10:
        atencao.append("Margem operacional apertada (abaixo de 10%)")
    if ctx.custos_operacionais > ctx.receita_bruta:
        atencao.append("Custos superam as receitas no momento")
        
    recs = [
        "Revisar categorias de maior custo no breakdown",
        "Avaliar eficiência do uso de insumos",
        "Comparar resultado com o planejado inicialmente"
    ]
    
    return AnaliseDREIA(
        resumo=resumo,
        pontos_positivos=positivos or ["Dados em processamento"],
        pontos_atencao=atencao or ["Nenhum alerta crítico imediato"],
        recomendacoes=recs,
        nivel_confianca=1.0,
        fonte="DETERMINISTICO"
    )

def _simulacao_deterministica(ctx: ContextoSimulacao) -> AnaliseSimulacaoIA:
    """Fallback determinístico para análise de simulação."""
    var_abs = ctx.resultado_simulado - ctx.resultado_real
    direcao = "melhoria" if var_abs > 0 else "piora"
    
    impacto = f"A simulação projeta uma {direcao} de R$ {abs(var_abs):,.2f} no resultado operacional."
    
    riscos = []
    if ctx.ajuste_receita_pct > 0:
        riscos.append("Dependência de aumento de produtividade ou preço de mercado.")
    if ctx.ajuste_custos_pct < 0:
        riscos.append("Necessidade de corte severo em despesas operacionais.")
        
    recs = [
        "Validar se os preços de venda simulados são realistas para o mercado atual.",
        "Identificar quais categorias de custo permitem a redução simulada."
    ]
    
    return AnaliseSimulacaoIA(
        impacto=impacto,
        riscos=riscos or ["Cenário neutro"],
        recomendacoes=recs,
        nivel_confianca=1.0,
        fonte="DETERMINISTICO"
    )

def _montar_prompt_dre(ctx: ContextoDRE) -> str:
    dados = {
        "receita_bruta": ctx.receita_bruta,
        "custos_operacionais": ctx.custos_operacionais,
        "resultado_operacional": ctx.resultado_operacional,
        "margem_percentual": f"{ctx.margem_percentual:.1f}%",
        "breakdown_custos": ctx.breakdown_custos,
        "breakdown_receitas": ctx.breakdown_receitas
    }

    return f"""Você é um consultor agro-financeiro sênior especializado em gestão de safras.
Analise os resultados da DRE Operacional abaixo e forneça uma interpretação estratégica.

REGRAS:
- Linguagem simples, direta e não técnica para o produtor rural.
- Foco em decisão e eficiência operacional.
- Não invente números. Use apenas o que foi fornecido.
- Destaque alertas reais se a margem estiver baixa ou custos concentrados.

DADOS DA DRE:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Responda EXCLUSIVAMENTE em formato JSON:
{{
  "resumo": "Uma frase resumindo a saúde financeira da safra",
  "pontos_positivos": ["lista de até 3 conquistas financeiras"],
  "pontos_atencao": ["lista de até 3 riscos ou gargalos identificados"],
  "recomendacoes": ["lista de até 3 ações práticas para melhorar o resultado"],
  "nivel_confianca": 0.95
}}"""

async def analisar_dre_safra(
    ctx: ContextoDRE,
    *,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    usuario_id: uuid.UUID | None = None,
) -> AnaliseDREIA:
    """Executa a análise da DRE usando IA com fallback."""
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from sqlalchemy import select
    
    # 1. Verifica tier
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
    
    # 2. Checks de disponibilidade
    if not await tenant_tem_ia(tenant_id, session) or not _ia_globalmente_habilitada():
        res = _analise_deterministica(ctx)
        res.ia_disponivel = False
        return res

    # 3. Verifica limites
    pode_usar, fonte_consumo = await _usage_svc.verificar_limite_ia(tenant_id, tier_value, session)
    if not pode_usar:
        await _usage_svc.registrar_uso_ia(session, tenant_id, "analise_dre", "FALLBACK", usuario_id=usuario_id)
        res = _analise_deterministica(ctx)
        res.ia_disponivel = True
        res.limite_atingido = True
        return res

    # 4. Chama IA
    modelo = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    try:
        resultado = await _chamar_ia_dre(ctx)
        resultado.ia_disponivel = True
        
        if fonte_consumo == "PACOTE":
            await _usage_svc.consumir_credito_pacote(tenant_id, session)
            
        await _usage_svc.registrar_uso_ia(
            session, tenant_id, "analise_dre", "SUCESSO",
            modelo=modelo, usuario_id=usuario_id, fonte_consumo=fonte_consumo
        )
        return resultado
    except Exception as exc:
        logger.error(f"IA falhou na análise da DRE: {exc}")
        await _usage_svc.registrar_uso_ia(session, tenant_id, "analise_dre", "ERRO", modelo=modelo, usuario_id=usuario_id)
        res = _analise_deterministica(ctx)
        res.ia_disponivel = True
        return res

async def _chamar_ia_dre(ctx: ContextoDRE) -> AnaliseDREIA:
    import httpx
    
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    prompt = _montar_prompt_dre(ctx)
    model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()

    content = resp.json()["content"][0]["text"].strip()
    start = content.find("{")
    end = content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    return AnaliseDREIA(
        resumo=parsed.get("resumo", ""),
        pontos_positivos=parsed.get("pontos_positivos", []),
        pontos_atencao=parsed.get("pontos_atencao", []),
        recomendacoes=parsed.get("recomendacoes", []),
        nivel_confianca=float(parsed.get("nivel_confianca", 0.0)),
        fonte="IA"
    )

async def analisar_simulacao_dre(
    ctx: ContextoSimulacao,
    *,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    usuario_id: uuid.UUID | None = None,
) -> AnaliseSimulacaoIA:
    """Analisa a simulação What-if usando IA ou fallback."""
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from sqlalchemy import select
    
    # 1. Verifica tier
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
    
    # 2. Checks de disponibilidade
    if not await tenant_tem_ia(tenant_id, session) or not _ia_globalmente_habilitada():
        res = _simulacao_deterministica(ctx)
        res.ia_disponivel = False
        return res

    # 3. Verifica limites
    pode_usar, fonte_consumo = await _usage_svc.verificar_limite_ia(tenant_id, tier_value, session)
    if not pode_usar:
        await _usage_svc.registrar_uso_ia(session, tenant_id, "simulacao_dre", "FALLBACK", usuario_id=usuario_id)
        res = _simulacao_deterministica(ctx)
        res.ia_disponivel = True
        res.limite_atingido = True
        return res

    # 4. Chama IA
    modelo = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    try:
        resultado = await _chamar_ia_simulacao(ctx)
        resultado.ia_disponivel = True
        
        if fonte_consumo == "PACOTE":
            await _usage_svc.consumir_credito_pacote(tenant_id, session)
            
        await _usage_svc.registrar_uso_ia(
            session, tenant_id, "simulacao_dre", "SUCESSO",
            modelo=modelo, usuario_id=usuario_id, fonte_consumo=fonte_consumo
        )
        return resultado
    except Exception as exc:
        logger.error(f"IA falhou na análise da simulação: {exc}")
        await _usage_svc.registrar_uso_ia(session, tenant_id, "simulacao_dre", "ERRO", modelo=modelo, usuario_id=usuario_id)
        res = _simulacao_deterministica(ctx)
        res.ia_disponivel = True
        return res

def _montar_prompt_simulacao(ctx: ContextoSimulacao) -> str:
    dados = {
        "atual": {
            "receita": ctx.receita_real,
            "custos": ctx.custos_real,
            "resultado": ctx.resultado_real,
            "margem": f"{ctx.margem_real:.1f}%"
        },
        "simulado": {
            "receita": ctx.receita_simulada,
            "custos": ctx.custos_simulados,
            "resultado": ctx.resultado_simulado,
            "margem": f"{ctx.margem_simulada:.1f}%"
        },
        "ajustes": {
            "receita_variacao": f"{ctx.ajuste_receita_pct}%",
            "custos_variacao": f"{ctx.ajuste_custos_pct}%"
        }
    }

    return f"""Você é um consultor agro-financeiro especializado em análise de cenários.
Analise esta SIMULAÇÃO "What-if" de resultado de safra comparando o cenário REAL com o SIMULADO.

DADOS DA SIMULAÇÃO:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Responda EXCLUSIVAMENTE em formato JSON:
{{
  "impacto": "Resumo curto do impacto financeiro",
  "riscos": ["lista de até 3 riscos dessa projeção"],
  "recomendacoes": ["lista de até 3 ações práticas para atingir esse cenário"],
  "nivel_confianca": 0.9
}}"""

async def _chamar_ia_simulacao(ctx: ContextoSimulacao) -> AnaliseSimulacaoIA:
    import httpx
    
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    prompt = _montar_prompt_simulacao(ctx)
    model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()

    content = resp.json()["content"][0]["text"].strip()
    start = content.find("{")
    end = content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    return AnaliseSimulacaoIA(
        impacto=parsed.get("impacto", ""),
        riscos=parsed.get("riscos", []),
        recomendacoes=parsed.get("recomendacoes", []),
        nivel_confianca=float(parsed.get("nivel_confianca", 0.0)),
        fonte="IA"
    )

def _simulacao_deterministica(ctx: ContextoSimulacao) -> AnaliseSimulacaoIA:
    """Fallback determinístico para análise de simulação."""
    impacto = f"Simulação de cenário com variação de {ctx.ajuste_receita_pct}% na receita e {ctx.ajuste_custos_pct}% nos custos."
    
    riscos = []
    if ctx.ajuste_receita_pct < -10:
        riscos.append("Queda significativa na receita bruta")
    if ctx.ajuste_custos_pct > 10:
        riscos.append("Aumento expressivo nos custos operacionais")
    if ctx.margem_simulada < 5:
        riscos.append("Margem de lucro em nível crítico")
    if not riscos:
        riscos = ["Volatilidade de preços de commodities", "Variação climática imprevista"]
        
    recomendacoes = ["Revisar premissas de custos", "Monitorar preços de venda no mercado"]
    if ctx.resultado_simulado < ctx.resultado_real:
        recomendacoes.append("Avaliar estratégias de redução de custos fixos")
    else:
        recomendacoes.append("Focar em eficiência operacional para sustentar ganho")

    return AnaliseSimulacaoIA(
        impacto=impacto,
        riscos=riscos[:3],
        recomendacoes=recomendacoes[:3],
        nivel_confianca=0.5,
        fonte="DETERMINISTICO"
    )
@dataclass
class ContextoCenarios:
    dre_real: ContextoDRE
    cenarios: list[dict] # {id, nome, receita_simulada, custos_simulados, resultado_simulado, margem_simulada}
    historico: list[dict] = field(default_factory=list)

@dataclass
class RecomendacaoCenarioIA:
    cenario_recomendado_id: str | None
    resumo: str
    justificativas: list[str]
    pontos_risco: list[str]
    nivel_confianca: float
    fonte: str           # IA | DETERMINISTICO
    ia_disponivel: bool = False
    limite_atingido: bool = False

async def _calcular_score_ia(tenant_id: uuid.UUID, session: AsyncSession) -> dict:
    """Calcula a taxa de acerto das recomendações da IA baseada no desvio real."""
    from financeiro.models.cenario import FinanceiroSafraCenario
    from financeiro.services.lancamento_service import LancamentoService
    from sqlalchemy import select

    try:
        # Busca cenários recomendados pela IA que possuem dados reais (safra com lançamentos)
        # Para simplificar, consideramos todos que foram recomendados
        stmt = (
            select(FinanceiroSafraCenario)
            .where(
                FinanceiroSafraCenario.tenant_id == tenant_id,
                FinanceiroSafraCenario.recomendado_pela_ia == True
            )
        )
        res = await session.execute(stmt)
        recomendacoes = res.scalars().all()

        total = len(recomendacoes)
        if total == 0:
            return {
                "total_decisoes": 0,
                "acertos": 0,
                "parciais": 0,
                "erros": 0,
                "taxa_acerto": 0.0,
                "taxa_erro": 0.0,
                "status": "SEM_DADOS"
            }

        acertos = 0
        parciais = 0
        erros = 0

        svc_lancamento = LancamentoService(session, tenant_id)

        for r in recomendacoes:
            dre = await svc_lancamento.gerar_dre(r.safra_id)
            resultado_real = dre["resultado_operacional"]
            
            # Desvio absoluto em relação ao projetado
            desvio_abs = abs(resultado_real - r.resultado_simulado)
            desvio_pct = (desvio_abs / abs(r.resultado_simulado) * 100) if r.resultado_simulado != 0 else 0
            
            # Lógica de acerto:
            # <= 10% -> ACERTO
            # 10% a 25% -> PARCIAL
            # > 25% -> ERRO
            if desvio_pct <= 10:
                acertos += 1
            elif desvio_pct <= 25:
                parciais += 1
            else:
                erros += 1

        taxa_acerto = (acertos / total) * 100
        taxa_erro = (erros / total) * 100

        return {
            "total_decisoes": total,
            "acertos": acertos,
            "parciais": parciais,
            "erros": erros,
            "taxa_acerto": round(taxa_acerto, 1),
            "taxa_erro": round(taxa_erro, 1),
            "status": "BOM" if taxa_acerto >= 70 else ("ATENCAO" if taxa_acerto >= 40 else "CRITICO")
        }
    except Exception as e:
        logger.warning(f"Erro ao calcular score de IA: {e}")
        return {
            "total_decisoes": 0,
            "acertos": 0,
            "parciais": 0,
            "erros": 0,
            "taxa_acerto": 0.0,
            "taxa_erro": 0.0,
            "status": "ERRO"
        }

async def _obter_historico_decisoes(tenant_id: uuid.UUID, session: AsyncSession) -> list[dict]:
    """Recupera os últimos 10 cenários escolhidos e seu desempenho real."""
    from financeiro.models.cenario import FinanceiroSafraCenario
    from financeiro.services.lancamento_service import LancamentoService
    from sqlalchemy import select

    try:
        # 1. Busca últimos 10 cenários escolhidos do tenant
        stmt = (
            select(FinanceiroSafraCenario)
            .where(
                FinanceiroSafraCenario.tenant_id == tenant_id,
                FinanceiroSafraCenario.escolhido == True
            )
            .order_by(FinanceiroSafraCenario.escolhido_at.desc())
            .limit(10)
        )
        res = await session.execute(stmt)
        cenarios_db = res.scalars().all()

        if not cenarios_db:
            return []

        historico = []
        svc_lancamento = LancamentoService(session, tenant_id)

        for c in cenarios_db:
            # Calcula DRE real atual da safra do cenário
            dre = await svc_lancamento.gerar_dre(c.safra_id)
            resultado_real = dre["resultado_operacional"]
            
            # Calcula desvio relativo ao planejado no cenário
            # Se planejou X e deu Y, o desvio é Y - X
            desvio = resultado_real - c.resultado_simulado
            desvio_pct = (desvio / abs(c.resultado_simulado) * 100) if c.resultado_simulado != 0 else 0
            
            historico.append({
                "safra_id": str(c.safra_id),
                "cenario_escolhido": c.nome,
                "resultado_planejado": c.resultado_simulado,
                "resultado_real": resultado_real,
                "desvio_percentual": f"{desvio_pct:+.1f}%"
            })
            
        return historico
    except Exception as e:
        logger.warning(f"Erro ao obter histórico de decisões para IA: {e}")
        return []

def _recomendacao_deterministica(ctx: ContextoCenarios) -> RecomendacaoCenarioIA:
    """Fallback determinístico: recomenda o cenário com maior margem simulada."""
    if not ctx.cenarios:
        return RecomendacaoCenarioIA(
            cenario_recomendado_id=None,
            resumo="Nenhum cenário simulado disponível para análise.",
            justificativas=[],
            pontos_risco=[],
            nivel_confianca=1.0,
            fonte="DETERMINISTICO"
        )
    
    # Encontra o cenário com melhor margem
    melhor = max(ctx.cenarios, key=lambda x: x.get("margem_simulada", 0))
    
    return RecomendacaoCenarioIA(
        cenario_recomendado_id=melhor["id"],
        resumo=f"Recomendamos o cenário '{melhor['nome']}' por apresentar a melhor margem operacional simulada.",
        justificativas=[
            f"Margem projetada de {melhor['margem_simulada']:.1f}%",
            f"Resultado operacional superior aos demais cenários (R$ {melhor['resultado_simulado']:,.2f})"
        ],
        pontos_risco=[
            "Análise baseada estritamente em indicadores numéricos",
            "Não considera variações de mercado externo ou riscos logísticos"
        ],
        nivel_confianca=1.0,
        fonte="DETERMINISTICO"
    )

def _montar_prompt_recomendacao(ctx: ContextoCenarios) -> str:
    dados = {
        "atual": {
            "receita": ctx.dre_real.receita_bruta,
            "custos": ctx.dre_real.custos_operacionais,
            "resultado": ctx.dre_real.resultado_operacional,
            "margem": f"{ctx.dre_real.margem_percentual:.1f}%"
        },
        "cenarios": ctx.cenarios,
        "historico_decisoes": ctx.historico
    }

    prompt_historico = ""
    if ctx.historico:
        linhas = []
        for h in ctx.historico:
            linhas.append(f"- Cenário '{h['cenario_escolhido']}' → desvio {h['desvio_percentual']}")
        
        prompt_historico = f"\nHISTÓRICO DE DECISÕES REAIS:\n" + "\n".join(linhas) + "\nEvite repetir estratégias com desempenho negativo e priorize padrões com melhor resultado.\n"

    return f"""Você é um consultor agro-financeiro estratégico.
Sua tarefa é recomendar o MELHOR cenário simulado para uma safra, comparando-os com o resultado atual (Real).

CRITÉRIOS DE ESCOLHA:
1. Equilíbrio entre rentabilidade (margem) e viabilidade (risco).
2. Se um cenário é muito agressivo (ex: corte de 50% de custo), aponte o risco.
3. Justifique por que este cenário é o mais equilibrado para o produtor.
{prompt_historico}
DADOS PARA ANÁLISE:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Responda EXCLUSIVAMENTE em formato JSON:
{{
  "cenario_recomendado_id": "ID do cenário escolhido",
  "resumo": "Uma frase explicando a escolha principal",
  "justificativas": ["lista de até 3 motivos técnicos/estratégicos"],
  "pontos_risco": ["lista de até 2 riscos específicos deste cenário"],
  "nivel_confianca": 0.9
}}"""

async def recomendar_cenario_safra(
    ctx: ContextoCenarios,
    *,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    usuario_id: uuid.UUID | None = None,
) -> RecomendacaoCenarioIA:
    """Recomenda o melhor cenário usando IA ou fallback."""
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from sqlalchemy import select
    
    # 1. Verifica cenários vazios
    if not ctx.cenarios:
        return _recomendacao_deterministica(ctx)

    # 2. Verifica tier
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
    
    # 3. Checks de disponibilidade
    if not await tenant_tem_ia(tenant_id, session) or not _ia_globalmente_habilitada():
        res = _recomendacao_deterministica(ctx)
        res.ia_disponivel = False
        return res

    # 4. Verifica limites
    pode_usar, fonte_consumo = await _usage_svc.verificar_limite_ia(tenant_id, tier_value, session)
    if not pode_usar:
        await _usage_svc.registrar_uso_ia(session, tenant_id, "recomendacao_cenario", "FALLBACK", usuario_id=usuario_id)
        res = _recomendacao_deterministica(ctx)
        res.ia_disponivel = True
        res.limite_atingido = True
        return res

    # 5. Busca histórico para aprendizado
    ctx.historico = await _obter_historico_decisoes(tenant_id, session)

    # 6. Chama IA
    modelo = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
    try:
        resultado = await _chamar_ia_recomendacao(ctx)
        resultado.ia_disponivel = True
        
        if fonte_consumo == "PACOTE":
            await _usage_svc.consumir_credito_pacote(tenant_id, session)
            
        await _usage_svc.registrar_uso_ia(
            session, tenant_id, "recomendacao_cenario", "SUCESSO",
            modelo=modelo, usuario_id=usuario_id, fonte_consumo=fonte_consumo
        )
        return resultado
    except Exception as exc:
        logger.error(f"IA falhou na recomendação de cenário: {exc}")
        await _usage_svc.registrar_uso_ia(session, tenant_id, "recomendacao_cenario", "ERRO", modelo=modelo, usuario_id=usuario_id)
        res = _recomendacao_deterministica(ctx)
        res.ia_disponivel = True
        return res

async def _chamar_ia_recomendacao(ctx: ContextoCenarios) -> RecomendacaoCenarioIA:
    import httpx
    
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    prompt = _montar_prompt_recomendacao(ctx)
    model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()

    content = resp.json()["content"][0]["text"].strip()
    start = content.find("{")
    end = content.rfind("}") + 1
    parsed = json.loads(content[start:end])

    return RecomendacaoCenarioIA(
        cenario_recomendado_id=parsed.get("cenario_recomendado_id"),
        resumo=parsed.get("resumo", ""),
        justificativas=parsed.get("justificativas", []),
        pontos_risco=parsed.get("pontos_risco", []),
        nivel_confianca=float(parsed.get("nivel_confianca", 0.0)),
        fonte="IA"
    )
