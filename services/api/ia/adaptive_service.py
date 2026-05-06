import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ia.autopilot_metrics_service import IAAutopilotMetricsService
from ia.autopilot_service import IAAutopilotService

class IAAutopilotAdaptiveService:
    @staticmethod
    async def avaliar_ajuste_autonomia(session: AsyncSession, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Analisa o desempenho do Autopilot e sugere ajustes dinâmicos nos limites (Step 212).
        Utiliza taxas de aceitação e reversão para calibrar a autonomia.
        """
        metrics = await IAAutopilotMetricsService.obter_metricas(session, tenant_id)
        config = await IAAutopilotService.get_config(session, tenant_id)
        
        total_acoes = metrics["total_acoes_automaticas"]
        taxa_aceitacao = metrics["taxa_aprovacao_implicita"]
        taxa_reversao = metrics["taxa_reversao"]
        limite_atual = config.limite_impacto_percentual
        
        # Volume mínimo para sugerir tuning (evitar decisões baseadas em ruído)
        if total_acoes < 5:
            return {
                "deve_ajustar": False,
                "acao": "MANTER",
                "limite_atual": limite_atual,
                "novo_limite": limite_atual,
                "mensagem": "Coletando dados suficientes para otimizar sua autonomia.",
                "motivo": "VOLUME_INSUFICIENTE"
            }
            
        # Regras de Ajuste (Step 212.3)
        # 1. Se aceitação for muito alta (>90%), sugere aumentar o limite para ser mais produtivo
        if taxa_aceitacao >= 90:
            novo_limite = min(limite_atual + 2.0, 20.0) # Teto de 20% para segurança inicial
            if novo_limite > limite_atual:
                return {
                    "deve_ajustar": True,
                    "acao": "AUMENTAR_AUTONOMIA",
                    "limite_atual": limite_atual,
                    "novo_limite": novo_limite,
                    "mensagem": f"O copiloto tem {taxa_aceitacao}% de aceitação. Podemos ampliar o limite de autonomia para {novo_limite}% para acelerar suas análises.",
                    "motivo": "ALTA_ACEITACAO"
                }
                
        # 2. Se a reversão for preocupante (>25%), sugere recuar para evitar retrabalho
        if taxa_reversao >= 25:
            novo_limite = max(limite_atual - 2.0, 2.0) # Piso de 2%
            if novo_limite < limite_atual:
                return {
                    "deve_ajustar": True,
                    "acao": "REDUZIR_AUTONOMIA",
                    "limite_atual": limite_atual,
                    "novo_limite": novo_limite,
                    "mensagem": f"Detectamos {taxa_reversao}% de reversões em ações automáticas. Sugerimos reduzir o limite para {novo_limite}% para alinhar melhor com suas preferências.",
                    "motivo": "ALTA_REVERSAO"
                }
                
        return {
            "deve_ajustar": False,
            "acao": "MANTER",
            "limite_atual": limite_atual,
            "novo_limite": limite_atual,
            "mensagem": "Seu nível de autonomia está perfeitamente calibrado para seu ritmo de trabalho.",
            "motivo": "EQUILIBRADO"
        }
