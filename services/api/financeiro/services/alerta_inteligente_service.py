import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from financeiro.services.lancamento_service import LancamentoService
from financeiro.services.cenario_service import CenarioFinanceiroService
from financeiro.models.cenario import FinanceiroSafraCenario
from ia.models import IAAlertaHistorico
from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.estresse_financeiro_service import IAEstresseFinanceiroService
from ia.plano_acao_service import IAPlanoAcaoService
from ia.estresse_financeiro_service import IAEstresseFinanceiroService

class AlertaInteligenteService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _analisar_comportamento_usuario(self) -> Dict[str, Any]:
        """
        Analisa o histórico de interações para identificar padrões de comportamento (Step 195).
        Retorna estatísticas de execução e ignorados por tipo de alerta.
        """
        from sqlalchemy import func
        
        # Busca últimos 50 alertas para análise de tendência
        stmt = select(IAAlertaHistorico).where(
            IAAlertaHistorico.tenant_id == self.tenant_id
        ).order_by(IAAlertaHistorico.created_at.desc()).limit(50)
        
        res = await self.session.execute(stmt)
        historico = res.scalars().all()
        
        if not historico:
            return {
                "taxa_execucao": 0.0,
                "taxa_ignorado": 0.0,
                "tipos_mais_executados": [],
                "tipos_mais_ignorados": [],
                "perfil": "EQUILIBRADO"
            }
            
        total = len(historico)
        executados = sum(1 for h in historico if h.acao_executada)
        ignorados = sum(1 for h in historico if h.ignorado)
        
        # Agrupamento por tipo
        stats_tipo = {}
        for h in historico:
            t = h.tipo_alerta
            if t not in stats_tipo:
                stats_tipo[t] = {"exec": 0, "ign": 0}
            if h.acao_executada: stats_tipo[t]["exec"] += 1
            if h.ignorado: stats_tipo[t]["ign"] += 1
            
        # Ordena tipos por performance
        tipos_mais_executados = sorted(stats_tipo.keys(), key=lambda k: stats_tipo[k]["exec"], reverse=True)[:2]
        tipos_mais_ignorados = sorted(stats_tipo.keys(), key=lambda k: stats_tipo[k]["ign"], reverse=True)[:2]
        
        taxa_exec = (executados / total) * 100
        taxa_ign = (ignorados / total) * 100
        
        # Classificação de Perfil (Step 195)
        if taxa_exec > 40:
            perfil = "AGRESSIVO" # Executa muito, aceita sugestões de risco
        elif taxa_ign > 50:
            perfil = "CONSERVADOR" # Ignora muito, prefere segurança extrema
        else:
            perfil = "EQUILIBRADO"
            
        return {
            "taxa_execucao": round(taxa_exec, 1),
            "taxa_ignorado": round(taxa_ign, 1),
            "tipos_mais_executados": tipos_mais_executados,
            "tipos_mais_ignorados": tipos_mais_ignorados,
            "perfil": perfil
        }

    async def verificar_alertas(self, safra_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Analisa a safra em busca de riscos e oportunidades, gerando alertas proativos (Step 195)."""
        alertas_dict = []
        
        # 0. Analisa Comportamento do Usuário (Step 195)
        comportamento = await self._analisar_comportamento_usuario()
        
        # 1. Busca Dados Reais (DRE)
        svc_lancamento = LancamentoService(self.session, self.tenant_id)
        dre = await svc_lancamento.gerar_dre(safra_id)
        
        # 2. Regra: Margem < 10% (Baixa Rentabilidade)
        if dre.margem_percentual < 10:
            alertas_dict.append({
                "tipo": "RENTABILIDADE",
                "gravidade": "alta" if dre.margem_percentual < 0 else "media",
                "titulo": "Baixa Rentabilidade Detectada",
                "mensagem": f"A margem atual de {dre.margem_percentual:.1f}% está abaixo do limite de segurança (10%).",
                "impacto": "Risco de prejuízo operacional caso os custos continuem subindo.",
                "recomendacao": "Revisar imediatamente custos de insumos e considerar antecipação de vendas para melhorar a liquidez.",
                "acao": "simular",
                "parametros": {
                    "receita_percentual": 5,
                    "custos_percentual": -5
                },
                "acao_sugerida": {
                    "acao": "SIMULACAO",
                    "parametros": {
                        "receita_percentual": 5,
                        "custos_percentual": -5
                    },
                    "descricao": "Simular ajuste de 5% na receita e -5% nos custos para recuperar margem."
                }
            })

        # 3. Regra: Desvio > 20% (Planejamento Falho)
        svc_cenario = CenarioFinanceiroService(self.session, self.tenant_id)
        analise = await svc_cenario.analisar_desvio(safra_id)
        
        if analise.get("cenario_escolhido") and abs(analise.get("desvio_percentual", 0)) > 20:
            alertas_dict.append({
                "tipo": "PLANEJAMENTO",
                "gravidade": "alta",
                "titulo": "Desvio Crítico no Planejamento",
                "mensagem": f"O resultado real está desviando {analise['desvio_percentual']:.1f}% do cenário '{analise['cenario_escolhido']}'.",
                "impacto": "As projeções financeiras não estão se concretizando, o que pode comprometer o fluxo de caixa futuro.",
                "recomendacao": "Ajustar o cenário escolhido com os novos dados reais e recalcular a necessidade de capital de giro.",
                "acao": "comparar",
                "parametros": {
                    "cenario_id": str(analise.get("cenario_id", "")),
                    "desvio": analise.get("desvio_percentual")
                },
                "acao_sugerida": {
                    "acao": "AJUSTE_CENARIO",
                    "parametros": {
                        "cenario_id": str(analise.get("cenario_id", "")),
                        "novo_custo_base": "real"
                    },
                    "descricao": "Ajustar projeções do cenário para alinhar com os custos reais detectados."
                }
            })

        # 4. Regra: Custo crescendo > Receita (Step 192)
        if dre.receita_bruta > 0:
            proporcao_custo = (dre.custos_operacionais / dre.receita_bruta) * 100
            if proporcao_custo > 90:
                alertas_dict.append({
                    "tipo": "EFICIENCIA",
                    "gravidade": "alta",
                    "titulo": "Eficiência Operacional em Risco",
                    "mensagem": f"Os custos operacionais consomem {proporcao_custo:.1f}% da receita bruta.",
                    "impacto": "Sufocamento da margem líquida e dependência excessiva de crédito.",
                    "recomendacao": "Identificar categorias de custo com maior variação e renegociar contratos de serviços/logística.",
                    "acao": "simular",
                    "parametros": {
                        "custos_percentual": -10
                    },
                    "acao_sugerida": {
                        "acao": "SIMULACAO",
                        "parametros": {
                            "custos_percentual": -10
                        },
                        "descricao": "Simular redução de 10% nos custos operacionais para aliviar o caixa."
                    }
                })

        # Simulação de Estresse (Step 206)
        svc_estresse = IAEstresseFinanceiroService(self.session, self.tenant_id)
        estresse = await svc_estresse.simular_estresse_financeiro(safra_id)
        
        if estresse["nivel_risco"] in ["CRITICO", "ALTO"]:
            # Gera Plano de Ação (Step 207)
            svc_plano = IAPlanoAcaoService(self.session, self.tenant_id)
            plano = await svc_plano.gerar_plano_recuperacao(safra_id)
            
            alertas_dict.append({
                "tipo": "ESTRESSE",
                "gravidade": "CRÍTICA" if estresse["nivel_risco"] == "CRITICO" else "ALTA",
                "titulo": f"Risco de Insolvência: {estresse['nivel_risco']}",
                "mensagem": estresse["descricao"],
                "impacto": f"Impacto projetado de R$ {estresse['pior_cenario']['resultado'] if estresse['pior_cenario'] else 0:,.2f} no pior cenário.",
                "recomendacao": f"Siga o Plano de Ação: {plano['resumo']}",
                "acao": "aplicar_plano",
                "parametros": {
                    "plano_id": plano.get("id")
                },
                "acao_sugerida": {
                    "acao": "APLICAR_PLANO",
                    "parametros": {
                        "plano_id": plano.get("id")
                    },
                    "descricao": "Executar as etapas do plano de recuperação de safra."
                }
            })

        # 5. Predição IA (Step 205)
        svc_predicao = IAPredicaoRiscoService(self.session, self.tenant_id)
        predicao = await svc_predicao.prever_risco_financeiro(safra_id)
        
        if predicao["risco"] != "BAIXO":
            alertas_dict.append({
                "tipo": "PREDITIVO",
                "gravidade": predicao["risco"].lower(),
                "titulo": f"Previsão de Risco: {predicao['risco']}",
                "mensagem": predicao["descricao"],
                "impacto": f"Impacto estimado em {predicao['tempo_estimado']}: R$ {predicao['impacto_estimado']:,.2f}",
                "recomendacao": predicao["acao_recomendada"],
                "acao": "simular",
                "parametros": {
                    "custos_percentual": -10
                },
                "acao_sugerida": {
                    "acao": "SIMULACAO",
                    "parametros": {
                        "custos_percentual": -10
                    },
                    "descricao": f"Executar simulação preventiva recomendada para mitigar risco previsto."
                }
            })

        # 7. Refinamento por IA Adaptativa (Step 195)
        # A IA ajusta a linguagem e prioridade com base no perfil do usuário
        alertas_dict = await self.gerar_alerta_ia(safra_id, alertas_dict, comportamento)

        # 8. Cálculo de Prioridade Determinística (Step 197)
        for a in alertas_dict:
            if "prioridade" not in a:
                a["prioridade"] = self._calcular_prioridade_alerta(a, comportamento)
            if "motivo_prioridade" not in a:
                a["motivo_prioridade"] = self._gerar_motivo_prioridade(a)

        # 9. Persistência no histórico (Step 194)
        limite_recentes = datetime.now(timezone.utc) - timedelta(hours=24)
        
        alertas_finais = []
        for a in alertas_dict:
            # Busca duplicidade
            stmt = select(IAAlertaHistorico).where(
                IAAlertaHistorico.tenant_id == self.tenant_id,
                IAAlertaHistorico.safra_id == safra_id,
                IAAlertaHistorico.tipo_alerta == a["tipo"],
                IAAlertaHistorico.created_at >= limite_recentes
            )
            existente = (await self.session.execute(stmt)).scalar_one_or_none()
            
            if not existente:
                novo_alerta = IAAlertaHistorico(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    safra_id=safra_id,
                    tipo_alerta=a["tipo"],
                    titulo=a["titulo"],
                    mensagem=a["mensagem"],
                    gravidade=a["gravidade"],
                    parametros_json={
                        "impacto": a["impacto"],
                        "recomendacao": a["recomendacao"],
                        "acao": a.get("acao"),
                        "parametros": a.get("parametros"),
                        "prioridade": a.get("prioridade", 0),
                        "motivo_prioridade": a.get("motivo_prioridade"),
                        "acao_sugerida": a.get("acao_sugerida")
                    }
                )
                self.session.add(novo_alerta)
                await self.session.flush()
                
                # Retorna o ID real do banco
                a["id"] = str(novo_alerta.id)
                alertas_finais.append(a)
            else:
                # Se o alerta já existe e foi ignorado, não mostramos novamente (Step 194)
                if existente.ignorado:
                    continue
                    
                a["id"] = str(existente.id)
                # Mantém prioridade do histórico ou recalcula
                if "prioridade" not in a:
                    a["prioridade"] = existente.parametros_json.get("prioridade", self._calcular_prioridade_alerta(a, comportamento))
                if "motivo_prioridade" not in a:
                    a["motivo_prioridade"] = existente.parametros_json.get("motivo_prioridade", self._gerar_motivo_prioridade(a))
                alertas_finais.append(a)
        
        # 10. Ordenação por Prioridade (Step 197)
        alertas_finais.sort(key=lambda x: x.get("prioridade", 0), reverse=True)
        
        await self.session.commit()
        return alertas_finais

    def _calcular_prioridade_alerta(self, alerta: Dict[str, Any], comportamento: Dict[str, Any]) -> float:
        """Calcula score de prioridade de 0 a 100 (Step 197)."""
        score = 0.0
        gravidade = alerta.get("gravidade", "baixa").lower()
        
        # 1. Gravidade (Base 50%)
        pesos_gravidade = {"alta": 50, "media": 30, "baixa": 10}
        score += pesos_gravidade.get(gravidade, 10)
        
        # 2. Impacto Financeiro (Bônus 20%)
        if alerta.get("tipo") in ["RENTABILIDADE", "PLANEJAMENTO"]:
            score += 20
        elif alerta.get("tipo") == "EFICIENCIA":
            score += 15
        elif alerta.get("tipo") == "PREDITIVO":
            score += 25  # Alta prioridade por ser antecipação
        elif alerta.get("tipo") == "ESTRESSE":
            score += 35  # Prioridade máxima para cenários de crise
            
        # 3. Comportamento e Histórico (Bônus/Ônus 30%)
        if alerta.get("tipo") in comportamento.get("tipos_mais_executados", []):
            score += 20
        if alerta.get("tipo") in comportamento.get("tipos_mais_ignorados", []):
            if gravidade != "alta":
                score -= 15
        
        # 4. Ajuste por Taxa de Execução Global
        score += (comportamento.get("taxa_execucao", 0) / 10) # Bônus pequeno para usuários engajados
        
        return min(100.0, max(0.0, score))

    def _gerar_motivo_prioridade(self, alerta: Dict[str, Any]) -> str:
        """Gera justificativa determinística para a prioridade (Step 197)."""
        gravidade = alerta.get("gravidade", "baixa").lower()
        if gravidade == "alta":
            return "Prioridade máxima devido ao risco imediato à margem da safra."
        if alerta.get("tipo") == "PLANEJAMENTO":
            return "Alta prioridade para alinhar o resultado real com as projeções simuladas."
        if alerta.get("tipo") == "RENTABILIDADE":
            return "Foco em recuperar a lucratividade operacional."
        if alerta.get("tipo") == "ESTRESSE":
            return "Prioridade CRÍTICA: Simulação de pior cenário detectou risco de insolvência."
        return "Alerta importante para monitoramento da saúde financeira."

    async def gerar_alerta_ia(self, safra_id: uuid.UUID, contexto_alertas: List[Dict], comportamento: Dict[str, Any]):
        """Usa IA para refinar os alertas e gerar recomendações mais contextuais adaptadas ao perfil (Step 195)."""
        if not contexto_alertas:
            return []

        import os
        import json
        import httpx
        from loguru import logger

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("IA desabilitada para refinamento: ANTHROPIC_API_KEY não configurada.")
            return contexto_alertas

        prompt = f"""Você é um copiloto agro-financeiro inteligente.
Sua tarefa é filtrar, refinar e PRIORIZAR alertas financeiros gerados para uma safra, adaptando-os ao PERFIL DO USUÁRIO.

PERFIL DO USUÁRIO:
- Tipo: {comportamento['perfil']}
- Taxa de Execução de Recomendações: {comportamento['taxa_execucao']}%
- Tipos de Alerta mais EXECUTADOS: {', '.join(comportamento['tipos_mais_executados']) or 'Nenhum ainda'}
- Tipos de Alerta mais IGNORADOS: {', '.join(comportamento['tipos_mais_ignorados']) or 'Nenhum ainda'}

REGRAS DE ADAPTAÇÃO E PRIORIZAÇÃO (Step 197):
1. Calcule uma "prioridade" de 0 a 100 para cada alerta.
2. Gere um "motivo_prioridade" curto explicando por que esse alerta é importante agora.
3. Se o perfil for CONSERVADOR: Suavize recomendações agressivas, foque em segurança.
4. Se o perfil for AGRESSIVO: Priorize oportunidades de alto impacto.
5. NUNCA oculte alertas críticos (gravidade alta).
6. Alertas que o usuário costuma EXECUTAR devem ganhar bônus de prioridade.

ALERTAS ATUAIS (DETERMINÍSTICOS):
{json.dumps(contexto_alertas, ensure_ascii=False, indent=2)}

Responda EXCLUSIVAMENTE em formato JSON (lista de objetos):
[
  {{
    "tipo": "...",
    "gravidade": "...",
    "titulo": "...",
    "mensagem": "...",
    "impacto": "...",
    "recomendacao": "...",
    "acao": "...",
    "parametros": {{}},
    "prioridade": 85.5,
    "motivo_prioridade": "...",
    "acao_sugerida": {{
      "acao": "SIMULACAO", 
      "parametros": {{"receita_percentual": 5, "custos_percentual": -10}},
      "descricao": "Executar simulação de ajuste para validar recuperação de margem."
    }}
  }}
]"""

        model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")
        try:
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
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()

            content = resp.json()["content"][0]["text"].strip()
            start = content.find("[")
            end = content.rfind("]") + 1
            alertas_refinados = json.loads(content[start:end])
            
            return alertas_refinados
        except Exception as exc:
            logger.error(f"IA falhou ao refinar alertas (Step 197): {exc}")
            return contexto_alertas
