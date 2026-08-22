from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima
from core.models.unidade_produtiva import UnidadeProdutiva
from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber


async def _assert_unit_belongs_to_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    unidade_produtiva_id: UUID,
) -> None:
    stmt = select(UnidadeProdutiva.id).where(
        UnidadeProdutiva.id == unidade_produtiva_id,
        UnidadeProdutiva.tenant_id == tenant_id,
        UnidadeProdutiva.ativo.is_(True),
    )
    if (await session.execute(stmt)).scalar_one_or_none() is None:
        raise ValueError("Unidade produtiva não pertence ao tenant do evento")


@register_event_subscriber
class ClimaEventSubscriber(EventSubscriber):
    """Subscriber que persiste dados climáticos a partir do provider de Integração."""

    subscriber_name = "climatico-ingestion"
    event_types = (
        "agricola.climatico.sync_realizado",
    )

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        if self.session is None:
            raise ValueError("session must be provided for ClimaEventSubscriber")

        started_at = datetime.now(timezone.utc)

        # Desempacotar dados
        unidade_produtiva_id = event.model_dump().get("unidade_produtiva_id")
        provider = event.model_dump().get("provider", "OPENWEATHER")
        await _assert_unit_belongs_to_tenant(self.session, event.tenant_id, unidade_produtiva_id)
        occurred_at = event.model_dump().get("occurred_at")
        if not occurred_at:
            occurred_at = started_at
        elif isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)

        data_registro = occurred_at.date()

        chuva_mm = event.model_dump().get("chuva_mm")
        temperatura = event.model_dump().get("temperatura")
        umidade = event.model_dump().get("umidade")
        vento_kmh = event.model_dump().get("vento_kmh")

        # Idempotência: verificar se já existe registro na mesma data
        stmt = select(RegistroClima).where(
            RegistroClima.tenant_id == event.tenant_id,
            RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
            RegistroClima.data_registro == data_registro,
            RegistroClima.fonte == provider
        )

        registro = (await self.session.execute(stmt)).scalars().first()
        created = 0
        updated = 0

        if registro:
            # Atualizar se mudou
            registro.precipitacao_mm = chuva_mm
            registro.temp_media_c = temperatura
            registro.umidade_rel_pct = umidade
            registro.vento_kmh = vento_kmh
            updated = 1
        else:
            # Criar novo
            registro = RegistroClima(
                tenant_id=event.tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                data_registro=data_registro,
                precipitacao_mm=chuva_mm,
                temp_media_c=temperatura,
                umidade_rel_pct=umidade,
                vento_kmh=vento_kmh,
                fonte=provider
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(registro)
                    await self.session.flush()
                created = 1
            except IntegrityError:
                stmt_existing = select(RegistroClima).where(
                    RegistroClima.tenant_id == event.tenant_id,
                    RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
                    RegistroClima.data_registro == data_registro,
                    RegistroClima.fonte == provider,
                )
                registro = (await self.session.execute(stmt_existing)).scalars().one()
                registro.precipitacao_mm = chuva_mm
                registro.temp_media_c = temperatura
                registro.umidade_rel_pct = umidade
                registro.vento_kmh = vento_kmh
                updated = 1

        await self.session.flush()

        finished_at = datetime.now(timezone.utc)
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status="success",
            created=created,
            updated=updated,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000)
        )


@register_event_subscriber
class PrevisaoClimaEventSubscriber(EventSubscriber):
    """Subscriber que persiste dados de previsão climática."""

    subscriber_name = "previsao-climatico-ingestion"
    event_types = (
        "agricola.climatico.previsao_sync_realizado",
    )

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        if self.session is None:
            raise ValueError("session must be provided")

        started_at = datetime.now(timezone.utc).replace(tzinfo=None)

        unidade_produtiva_id = event.model_dump().get("unidade_produtiva_id")
        previsoes = event.model_dump().get("previsoes", [])
        await _assert_unit_belongs_to_tenant(self.session, event.tenant_id, unidade_produtiva_id)

        created = 0
        updated = 0

        from agricola.climatico.models import PrevisaoClima

        for prev in previsoes:
            data_previsao_str = prev.get("data_previsao")
            if not data_previsao_str:
                continue

            data_previsao = datetime.fromisoformat(data_previsao_str).date() if isinstance(data_previsao_str, str) else data_previsao_str

            stmt = select(PrevisaoClima).where(
                PrevisaoClima.tenant_id == event.tenant_id,
                PrevisaoClima.unidade_produtiva_id == unidade_produtiva_id,
                PrevisaoClima.data_previsao == data_previsao
            )
            registro = (await self.session.execute(stmt)).scalars().first()

            if registro:
                registro.precipitacao_mm = prev.get("precipitacao_mm")
                registro.temp_max_c = prev.get("temp_max_c")
                registro.temp_min_c = prev.get("temp_min_c")
                registro.probabilidade_chuva_pct = prev.get("probabilidade_chuva_pct")
                registro.periodos = prev.get("periodos", [])
                registro.atualizado_em = started_at
                updated += 1
            else:
                registro = PrevisaoClima(
                    tenant_id=event.tenant_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    data_previsao=data_previsao,
                    precipitacao_mm=prev.get("precipitacao_mm"),
                    temp_max_c=prev.get("temp_max_c"),
                    temp_min_c=prev.get("temp_min_c"),
                    probabilidade_chuva_pct=prev.get("probabilidade_chuva_pct"),
                    periodos=prev.get("periodos", []),
                )
                try:
                    async with self.session.begin_nested():
                        self.session.add(registro)
                        await self.session.flush()
                    created += 1
                except IntegrityError:
                    stmt_existing = select(PrevisaoClima).where(
                        PrevisaoClima.tenant_id == event.tenant_id,
                        PrevisaoClima.unidade_produtiva_id == unidade_produtiva_id,
                        PrevisaoClima.data_previsao == data_previsao,
                    )
                    registro = (await self.session.execute(stmt_existing)).scalars().one()
                    registro.precipitacao_mm = prev.get("precipitacao_mm")
                    registro.temp_max_c = prev.get("temp_max_c")
                    registro.temp_min_c = prev.get("temp_min_c")
                    registro.probabilidade_chuva_pct = prev.get("probabilidade_chuva_pct")
                    registro.periodos = prev.get("periodos", [])
                    registro.atualizado_em = started_at
                    updated += 1

        await self.session.flush()

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status="success",
            created=created,
            updated=updated,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000)
        )
