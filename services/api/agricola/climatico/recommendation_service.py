from datetime import datetime, date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima
from agricola.climatico.schemas import RecomendacaoOperacionalResponse
from agricola.climatico.config import ClimaThresholds
from alert_engine.models import OperationalAlert, AlertStatus


class ClimaRecommendationService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get_recomendacoes(self, unidade_produtiva_id: UUID) -> list[RecomendacaoOperacionalResponse]:
        # Busca último RegistroClima
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
        fonte = "CLIMA_RECOMENDACAO_ENGINE"

        if not ultimo_registro:
            # Sem dados, não podemos recomendar pulverização nem colheita com segurança
            recomendacoes.extend([
                self._build_rec(unidade_produtiva_id, "PULVERIZACAO", "SEM_DADOS", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "COLHEITA", "SEM_DADOS", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "ADUBACAO", "ATENCAO", "WARNING", "Sem dados climáticos recentes", {}, data_ref, fonte),
                self._build_rec(unidade_produtiva_id, "GERAL", "SEM_DADOS", "WARNING", "Aguardando sincronização climática", {}, data_ref, fonte),
            ])
            return recomendacoes

        dados_utilizados = {
            "vento_kmh": ultimo_registro.vento_kmh,
            "precipitacao_mm": ultimo_registro.precipitacao_mm,
            "temperatura_max": ultimo_registro.temp_max_c,
            "alertas": alertas_tipos
        }

        # Pulverização
        rec_pulv = self._avaliar_pulverizacao(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_pulv)

        # Colheita
        rec_colheita = self._avaliar_colheita(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_colheita)

        # Adubação
        rec_adubacao = self._avaliar_adubacao(unidade_produtiva_id, ultimo_registro, alertas_tipos, dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_adubacao)

        # Geral
        rec_geral = self._avaliar_geral(unidade_produtiva_id, [rec_pulv, rec_colheita, rec_adubacao], dados_utilizados, data_ref, fonte)
        recomendacoes.append(rec_geral)

        return recomendacoes

    def _avaliar_pulverizacao(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        vento = reg.vento_kmh or 0
        if vento > ClimaThresholds.VENTO_ALERTA_KMH:
            return self._build_rec(up_id, "PULVERIZACAO", "NAO_RECOMENDADO", "CRITICAL", f"Vento excessivo ({vento} km/h)", dados, data_ref, fonte)
        
        if 'CLIMA_VENTO_ALTO' in alertas:
            return self._build_rec(up_id, "PULVERIZACAO", "NAO_RECOMENDADO", "CRITICAL", "Alerta de vento alto ativo", dados, data_ref, fonte)
        
        if 'CLIMA_TEMPERATURA_EXTREMA' in alertas:
            return self._build_rec(up_id, "PULVERIZACAO", "ATENCAO", "WARNING", "Temperatura extrema pode afetar absorção", dados, data_ref, fonte)
            
        if 'CLIMA_CHUVA_RECENTE' in alertas:
            return self._build_rec(up_id, "PULVERIZACAO", "ATENCAO", "WARNING", "Risco de lavagem de defensivos", dados, data_ref, fonte)

        return self._build_rec(up_id, "PULVERIZACAO", "RECOMENDADO", "NORMAL", "Condições favoráveis", dados, data_ref, fonte)

    def _avaliar_colheita(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        chuva = reg.precipitacao_mm or 0
        if 'CLIMA_CHUVA_RECENTE' in alertas or chuva > ClimaThresholds.CHUVA_ALERTA_MM:
            return self._build_rec(up_id, "COLHEITA", "ATENCAO", "WARNING", "Chuva recente pode afetar umidade do grão", dados, data_ref, fonte)
        
        if 'CLIMA_VENTO_ALTO' in alertas:
            return self._build_rec(up_id, "COLHEITA", "ATENCAO", "WARNING", "Ventos fortes podem dificultar operação", dados, data_ref, fonte)

        if 'CLIMA_TEMPERATURA_EXTREMA' in alertas:
            return self._build_rec(up_id, "COLHEITA", "ATENCAO", "WARNING", "Calor excessivo no campo", dados, data_ref, fonte)

        return self._build_rec(up_id, "COLHEITA", "RECOMENDADO", "NORMAL", "Condições favoráveis", dados, data_ref, fonte)

    def _avaliar_adubacao(self, up_id: UUID, reg: RegistroClima, alertas: list[str], dados: dict, data_ref: datetime, fonte: str):
        if 'CLIMA_CHUVA_RECENTE' in alertas:
            return self._build_rec(up_id, "ADUBACAO", "ATENCAO", "WARNING", "Risco de lixiviação de nutrientes pela chuva", dados, data_ref, fonte)

        return self._build_rec(up_id, "ADUBACAO", "RECOMENDADO", "NORMAL", "Condições favoráveis", dados, data_ref, fonte)

    def _avaliar_geral(self, up_id: UUID, recs: list[RecomendacaoOperacionalResponse], dados: dict, data_ref: datetime, fonte: str):
        status_set = {r.status for r in recs}
        
        if "NAO_RECOMENDADO" in status_set:
            return self._build_rec(up_id, "GERAL", "CRITICO", "CRITICAL", "Clima crítico para operações", dados, data_ref, fonte)
        
        if "ATENCAO" in status_set:
            return self._build_rec(up_id, "GERAL", "ATENCAO", "WARNING", "Clima exige atenção", dados, data_ref, fonte)

        return self._build_rec(up_id, "GERAL", "FAVORAVEL", "NORMAL", "Clima favorável geral", dados, data_ref, fonte)

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
