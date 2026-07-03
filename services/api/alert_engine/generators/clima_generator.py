from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from agricola.climatico.models import RegistroClima
from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult
from agricola.climatico.config import ClimaThresholds


@register_alert_generator
class ClimaAlertGenerator(BaseAlertGenerator):
    """Generates canonical alerts for climate operational signals."""

    generator_name = "clima"
    domain = Domain.AGRICULTURE
    category = Category.CLIMATICO
    execution_modes = ("scheduled", "hybrid")

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute climate rules from canonical context."""

        await set_rls_context(self.session, context.tenant_id)

        counters = {
            "chuva_recente": 0,
            "vento_alto": 0,
            "temperatura_extrema": 0,
        }

        result = AlertGeneratorResult(
            generator_name=self.generator_name,
            metadata={"rule_counters": counters},
        )

        # Parâmetros com fallback para default (defensivo)
        chuva_alerta_mm = self._metadata_float(context, "chuva_alerta_mm", ClimaThresholds.CHUVA_ALERTA_MM)
        vento_alerta_kmh = self._metadata_float(context, "vento_alerta_kmh", ClimaThresholds.VENTO_ALERTA_KMH)
        temperatura_min_c = self._metadata_float(context, "temperatura_min_c", ClimaThresholds.TEMPERATURA_MIN_C)
        temperatura_max_c = self._metadata_float(context, "temperatura_max_c", ClimaThresholds.TEMPERATURA_MAX_C)
        janela_horas = self._metadata_int(context, "janela_horas", 24)

        data_limite = date.today() - timedelta(hours=janela_horas)

        registros = await self._listar_registros_climaticos(
            tenant_id=context.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            data_limite=data_limite
        )

        for reg in registros:
            # 1. Alerta de chuva recente
            if reg.precipitacao_mm is not None and float(reg.precipitacao_mm) > chuva_alerta_mm:
                created = await self._gerar_alerta(
                    tenant_id=context.tenant_id,
                    unidade_produtiva_id=reg.unidade_produtiva_id,
                    category=Category.CLIMATICO,
                    severity=Severity.WARNING,
                    priority=Priority.HIGH,
                    title="Atenção: Chuva recente na Unidade Produtiva",
                    message=f"A precipitação registrada foi de {reg.precipitacao_mm} mm nas últimas horas, excedendo o limite de {chuva_alerta_mm} mm.",
                    source_type="CLIMA_CHUVA_RECENTE",
                    source_id=str(reg.id),
                    dedupe_key=f"clima:chuva:{reg.unidade_produtiva_id}:{reg.data_registro.isoformat()}",
                    entity_type="registro_clima",
                    entity_id=reg.id,
                    metadata={
                        "precipitacao_mm": float(reg.precipitacao_mm),
                        "limite": chuva_alerta_mm,
                        "data_registro": reg.data_registro.isoformat()
                    }
                )
                result.created += created
                result.updated += 1 - created if created in {0, 1} else 0
                counters["chuva_recente"] += created

            # 2. Alerta de vento alto
            if reg.vento_kmh is not None and float(reg.vento_kmh) > vento_alerta_kmh:
                severity = Severity.CRITICAL if float(reg.vento_kmh) > (vento_alerta_kmh * 1.5) else Severity.WARNING
                created = await self._gerar_alerta(
                    tenant_id=context.tenant_id,
                    unidade_produtiva_id=reg.unidade_produtiva_id,
                    category=Category.CLIMATICO,
                    severity=severity,
                    priority=Priority.HIGH,
                    title="Atenção: Vento alto na Unidade Produtiva",
                    message=f"O vento registrado foi de {reg.vento_kmh} km/h, excedendo o limite de {vento_alerta_kmh} km/h. Risco operacional detectado.",
                    source_type="CLIMA_VENTO_ALTO",
                    source_id=str(reg.id),
                    dedupe_key=f"clima:vento:{reg.unidade_produtiva_id}:{reg.data_registro.isoformat()}",
                    entity_type="registro_clima",
                    entity_id=reg.id,
                    metadata={
                        "vento_kmh": float(reg.vento_kmh),
                        "limite": vento_alerta_kmh,
                        "data_registro": reg.data_registro.isoformat()
                    }
                )
                result.created += created
                result.updated += 1 - created if created in {0, 1} else 0
                counters["vento_alto"] += created

            # 3. Temperatura extrema
            temp = None
            if reg.temp_max_c is not None and float(reg.temp_max_c) > temperatura_max_c:
                temp = float(reg.temp_max_c)
            elif reg.temp_min_c is not None and float(reg.temp_min_c) < temperatura_min_c:
                temp = float(reg.temp_min_c)
            elif reg.temp_media_c is not None and (float(reg.temp_media_c) > temperatura_max_c or float(reg.temp_media_c) < temperatura_min_c):
                temp = float(reg.temp_media_c)

            if temp is not None:
                created = await self._gerar_alerta(
                    tenant_id=context.tenant_id,
                    unidade_produtiva_id=reg.unidade_produtiva_id,
                    category=Category.CLIMATICO,
                    severity=Severity.WARNING,
                    priority=Priority.HIGH,
                    title="Atenção: Temperatura Extrema",
                    message=f"Temperatura extrema detectada ({temp} °C). Pode causar estresse térmico.",
                    source_type="CLIMA_TEMPERATURA_EXTREMA",
                    source_id=str(reg.id),
                    dedupe_key=f"clima:temperatura:{reg.unidade_produtiva_id}:{reg.data_registro.isoformat()}",
                    entity_type="registro_clima",
                    entity_id=reg.id,
                    metadata={
                        "temperatura": temp,
                        "min_limite": temperatura_min_c,
                        "max_limite": temperatura_max_c,
                        "data_registro": reg.data_registro.isoformat()
                    }
                )
                result.created += created
                result.updated += 1 - created if created in {0, 1} else 0
                counters["temperatura_extrema"] += created

        result.metadata = {"rule_counters": counters}
        return result

    async def _listar_registros_climaticos(self, tenant_id: UUID, unidade_produtiva_id: UUID | None, data_limite: date) -> list[RegistroClima]:
        stmt = select(RegistroClima).where(
            RegistroClima.tenant_id == tenant_id,
            RegistroClima.data_registro >= data_limite
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(RegistroClima.unidade_produtiva_id == unidade_produtiva_id)

        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def _gerar_alerta(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        category: Category,
        severity: Severity,
        priority: Priority,
        title: str,
        message: str,
        source_type: str,
        source_id: str,
        dedupe_key: str,
        entity_type: str,
        entity_id: UUID,
        metadata: dict[str, object],
    ) -> int:
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=Domain.AGRICULTURE,
            category=category,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            status=AlertStatus.OPEN,
            trigger_type=TriggerType.SCHEDULE,
            source_type=source_type,
            source_id=source_id,
            entity_type=entity_type,
            entity_id=entity_id,
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=dedupe_key,
            context=metadata,
        )
        await AlertLifecycleService(self.session, tenant_id).create_or_update_alert(payload)
        return 0 if was_update else 1

    @staticmethod
    def _metadata_int(context: AlertGeneratorContext, key: str, default: int) -> int:
        value = context.metadata.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metadata_float(context: AlertGeneratorContext, key: str, default: float) -> float:
        value = context.metadata.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
