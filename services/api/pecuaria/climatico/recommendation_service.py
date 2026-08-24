from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima
from alert_engine.models import OperationalAlert, AlertStatus
from pecuaria.climatico.schemas import RecomendacaoOperacionalResponse
from agricola.climatico.config import ClimaThresholds

class ClimaPecuariaRecommendationService:
    """Motor de Recomendações Operacionais para Pecuária"""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get_recomendacoes(self, unidade_produtiva_id: UUID) -> list[RecomendacaoOperacionalResponse]:
        # Busca último RegistroClima (Reusando a tabela agrícola de clima base)
        stmt_registro = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).order_by(RegistroClima.data_registro.desc()).limit(1)
        
        result_registro = await self.session.execute(stmt_registro)
        ultimo_registro = result_registro.scalars().first()

        # Busca alertas ativos de clima
        source_types_clima = ['CLIMA_CHUVA_RECENTE', 'CLIMA_VENTO_ALTO', 'CLIMA_TEMPERATURA_EXTREMA']
        stmt_alertas = select(OperationalAlert).filter(
            OperationalAlert.tenant_id == self.tenant_id,
            OperationalAlert.source_id == str(unidade_produtiva_id),
            OperationalAlert.source_type.in_(source_types_clima),
            OperationalAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
        )
        
        result_alertas = await self.session.execute(stmt_alertas)
        alertas = result_alertas.scalars().all()

        alertas_tipos = [a.source_type for a in alertas]

        recomendacoes = []
        data_ref = datetime.utcnow()
        fonte = "CLIMA_RECOMENDACAO_ENGINE_PECUARIA"

        if not ultimo_registro:
            recomendacoes.extend([
                self._build_rec(unidade_produtiva_id, "TRANSPORTE", "SEM_DADOS", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "SUPLEMENTACAO", "SEM_DADOS", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "MANEJO_PASTO", "ATENCAO", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "GERAL", "SEM_DADOS", "WARNING", "Aguardando sincronização climática", {}, data_ref, fonte),
            ])
            return recomendacoes

        dados_utilizados = {
            "vento_kmh": ultimo_registro.vento_kmh,
            "precipitacao_mm": ultimo_registro.precipitacao_mm,
            "temperatura_max": ultimo_registro.temp_max_c,
            "alertas": alertas_tipos
        }

        # Transporte
        rec_transporte = self._avaliar_transporte(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_transporte)

        # Suplementacao
        rec_suplementacao = self._avaliar_suplementacao(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_suplementacao)

        # Manejo de Pasto
        rec_manejo = self._avaliar_manejo_pasto(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_manejo)

        # Geral
        rec_geral = self._avaliar_geral(unidade_produtiva_id, [rec_transporte, rec_suplementacao, rec_manejo], dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_geral)

        return recomendacoes

    def _avaliar_transporte(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        temp_max = reg.temp_max_c or 0
        if temp_max >= 32 or 'CLIMA_TEMPERATURA_EXTREMA' in alertas:
            return self._build_rec(up_id, "TRANSPORTE", "NAO_RECOMENDADO", "CRITICAL", f"Calor excessivo (Máx {temp_max}°C) pode causar alta mortalidade", dados, data_ref, fonte)
        
        if temp_max >= 28:
            return self._build_rec(up_id, "TRANSPORTE", "ATENCAO", "WARNING", "Calor requer atenção na ventilação e lotação do caminhão", dados, data_ref, fonte)
            
        return self._build_rec(up_id, "TRANSPORTE", "RECOMENDADO", "NORMAL", "Condições térmicas favoráveis para transporte", dados, data_ref, fonte)

    def _avaliar_suplementacao(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        chuva = reg.precipitacao_mm or 0
        if 'CLIMA_CHUVA_RECENTE' in alertas or chuva > 15:
            return self._build_rec(up_id, "SUPLEMENTACAO", "ATENCAO", "WARNING", "Risco de molhar e estragar suplementos em cocho aberto", dados, data_ref, fonte)

        return self._build_rec(up_id, "SUPLEMENTACAO", "RECOMENDADO", "NORMAL", "Condições favoráveis para reposição de cochos", dados, data_ref, fonte)

    def _avaliar_manejo_pasto(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        chuva = reg.precipitacao_mm or 0
        
        if 'CLIMA_CHUVA_RECENTE' in alertas or chuva > 30:
            return self._build_rec(up_id, "MANEJO_PASTO", "ATENCAO", "WARNING", "Excesso de chuvas pode causar pisoteio e compactação excessiva do pasto", dados, data_ref, fonte)
            
        if 'CLIMA_VENTO_ALTO' in alertas:
            return self._build_rec(up_id, "MANEJO_PASTO", "ATENCAO", "WARNING", "Ventos muito fortes, evite manejo perto de áreas de risco", dados, data_ref, fonte)

        return self._build_rec(up_id, "MANEJO_PASTO", "RECOMENDADO", "NORMAL", "Condições de pastagem e clima favoráveis para movimentação", dados, data_ref, fonte)

    def _avaliar_geral(self, up_id: UUID, recs: list[RecomendacaoOperacionalResponse], dados: dict, data_ref: datetime, fonte: str):
        status_set = {r.status for r in recs}
        
        if "NAO_RECOMENDADO" in status_set:
            return self._build_rec(up_id, "GERAL", "CRITICO", "CRITICAL", "Clima crítico para certas operações pecuárias", dados, data_ref, fonte)
        
        if "ATENCAO" in status_set:
            return self._build_rec(up_id, "GERAL", "ATENCAO", "WARNING", "Clima exige atenção no manejo diário", dados, data_ref, fonte)

        return self._build_rec(up_id, "GERAL", "FAVORAVEL", "NORMAL", "Clima favorável geral para rotina zootécnica", dados, data_ref, fonte)

    def _build_rec(self, up_id: UUID, tipo: str, status: str, severidade: str, motivo: str, dados: dict, data_ref: datetime, fonte: str):
        return RecomendacaoOperacionalResponse(
            unidade_produtiva_id=up_id,
            tipo_operacao=tipo,
            status=status,
            severidade=severidade,
            motivo=motivo,
            dados_utilizados=dados,
            data_referencia=data_ref,
            fonte=fonte,
            validade_horas=12
        )
