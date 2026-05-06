import uuid
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from financeiro.services.lancamento_service import LancamentoService
from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.estresse_financeiro_service import IAEstresseFinanceiroService

class IAPlanoAcaoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def gerar_plano_recuperacao(self, safra_id: uuid.UUID) -> Dict[str, Any]:
        """
        Gera automaticamente um plano de ação para recuperação financeira (Step 207).
        Consolida dados de DRE, Predição e Estresse.
        """
        logger.info(f"Gerando plano de ação para safra {safra_id}")

        # 1. Coleta de dados
        svc_lancamento = LancamentoService(self.session, self.tenant_id)
        dre = await svc_lancamento.gerar_dre(safra_id)

        svc_predicao = IAPredicaoRiscoService(self.session, self.tenant_id)
        predicao = await svc_predicao.prever_risco_financeiro(safra_id)

        svc_estresse = IAEstresseFinanceiroService(self.session, self.tenant_id)
        estresse = await svc_estresse.simular_estresse_financeiro(safra_id)

        # 2. Lógica Determinística Inicial
        nivel_risco = estresse["nivel_risco"]
        resumo = estresse["descricao"]
        acoes = []

        # Ação 1: Redução de Custos (Sempre sugerida se risco >= MEDIO)
        if nivel_risco in ["CRITICO", "ALTO", "MEDIO"]:
            percentual_reducao = 0.10 if nivel_risco == "CRITICO" else 0.05
            impacto_valor = dre.custos_operacionais * percentual_reducao
            acoes.append({
                "id": str(uuid.uuid4()),
                "tipo": "REDUCAO_CUSTO",
                "descricao": f"Reduzir custos operacionais em {int(percentual_reducao*100)}% focando em insumos e logística.",
                "impacto_estimado": f"+R$ {impacto_valor:,.2f}",
                "impacto_valor": impacto_valor,
                "prioridade": 1,
                "acao_sugerida": "AJUSTE_CENARIO",
                "parametros_json": {
                    "custos_percentual": -int(percentual_reducao * 100)
                }
            })

        # Ação 2: Aumento de Receita / Renegociação (Se margem baixa)
        if dre.margem_percentual < 15 or nivel_risco == "CRITICO":
            percentual_aumento = 0.05
            impacto_valor = dre.receita_bruta * percentual_aumento
            acoes.append({
                "id": str(uuid.uuid4()),
                "tipo": "AUMENTO_RECEITA",
                "descricao": "Antecipar contratos de venda ou buscar novos canais para elevar preço médio em 5%.",
                "impacto_estimado": f"+R$ {impacto_valor:,.2f}",
                "impacto_valor": impacto_valor,
                "prioridade": 2,
                "acao_sugerida": "AJUSTE_CENARIO",
                "parametros_json": {
                    "receita_percentual": int(percentual_aumento * 100)
                }
            })

        # Ação 3: Proteção Financeira (Se estresse alto)
        if nivel_risco in ["CRITICO", "ALTO"]:
            acoes.append({
                "id": str(uuid.uuid4()),
                "tipo": "PROTECAO_HEDGE",
                "descricao": "Realizar operações de hedge ou seguro agrícola para mitigar variações de preço/clima.",
                "impacto_estimado": "Mitigação de Risco",
                "impacto_valor": 0.0,
                "prioridade": 3,
                "acao_sugerida": "ANALISE_DETALHADA",
                "parametros_json": {
                    "modulo": "mercado",
                    "sugestao": "hedge_clima"
                }
            })

        # 3. Refinamento via IA (Opcional)
        plano_refinado = await self._refinar_plano_ia(dre, predicao, estresse, acoes)
        
        if plano_refinado:
            return plano_refinado

        # 4. Autopilot (Step 210)
        from ia.autopilot_service import IAAutopilotService
        plano = {
            "nivel_risco": nivel_risco,
            "resumo": resumo,
            "acoes": acoes,
            "data_geracao": datetime.now(timezone.utc)
        }
        
        acoes_auto = await IAAutopilotService.avaliar_e_executar(self.session, self.tenant_id, plano)
        plano["acoes_executadas_automaticamente"] = acoes_auto
        
        return plano

    async def _refinar_plano_ia(self, dre, predicao, estresse, acoes_base) -> Optional[Dict[str, Any]]:
        """Usa IA para refinar o plano de ação, tornando-o mais específico e humano."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        prompt = f"""Você é um consultor financeiro agrícola focado em recuperação de safras.
Gere um PLANO DE AÇÃO prático para o produtor rural.

DADOS ATUAIS:
- Margem Atual: {dre.margem_percentual:.1f}%
- Resultado Atual: R$ {dre.resultado_liquido:,.2f}

RISCO PREDITIVO:
- {predicao['descricao']}

CENÁRIO DE ESTRESSE:
- Nível: {estresse['nivel_risco']}
- Impacto: {estresse['descricao']}

AÇÕES SUGERIDAS PELO MOTOR:
{json.dumps(acoes_base, ensure_ascii=False, indent=2)}

REGRAS:
1. Refine as descrições para serem mais 'acionáveis'.
2. Adicione um tom de urgência se o risco for CRÍTICO.
3. Mantenha o foco em impacto financeiro (R$).
4. Retorne EXATAMENTE 2 a 4 ações priorizadas.

Responda em JSON:
{{
  "nivel_risco": "{estresse['nivel_risco']}",
  "resumo": "Breve análise da situação",
  "acoes": [
    {{
      "id": "uuid-string",
      "tipo": "TIPO_ACAO",
      "descricao": "O que fazer exatamente",
      "impacto_estimado": "+R$ ...",
      "impacto_valor": 0.0,
      "prioridade": 1,
      "acao_sugerida": "AJUSTE_CENARIO",
      "parametros_json": {{"percentual": 10}}
    }}
  ]
}}
"""
        try:
            # Simulação de chamada para Claude (mesmo padrão dos outros serviços)
            # Para o Step 207, garantiremos que o JSON retornado seja válido.
            # Aqui usaremos a estrutura base se a IA falhar.
            return None # Fallback por enquanto, integraremos a chamada real se necessário
        except Exception as e:
            logger.error(f"Erro ao refinar plano via IA: {e}")
            return None
