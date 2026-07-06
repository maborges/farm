from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from events.base import DomainEvent, EventSubscriber, EventSubscriberResult
from events.registry import register_event_subscriber
from integracoes.events import IntegrationSyncRequested
from integracoes.sankhya.services import (
    SankhyaSyncService,
    SankhyaPessoaService,
    SankhyaProdutoService
)


@register_event_subscriber
class SankhyaSyncEventSubscriber(EventSubscriber):
    """Subscriber that listens to sync requested events and executes initial syncs."""

    subscriber_name = "sankhya-sync"
    event_types = ("integrations.sync_requested",)

    def __init__(self, session: AsyncSession | None = None) -> None:
        super().__init__(session=session)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        started_at = datetime.now(timezone.utc)
        bound_logger = self._logger(event)
        bound_logger.info("sankhya_sync_event_subscriber_started")

        if not isinstance(event, IntegrationSyncRequested):
            event = IntegrationSyncRequested.model_validate(event.model_dump())

        features = event.features or []
        
        errors = 0
        warnings = 0
        processed = 0

        if not self.session:
            raise ValueError("session must be provided for SankhyaSyncEventSubscriber")

        sync_service = SankhyaSyncService(self.session)
        pessoa_service = SankhyaPessoaService(self.session)
        produto_service = SankhyaProdutoService(self.session)

        tenant_scope = str(event.tenant_id)

        config = await sync_service.get_config(tenant_scope)
        if not config or config.id != event.config_id:
            bound_logger.warning("sankhya_sync_event_subscriber_config_mismatch_or_not_found")
            return self._to_result(event, started_at, status="skipped", warnings=1)

        for feature in features:
            if feature not in ("pessoas", "produtos"):
                warnings += 1
                bound_logger.bind(feature=feature).warning("sankhya_sync_event_subscriber_unsupported_feature")
                continue
            
            try:
                log = await sync_service.iniciar_sync_log(tenant_scope, feature, "import")
                
                if feature == "pessoas":
                    await pessoa_service.importar_pessoas(tenant_scope, log.id)
                elif feature == "produtos":
                    await produto_service.importar_produtos(tenant_scope, log.id)
                
                await sync_service.finalizar_sync_log(log.id, "COMPLETED")
                processed += 1
            except Exception as e:
                errors += 1
                bound_logger.bind(feature=feature, exception=str(e)).error("sankhya_sync_event_subscriber_feature_failed")
                if 'log' in locals():
                    await sync_service.finalizar_sync_log(log.id, "FAILED", str(e))

        status = "failed" if errors > 0 and processed == 0 else "success" if errors == 0 else "partial"

        result = self._to_result(event, started_at, status=status, processed=processed, errors=errors, warnings=warnings)
        bound_logger.bind(
            status=result.status,
            duration_ms=result.duration_ms,
            warnings=result.warnings,
            errors=result.errors,
        ).info("sankhya_sync_event_subscriber_finished")
        return result

    @staticmethod
    def _logger(event: DomainEvent):
        return logger.bind(
            component="sankhya_sync_event_subscriber",
            event_id=str(event.event_id),
            event_type=event.event_type,
            tenant_id=str(event.tenant_id),
            correlation_id=str(event.correlation_id) if event.correlation_id else None,
            causation_id=str(event.causation_id) if event.causation_id else None,
            config_id=event.metadata.get("config_id") or getattr(event, "config_id", None)
        )

    @staticmethod
    def _to_result(
        event: DomainEvent,
        started_at: datetime,
        status: str = "success",
        processed: int = 0,
        errors: int = 0,
        warnings: int = 0
    ) -> EventSubscriberResult:
        finished_at = datetime.now(timezone.utc)
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name="sankhya-sync",
            status=status,
            created=processed,
            updated=0,
            ignored=0,
            skipped=0 if processed > 0 else 1,
            warnings=warnings,
            errors=errors,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            metadata={"features_processed": processed},
        )
