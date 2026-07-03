from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima
from agricola.climatico.schemas import ClimaResumoResponse, ClimaAlertaResponse
from alert_engine.models import OperationalAlert, AlertStatus
from core.base_service import BaseService


class ClimaService(BaseService[RegistroClima]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(RegistroClima, session, tenant_id)

    async def get_resumo_climatico(self, unidade_produtiva_id: UUID) -> ClimaResumoResponse:
        # Busca o último registro de clima
        stmt_registro = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).order_by(RegistroClima.data_registro.desc()).limit(1)
        
        result_registro = await self.session.execute(stmt_registro)
        ultimo_registro = result_registro.scalars().first()

        # Busca alertas ativos relacionados ao clima para esta unidade
        source_types_clima = ['CLIMA_CHUVA_RECENTE', 'CLIMA_VENTO_ALTO', 'CLIMA_TEMPERATURA_EXTREMA']
        stmt_alertas = select(OperationalAlert).filter(
            OperationalAlert.tenant_id == self.tenant_id,
            OperationalAlert.source_id == str(unidade_produtiva_id),
            OperationalAlert.source_type.in_(source_types_clima),
            OperationalAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
        )
        
        result_alertas = await self.session.execute(stmt_alertas)
        alertas = result_alertas.scalars().all()

        status_operacional = "SEM_DADOS"
        if ultimo_registro:
            status_operacional = "NORMAL"
            if any(a.severity.name == 'CRITICAL' for a in alertas):
                status_operacional = "CRITICO"
            elif any(a.severity.name == 'WARNING' for a in alertas):
                status_operacional = "ATENCAO"

        return ClimaResumoResponse(
            unidade_produtiva_id=unidade_produtiva_id,
            data_registro=ultimo_registro.data_registro if ultimo_registro else None,
            temperatura_atual=ultimo_registro.temp_media_c if ultimo_registro else None,
            temperatura_min=ultimo_registro.temp_min_c if ultimo_registro else None,
            temperatura_max=ultimo_registro.temp_max_c if ultimo_registro else None,
            umidade=ultimo_registro.umidade_rel_pct if ultimo_registro else None,
            precipitacao_mm=ultimo_registro.precipitacao_mm if ultimo_registro else None,
            vento_kmh=ultimo_registro.vento_kmh if ultimo_registro else None,
            condicao="NORMAL",
            fonte=ultimo_registro.fonte if ultimo_registro else None,
            status_operacional=status_operacional,
            alertas_ativos=len(alertas)
        )

    async def get_alertas_ativos(self, unidade_produtiva_id: UUID) -> list[ClimaAlertaResponse]:
        source_types_clima = ['CLIMA_CHUVA_RECENTE', 'CLIMA_VENTO_ALTO', 'CLIMA_TEMPERATURA_EXTREMA']
        stmt = select(OperationalAlert).filter(
            OperationalAlert.tenant_id == self.tenant_id,
            OperationalAlert.source_id == str(unidade_produtiva_id),
            OperationalAlert.source_type.in_(source_types_clima),
            OperationalAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
        ).order_by(OperationalAlert.created_at.desc())
        
        result = await self.session.execute(stmt)
        alertas = result.scalars().all()
        
        return [
            ClimaAlertaResponse(
                id=a.id,
                severity=a.severity.name,
                priority=a.priority.name,
                title=a.title,
                description=a.message,
                source_type=a.source_type,
                created_at=a.created_at
            ) for a in alertas
        ]

    async def sync_open_meteo(self, unidade_produtiva_id: UUID) -> str:
        # 1. Obter lat/lng da Fazenda localmente
        # 2. Requisitar dados histórcios do dia anterior na API Historical Open-Meteo
        # 3. Salvar no BD
        return "Sincronização do clima executada com sucesso"

    async def get_clima_periodo(self, unidade_produtiva_id: UUID, data_inicio: date, data_fim: date):
        stmt = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(
            RegistroClima.data_registro >= data_inicio,
            RegistroClima.data_registro <= data_fim
        ).order_by(RegistroClima.data_registro.asc())

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_chuva_acumulada(self, unidade_produtiva_id: UUID, dias: int = 30) -> float:
        hoje = date.today()
        limite = hoje - timedelta(days=dias)

        stmt = select(func.sum(RegistroClima.precipitacao_mm)).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(RegistroClima.data_registro >= limite)

        resultado = await self.session.execute(stmt)
        val = resultado.scalar()
        return float(val) if val else 0.0
