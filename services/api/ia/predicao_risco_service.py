import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from financeiro.services.lancamento_service import LancamentoService
from financeiro.services.cenario_service import CenarioFinanceiroService
from agricola.safras.models import Safra

class IAPredicaoRiscoService:
    """
    Motor preditivo inicial do Copiloto IA (Step 205).
    Analisa tendências históricas para antecipar riscos financeiros.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def prever_risco_financeiro(self, safra_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Analisa a evolução de receitas e custos para prever riscos nos próximos 7-14 dias.
        """
        if not safra_id:
            # Busca safra mais recente
            stmt = select(Safra.id).where(Safra.tenant_id == self.tenant_id).order_by(Safra.created_at.desc()).limit(1)
            safra_id = (await self.session.execute(stmt)).scalar_one_or_none()
            
        if not safra_id:
            return {
                "risco": "BAIXO",
                "descricao": "Nenhuma safra encontrada para análise preditiva.",
                "impacto_estimado": 0.0,
                "tempo_estimado": "N/A",
                "acao_recomendada": "Inicie uma nova safra para habilitar previsões.",
                "confianca": 0.0
            }

        logger.info(f"[IAPredicao] Iniciando análise preditiva para safra {safra_id}")

        # 1. Obter dados históricos (últimos 60 dias)
        data_inicio = datetime.now() - timedelta(days=60)
        
        # Simulamos a obtenção de séries temporais de fluxo de caixa
        # Em um cenário real, buscaríamos agregados por dia/semana
        historico_custos = await self._obter_serie_custos(safra_id, data_inicio)
        historico_receitas = await self._obter_serie_receitas(safra_id, data_inicio)
        
        if not historico_custos or len(historico_custos) < 3:
            return {
                "risco": "BAIXO",
                "descricao": "Dados insuficientes para projeção preditiva confiável.",
                "impacto_estimado": 0.0,
                "tempo_estimado": "N/A",
                "acao_recomendada": "Continue registrando lançamentos para habilitar previsões.",
                "confianca": 0.0
            }

        # 2. Calcular Tendências (Delta)
        tendencia_custo = self._calcular_tendencia(historico_custos)
        tendencia_receita = self._calcular_tendencia(historico_receitas)

        # 3. Projetar Margem
        # Se o custo sobe mais rápido que a receita, há risco de compressão de margem
        risco_score = 0
        status_risco = "BAIXO"
        descricao = "A saúde financeira da safra parece estável para os próximos 15 dias."
        acao = "Manter monitoramento atual."
        tempo = "15 dias"
        
        desvio_custo_percentual = tendencia_custo * 100
        
        if tendencia_custo > 0.05 and tendencia_receita <= tendencia_custo:
            risco_score = 70
            status_risco = "ALTO"
            descricao = f"Risco de compressão de margem: custos operacionais apresentam tendência de alta de {desvio_custo_percentual:.1f}% para as próximas semanas."
            acao = "Revisar contratos de insumos ou antecipar vendas para garantir liquidez."
            tempo = "7 a 10 dias"
        elif tendencia_custo > 0.02:
            risco_score = 40
            status_risco = "MEDIO"
            descricao = "Alerta de tendência: crescimento progressivo de custos acima do planejado."
            acao = "Simular cenário de ajuste de custos operacionais."
            tempo = "14 dias"

        return {
            "risco": status_risco,
            "descricao": descricao,
            "impacto_estimado": abs(tendencia_custo * 10000), # Simulação de impacto financeiro
            "tempo_estimado": tempo,
            "acao_recomendada": acao,
            "confianca": 0.75 if len(historico_custos) > 10 else 0.5,
            "tendencia_custo": tendencia_custo,
            "tendencia_receita": tendencia_receita
        }

    async def _obter_serie_custos(self, safra_id: uuid.UUID, desde: datetime) -> List[float]:
        """Busca histórico de custos agregados para análise de tendência."""
        from financeiro.models.lancamento import LancamentoFinanceiro
        from sqlalchemy import func, and_

        stmt = select(func.sum(LancamentoFinanceiro.valor)).where(
            and_(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.safra_id == safra_id,
                LancamentoFinanceiro.tipo == "CUSTO",
                LancamentoFinanceiro.data >= desde
            )
        ).group_by(LancamentoFinanceiro.data).order_by(LancamentoFinanceiro.data)
        
        result = await self.session.execute(stmt)
        return [float(row[0]) for row in result.all()]

    async def _obter_serie_receitas(self, safra_id: uuid.UUID, desde: datetime) -> List[float]:
        """Busca histórico de receitas agregadas."""
        from financeiro.models.lancamento import LancamentoFinanceiro
        from sqlalchemy import func, and_

        stmt = select(func.sum(LancamentoFinanceiro.valor)).where(
            and_(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.safra_id == safra_id,
                LancamentoFinanceiro.tipo == "RECEITA",
                LancamentoFinanceiro.data >= desde
            )
        ).group_by(LancamentoFinanceiro.data).order_by(LancamentoFinanceiro.data)
        
        result = await self.session.execute(stmt)
        return [float(row[0]) for row in result.all()]

    def _calcular_tendencia(self, serie: List[float]) -> float:
        """
        Calcula a inclinação da tendência (regressão linear simplificada).
        Retorna a variação percentual média entre os períodos.
        """
        if len(serie) < 2:
            return 0.0
        
        variacoes = []
        for i in range(1, len(serie)):
            prev = serie[i-1] if serie[i-1] != 0 else 1
            var = (serie[i] - serie[i-1]) / prev
            variacoes.append(var)
        
        return sum(variacoes) / len(variacoes)
