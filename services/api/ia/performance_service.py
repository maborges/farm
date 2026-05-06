from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, extract
from ia.models import IAAlertaHistorico, IAAcaoAssistidaHistorico, IAComprasRecomendacao, IAUso

class IAPerformanceService:
    """Serviço para consolidação de métricas de performance e ROI da IA (Step 202)."""

    @staticmethod
    async def get_dashboard_metrics(session: AsyncSession, tenant_id: UUID):
        # 1. Taxa de Acerto IA (Step 190)
        # Baseado em feedbacks úteis em recomendações de compra
        q_acerto = select(
            func.count(IAComprasRecomendacao.id).label("total"),
            func.count(case((IAComprasRecomendacao.feedback_util == True, 1))).label("uteis")
        ).where(
            IAComprasRecomendacao.tenant_id == tenant_id,
            IAComprasRecomendacao.feedback_util.isnot(None)
        )
        
        res_acerto = await session.execute(q_acerto)
        row_acerto = res_acerto.one()
        taxa_acerto = (row_acerto.uteis / row_acerto.total * 100) if row_acerto.total > 0 else 0.0

        # 2. Taxa de Execução Alertas (Step 194)
        q_alertas = select(
            func.count(IAAlertaHistorico.id).label("total"),
            func.count(case((IAAlertaHistorico.visualizado_em.isnot(None), 1))).label("visualizados"),
            func.count(case((IAAlertaHistorico.acao_executada == True, 1))).label("executados")
        ).where(IAAlertaHistorico.tenant_id == tenant_id)
        
        res_alertas = await session.execute(q_alertas)
        row_alertas = res_alertas.one()
        taxa_execucao = (row_alertas.executados / row_alertas.visualizados * 100) if row_alertas.visualizados > 0 else 0.0

        # 3. Taxa de Conclusão Ações Assistidas (Step 201)
        q_acoes = select(
            func.count(IAAcaoAssistidaHistorico.id).label("total"),
            func.count(case((IAAcaoAssistidaHistorico.concluida == True, 1))).label("concluidas")
        ).where(IAAcaoAssistidaHistorico.tenant_id == tenant_id)
        
        res_acoes = await session.execute(q_acoes)
        row_acoes = res_acoes.one()
        taxa_conclusao = (row_acoes.concluidas / row_acoes.total * 100) if row_acoes.total > 0 else 0.0

        # 4. Tempo Médio de Decisão (Minutos)
        # Diferença entre visualização e execução nos alertas
        q_tempo = select(
            func.avg(extract('epoch', IAAlertaHistorico.acao_executada_em) - extract('epoch', IAAlertaHistorico.visualizado_em))
        ).where(
            IAAlertaHistorico.tenant_id == tenant_id,
            IAAlertaHistorico.acao_executada == True,
            IAAlertaHistorico.visualizado_em.isnot(None),
            IAAlertaHistorico.acao_executada_em.isnot(None)
        )
        res_tempo = await session.execute(q_tempo)
        tempo_medio_segundos = res_tempo.scalar() or 0
        tempo_medio_minutos = tempo_medio_segundos / 60

        # 5. Economia Total Gerada (Estimativa baseada no impacto financeiro dos alertas concluídos)
        # Procuramos por 'impacto_financeiro' no JSON dos alertas que resultaram em ações concluídas
        economia_total = Decimal("0.0")
        
        # Buscamos alertas executados que tenham impacto financeiro no parâmetros_json
        q_economia = select(IAAlertaHistorico.parametros_json).where(
            IAAlertaHistorico.tenant_id == tenant_id,
            IAAlertaHistorico.acao_executada == True,
            IAAlertaHistorico.parametros_json.isnot(None)
        )
        res_economia = await session.execute(q_economia)
        for row in res_economia.scalars():
            if row and "impacto_financeiro" in row:
                try:
                    economia_total += Decimal(str(row["impacto_financeiro"]))
                except (ValueError, TypeError):
                    pass

        economia_media = (economia_total / row_acoes.concluidas) if row_acoes.concluidas > 0 else Decimal("0")

        # 6. Insights e Funil
        funil = {
            "gerados": row_alertas.total,
            "visualizados": row_alertas.visualizados,
            "executados": row_alertas.executados,
            "concluidos": row_acoes.concluidas
        }

        return {
            "metrics": {
                "taxa_acerto_ia": round(taxa_acerto, 1),
                "taxa_execucao_alertas": round(taxa_execucao, 1),
                "taxa_conclusao_acoes": round(taxa_conclusao, 1),
                "tempo_medio_decisao": round(tempo_medio_minutos, 1),
                "economia_total_gerada": float(economia_total),
                "economia_media_por_decisao": float(economia_media)
            },
            "funil": funil,
            "resumo_performance": f"A IA está gerando economia média de R$ {economia_media:,.2f} por decisão, com taxa de acerto de {taxa_acerto:.1f}%."
        }
