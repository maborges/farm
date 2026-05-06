import uuid
import os
import json
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from loguru import logger
from financeiro.services.alerta_inteligente_service import AlertaInteligenteService
from financeiro.services.lancamento_service import LancamentoService
from financeiro.schemas.lancamento_schema import ResumoDiarioResponse, SaudeFinanceiraResumo, AlertaInteligente
from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.estresse_financeiro_service import IAEstresseFinanceiroService
from ia.plano_acao_service import IAPlanoAcaoService

class ResumoDiarioService:
    def __init__(self, session, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def obter_resumo(self, safra_id: uuid.UUID) -> ResumoDiarioResponse:
        """
        Gera o resumo consolidado diário (Step 198).
        Consolida alertas prioritários, saúde financeira e insights de IA.
        """
        # 1. Busca Alertas Prioritários (Top 3)
        svc_alertas = AlertaInteligenteService(self.session, self.tenant_id)
        alertas = await svc_alertas.verificar_alertas(safra_id)
        top_alertas = alertas[:3]
        
        # 2. Busca Saúde Financeira (DRE)
        svc_lancamento = LancamentoService(self.session, self.tenant_id)
        dre = await svc_lancamento.gerar_dre(safra_id)
        
        saude = SaudeFinanceiraResumo(
            receita=dre.receita_bruta,
            custos=dre.custos_operacionais,
            margem=dre.margem_percentual
        )
        
        # 3. Identifica Risco e Oportunidade Principal
        # Risco: Geralmente o alerta de maior prioridade
        risco_principal = "Estabilidade financeira mantida."
        oportunidade_principal = "Monitoramento constante de mercado."
        
        if top_alertas:
            risco_principal = top_alertas[0]["impacto"]
            oportunidade_principal = top_alertas[0]["recomendacao"]
            
        # 3.1. Busca Predição IA (Step 205)
        svc_predicao = IAPredicaoRiscoService(self.session, self.tenant_id)
        predicao = await svc_predicao.prever_risco_financeiro(safra_id)
        
        # 3.2. Busca Simulação de Estresse (Step 206)
        svc_estresse = IAEstresseFinanceiroService(self.session, self.tenant_id)
        estresse = await svc_estresse.simular_estresse_financeiro(safra_id)
        
        # 3.3. Busca Plano de Ação (Step 207)
        svc_plano = IAPlanoAcaoService(self.session, self.tenant_id)
        plano = await svc_plano.gerar_plano_recuperacao(safra_id)
            
        # 4. Gera Resumo via IA
        ia_resumo = await self._gerar_resumo_ia(saude, top_alertas, predicao, estresse, plano)
        
        return ResumoDiarioResponse(
            texto_resumo=ia_resumo.get("texto_resumo", "Resumo diário indisponível no momento."),
            top_alertas=[AlertaInteligente(**a) for a in top_alertas],
            saude_financeira=saude,
            risco_principal=risco_principal,
            oportunidade_principal=oportunidade_principal,
            recomendacao_ia=ia_resumo.get("recomendacao", "Continue monitorando os indicadores."),
            ia_disponivel=ia_resumo.get("ia_sucesso", False)
        )

    async def _gerar_resumo_ia(self, saude: SaudeFinanceiraResumo, alertas: List[Dict], predicao: Dict[str, Any], estresse: Dict[str, Any], plano: Dict[str, Any]) -> Dict[str, Any]:
        """Usa IA para gerar o texto do briefing diário (Step 198) com dados preditivos (Step 205), estresse (Step 206) e plano de ação (Step 207)."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {
                "texto_resumo": f"Sua margem atual é de {saude.margem:.1f}%. Possui {len(alertas)} alertas ativos.",
                "recomendacao": "Consulte o dashboard para detalhes.",
                "ia_sucesso": False
            }

        prompt = f"""Você é um analista financeiro agrícola senior.
Gere um RESUMO DIÁRIO (Daily Briefing) CONSOLIDADO para o produtor rural.

DADOS FINANCEIROS:
- Receita: R$ {saude.receita:,.2f}
- Custos: R$ {saude.custos:,.2f}
- Margem: {saude.margem:.1f}%

ALERTAS PRIORITÁRIOS:
{json.dumps(alertas, ensure_ascii=False, indent=2)}

TENDÊNCIA PREDITIVA (PRÓXIMOS 15 DIAS):
- Impacto Estimado: R$ {predicao['impacto_estimado']:,.2f}
 
 CENÁRIO DE ESTRESSE (PIOR CASO - Step 206):
 - Risco: {estresse['nivel_risco']}
 - Descrição: {estresse['descricao']}
 - Resultado Pior Caso: R$ {estresse['pior_cenario']['resultado'] if estresse['pior_cenario'] else 0:,.2f}
 
 PLANO DE AÇÃO RECOMENDADO (Step 207):
 - Resumo: {plano['resumo']}
 - Ações: {json.dumps(plano['acoes'][:2], ensure_ascii=False)}

REGRAS:
1. Linguagem simples e direta.
2. Até 3-5 frases curtas.
3. Foco em AÇÃO e INSIGHT.
4. Evite jargões técnicos excessivos.

Responda em JSON:
{{
  "texto_resumo": "Consolidado do dia em poucas frases",
  "recomendacao": "Principal ação recomendada",
  "acao_sugerida": {{
    "acao": "SIMULACAO", 
    "parametros": {{"receita_percentual": 5, "custos_percentual": -10}},
    "descricao": "Executar ajuste sugerido para recuperação de margem"
  }}
}}"""

        model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
        try:
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
                        "max_tokens": 800,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                
            content = resp.json()["content"][0]["text"].strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            data = json.loads(content[start:end])
            data["ia_sucesso"] = True
            return data
            
        except Exception as exc:
            logger.error(f"IA falhou ao gerar resumo diário: {exc}")
            return {
                "texto_resumo": f"Sua margem atual é de {saude.margem:.1f}%. Possui {len(alertas)} alertas ativos.",
                "recomendacao": "Consulte o dashboard para detalhes.",
                "ia_sucesso": False
            }
