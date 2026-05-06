import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from ia.models import IAAcaoAssistidaHistorico

class IAAutopilotMetricsService:
    @staticmethod
    async def obter_metricas(session: AsyncSession, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calcula métricas de performance do Autopilot (Step 211).
        Cruza dados de ações AUTOMATICA para medir impacto e aceitação.
        """
        # Filtro base para ações do Autopilot
        stmt = select(
            func.count(IAAcaoAssistidaHistorico.id).label("total"),
            func.sum(IAAcaoAssistidaHistorico.impacto_valor).label("impacto_total"),
            func.count(case((IAAcaoAssistidaHistorico.revertida == True, 1))).label("revertidas"),
            func.count(case((IAAcaoAssistidaHistorico.concluida == True, 1))).label("concluidas"),
            func.avg(
                case(
                    ((IAAcaoAssistidaHistorico.concluida == True) | (IAAcaoAssistidaHistorico.revertida == True),
                     func.extract('epoch', 
                        func.coalesce(IAAcaoAssistidaHistorico.concluida_em, IAAcaoAssistidaHistorico.revertida_em) - 
                        IAAcaoAssistidaHistorico.created_at
                     ))
                )
            ).label("tempo_medio_interacao")
        ).where(
            IAAcaoAssistidaHistorico.tenant_id == tenant_id,
            IAAcaoAssistidaHistorico.metodo_execucao == "AUTOMATICA"
        )
        
        result = await session.execute(stmt)
        row = result.one()
        
        total = row.total or 0
        impacto_total = float(row.impacto_total or 0)
        revertidas = row.revertidas or 0
        concluidas = row.concluidas or 0
        
        # Taxas
        taxa_reversao = (revertidas / total * 100) if total > 0 else 0
        # Aprovação implícita: não revertidas
        taxa_aprovacao = ((total - revertidas) / total * 100) if total > 0 else 0
        
        impacto_medio = (impacto_total / total) if total > 0 else 0
        tempo_medio_minutos = (row.tempo_medio_interacao / 60) if row.tempo_medio_interacao else 0
        
        # Gerar Insight Automático (Step 211.7)
        insight = "O Autopilot ainda está coletando dados iniciais para gerar recomendações."
        if total > 0:
            insight = f"O Autopilot gerou R$ {impacto_total:,.2f} em otimizações simuladas com taxa de aceitação de {taxa_aprovacao:.1f}%."

        return {
            "total_acoes_automaticas": total,
            "impacto_financeiro_simulado_total": round(impacto_total, 2),
            "impacto_medio_por_acao": round(impacto_medio, 2),
            "taxa_aprovacao_implicita": round(taxa_aprovacao, 2),
            "taxa_reversao": round(taxa_reversao, 2),
            "tempo_medio_ate_interacao_minutos": round(tempo_medio_minutos, 2),
            "insight": insight,
            "indicador_confianca": 85 if taxa_aprovacao > 80 else 65
        }
