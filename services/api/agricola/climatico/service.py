from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import cast, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima, PrevisaoClima
from agricola.climatico.schemas import ClimaResumoResponse, ClimaAlertaResponse, PrevisaoClimaResponse
from alert_engine.models import OperationalAlert, AlertStatus
from core.base_service import BaseService


class ClimaService(BaseService[RegistroClima]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(RegistroClima, session, tenant_id)

    async def _ensure_tenant_context(self) -> None:
        """Reaplica o tenant antes das leituras protegidas por RLS."""
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )

    async def get_resumo_climatico(self, unidade_produtiva_id: UUID) -> ClimaResumoResponse:
        await self._ensure_tenant_context()
        # Busca o último registro de clima
        stmt_registro = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).order_by(RegistroClima.data_registro.desc()).limit(1)

        result_registro = await self.session.execute(stmt_registro)
        ultimo_registro = result_registro.scalars().first()

        # Busca alertas ativos relacionados ao clima para esta unidade
        alertas = await self._fetch_alertas_clima(unidade_produtiva_id)

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
            condicao=None,
            fonte=ultimo_registro.fonte if ultimo_registro else None,
            status_operacional=status_operacional,
            alertas_ativos=len(alertas)
        )

    async def _fetch_alertas_clima(self, unidade_produtiva_id: UUID) -> list:
        """Busca alertas climáticos ativos para a unidade, usando cast explícito para evitar
        conflitos de tipo UUID vs VARCHAR no asyncpg."""
        source_types_clima = ['CLIMA_CHUVA_RECENTE', 'CLIMA_VENTO_ALTO', 'CLIMA_TEMPERATURA_EXTREMA']
        stmt = select(OperationalAlert).where(
            cast(OperationalAlert.tenant_id, PG_UUID) == cast(str(self.tenant_id), PG_UUID),
            OperationalAlert.source_id == str(unidade_produtiva_id),
            OperationalAlert.source_type.in_(source_types_clima),
            OperationalAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
        ).order_by(OperationalAlert.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_alertas_ativos(self, unidade_produtiva_id: UUID) -> list[ClimaAlertaResponse]:
        await self._ensure_tenant_context()
        alertas = await self._fetch_alertas_clima(unidade_produtiva_id)
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

    async def get_previsoes_unidade(self, unidade_produtiva_id: UUID, dias: int = 5) -> list[PrevisaoClima]:
        """Retorna previsões de clima para os próximos `dias` dias para a unidade produtiva."""
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje + timedelta(days=dias)
        stmt = select(PrevisaoClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        ).where(
            PrevisaoClima.data_previsao >= hoje,
            PrevisaoClima.data_previsao <= limite,
        ).order_by(PrevisaoClima.data_previsao.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_clima_periodo(self, unidade_produtiva_id: UUID, data_inicio: date, data_fim: date):
        await self._ensure_tenant_context()
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
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje - timedelta(days=dias)

        stmt = select(func.sum(RegistroClima.precipitacao_mm)).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(RegistroClima.data_registro >= limite)

        resultado = await self.session.execute(stmt)
        val = resultado.scalar()
        return float(val) if val else 0.0

    async def get_analise_avancada(self, unidade_produtiva_id: UUID, dias_historico: int = 30) -> dict:
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje - timedelta(days=dias_historico)

        stmt = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(RegistroClima.data_registro >= limite).order_by(RegistroClima.data_registro.asc())

        result = await self.session.execute(stmt)
        registros = result.scalars().all()

        historico = []
        gdu_acumulado = 0.0
        chuva_acumulada = 0.0
        temp_base = 10.0

        for r in registros:
            if r.temp_max_c is not None and r.temp_min_c is not None:
                gdu_dia = max(0.0, float((r.temp_max_c + r.temp_min_c) / 2) - temp_base)
                gdu_acumulado += gdu_dia

            if r.precipitacao_mm is not None:
                chuva_acumulada += float(r.precipitacao_mm)

            historico.append({
                "data": r.data_registro,
                "temp_min": float(r.temp_min_c) if r.temp_min_c is not None else None,
                "temp_max": float(r.temp_max_c) if r.temp_max_c is not None else None,
                "temp_media": float(r.temp_media_c) if r.temp_media_c is not None else None,
                "precipitacao": float(r.precipitacao_mm) if r.precipitacao_mm is not None else None
            })

        stmt_prev = select(PrevisaoClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(PrevisaoClima.data_previsao >= hoje).order_by(PrevisaoClima.data_previsao.asc()).limit(5)

        result_prev = await self.session.execute(stmt_prev)
        previsoes = result_prev.scalars().all()

        riscos = []

        min_temp_prevista = min([float(p.temp_min_c) for p in previsoes if p.temp_min_c is not None], default=99.0)
        if min_temp_prevista <= 4.0:
            riscos.append({
                "tipo": "Geada",
                "nivel": "CRITICO" if min_temp_prevista <= 0 else "ALTO",
                "mensagem": f"Alerta de geada nos próximos dias. Temperatura mínima prevista: {min_temp_prevista}°C",
                "data_alerta": None
            })

        chuva_prevista = sum([float(p.precipitacao_mm) for p in previsoes if p.precipitacao_mm is not None])
        if chuva_acumulada < 30.0 and chuva_prevista < 10.0:
            riscos.append({
                "tipo": "Estresse Hídrico",
                "nivel": "ALTO",
                "mensagem": "Baixo volume de chuva nos últimos 30 dias e pouca previsão de precipitação.",
                "data_alerta": None
            })

        if not riscos:
            riscos.append({
                "tipo": "Normal",
                "nivel": "BAIXO",
                "mensagem": "Condições climáticas dentro da normalidade.",
                "data_alerta": hoje
            })

        return {
            "gdu_acumulado": round(gdu_acumulado, 2),
            "gdu_progresso_pct": None,
            "riscos": riscos,
            "historico": historico
        }
