from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import RegistroClima
from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber


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
            self.session.add(registro)
            created = 1

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
