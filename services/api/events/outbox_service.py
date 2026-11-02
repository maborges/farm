from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .base import DomainEvent
from .outbox_model import DomainEventOutbox, DomainEventOutboxStatus


class DomainEventOutboxService:
    """Service responsible for persisting and managing domain-event outbox rows."""

    max_attempts = 5

    def __init__(self, session: AsyncSession, tenant_id: UUID | None = None) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def enqueue(self, event: DomainEvent, commit: bool = True) -> DomainEventOutbox:
        """Persist a domain event in the outbox with stable idempotency."""

        self._ensure_tenant(event.tenant_id)
        await self._set_rls_context(event.tenant_id)
        idempotency_key = self._idempotency_key(event)
        existing = await self._find_by_idempotency_key(event.tenant_id, idempotency_key)
        if existing is not None:
            return existing

        outbox_row = DomainEventOutbox.from_domain_event(event, idempotency_key)
        try:
            async with self.session.begin_nested():
                self.session.add(outbox_row)
                await self.session.flush()
        except IntegrityError:
            logger.bind(
                component="domain_event_outbox_service",
                tenant_id=str(event.tenant_id),
                event_type=event.event_type,
                idempotency_key=idempotency_key,
            ).info("domain_event_outbox_duplicate_skipped")
            return await self._find_or_raise(event.tenant_id, idempotency_key)

        if commit:
            await self.session.commit()

        logger.bind(
            component="domain_event_outbox_service",
            outbox_id=str(outbox_row.id),
            tenant_id=str(outbox_row.tenant_id),
            event_type=outbox_row.event_type,
            idempotency_key=outbox_row.idempotency_key,
            status=outbox_row.status,
        ).info("domain_event_outbox_enqueued")
        return outbox_row

    async def list_pending(
        self,
        batch_size: int = 100,
        tenant_id: UUID | None = None,
        event_type: str | None = None,
    ) -> list[DomainEventOutbox]:
        """List outbox rows that are due for processing."""

        effective_tenant_id = self._effective_tenant_id(tenant_id)
        if effective_tenant_id is not None:
            await self._set_rls_context(effective_tenant_id)
        stmt = self._due_statement(
            batch_size=batch_size,
            tenant_id=effective_tenant_id,
            event_type=event_type,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if not rows and effective_tenant_id is None and not self._is_sqlite():
            for tid in await self._resolve_rls_tenant_ids():
                remaining = batch_size - len(rows)
                if remaining <= 0:
                    break
                await self._set_rls_context(tid)
                t_stmt = self._due_statement(
                    batch_size=remaining,
                    tenant_id=tid,
                    event_type=event_type,
                )
                rows.extend((await self.session.execute(t_stmt)).scalars().all())
        return rows

    async def claim_batch(
        self,
        batch_size: int = 50,
        tenant_id: UUID | None = None,
        relay_id: str | None = None,
        event_type: str | None = None,
    ) -> list[DomainEventOutbox]:
        """Claim a batch of due rows for processing."""

        effective_tenant_id = self._effective_tenant_id(tenant_id)
        if effective_tenant_id is not None:
            await self._set_rls_context(effective_tenant_id)
        stmt = self._due_statement(
            batch_size=batch_size,
            tenant_id=effective_tenant_id,
            event_type=event_type,
        )
        if self._supports_skip_locked():
            stmt = stmt.with_for_update(skip_locked=True)
        rows = list((await self.session.execute(stmt)).scalars().all())
        if not rows and effective_tenant_id is None and not self._is_sqlite():
            now = datetime.now(timezone.utc)  # noqa: UP017
            claimed_rows: list[DomainEventOutbox] = []
            for tid in await self._resolve_rls_tenant_ids():
                remaining = batch_size - len(claimed_rows)
                if remaining <= 0:
                    break
                await self._set_rls_context(tid)
                t_stmt = self._due_statement(
                    batch_size=remaining,
                    tenant_id=tid,
                    event_type=event_type,
                )
                if self._supports_skip_locked():
                    t_stmt = t_stmt.with_for_update(skip_locked=True)
                t_rows = list((await self.session.execute(t_stmt)).scalars().all())
                if not t_rows:
                    continue
                for row in t_rows:
                    row.status = DomainEventOutboxStatus.PROCESSING.value
                    row.attempts += 1
                    row.locked_at = now
                    row.locked_by = relay_id or "domain-event-outbox-relay"
                await self.session.flush()
                claimed_rows.extend(t_rows)
            return claimed_rows

        now = datetime.now(timezone.utc)  # noqa: UP017
        for row in rows:
            row.status = DomainEventOutboxStatus.PROCESSING.value
            row.attempts += 1
            row.locked_at = now
            row.locked_by = relay_id or "domain-event-outbox-relay"
        await self.session.flush()
        return rows

    async def mark_processed(self, row: DomainEventOutbox) -> DomainEventOutbox:
        """Mark an outbox row as processed."""

        if getattr(row, "tenant_id", None) is not None:
            await self._set_rls_context(row.tenant_id)
        now = datetime.now(timezone.utc)  # noqa: UP017
        row.status = DomainEventOutboxStatus.PROCESSED.value
        row.processed_at = now
        row.failed_at = None
        row.last_error = None
        row.next_attempt_at = now
        row.locked_at = None
        row.locked_by = None
        await self.session.flush()
        return row

    async def mark_failed(
        self, row: DomainEventOutbox, error: Exception | str
    ) -> DomainEventOutbox:
        """Mark an outbox row as failed or dead letter after retries."""

        if getattr(row, "tenant_id", None) is not None:
            await self._set_rls_context(row.tenant_id)
        now = datetime.now(timezone.utc)  # noqa: UP017
        row.failed_at = now
        row.last_error = self._error_message(error)
        row.locked_at = None
        row.locked_by = None
        if row.attempts >= self.max_attempts:
            row.status = DomainEventOutboxStatus.DEAD_LETTER.value
            row.next_attempt_at = now
        else:
            row.status = DomainEventOutboxStatus.FAILED.value
            row.next_attempt_at = now + self._backoff_delay(row.attempts)
        await self.session.flush()
        return row

    @staticmethod
    def rebuild_domain_event(row: DomainEventOutbox) -> DomainEvent:
        """Rebuild a canonical domain event from the persisted payload."""

        return row.to_domain_event()

    def _due_statement(
        self,
        *,
        batch_size: int,
        tenant_id: UUID | None,
        event_type: str | None = None,
    ) -> Any:
        stmt = select(DomainEventOutbox).where(
            DomainEventOutbox.status.in_(
                (
                    DomainEventOutboxStatus.PENDING.value,
                    DomainEventOutboxStatus.FAILED.value,
                )
            ),
            DomainEventOutbox.next_attempt_at <= datetime.now(timezone.utc),  # noqa: UP017
        )
        if tenant_id is not None:
            stmt = stmt.where(DomainEventOutbox.tenant_id == tenant_id)
        if event_type is not None:
            stmt = stmt.where(DomainEventOutbox.event_type == event_type)
        return stmt.order_by(
            DomainEventOutbox.next_attempt_at.asc(), DomainEventOutbox.created_at.asc()
        ).limit(batch_size)

    async def _find_by_idempotency_key(
        self,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> DomainEventOutbox | None:
        stmt = select(DomainEventOutbox).where(
            DomainEventOutbox.tenant_id == tenant_id,
            DomainEventOutbox.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        return cast(DomainEventOutbox | None, result.scalars().first())

    async def _find_or_raise(self, tenant_id: UUID, idempotency_key: str) -> DomainEventOutbox:
        row = await self._find_by_idempotency_key(tenant_id, idempotency_key)
        if row is None:
            raise LookupError("Outbox row not found after duplicate insert")
        return row

    def _effective_tenant_id(self, tenant_id: UUID | None) -> UUID | None:
        if tenant_id is not None:
            return tenant_id
        return self.tenant_id

    def _ensure_tenant(self, tenant_id: UUID) -> None:
        if self.tenant_id is not None and self.tenant_id != tenant_id:
            raise ValueError("tenant mismatch for outbox service")

    async def _set_rls_context(self, tenant_id: UUID) -> None:
        if hasattr(self.session, "info") and isinstance(self.session.info, dict):
            self.session.info["tenant_id"] = tenant_id
        if self._is_sqlite():
            return
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

    async def _resolve_rls_tenant_ids(self) -> list[UUID]:
        if self._is_sqlite() or not hasattr(self.session, "execute"):
            return []
        from core.models.tenant import Tenant

        try:
            result = await self.session.execute(
                select(Tenant.id).where(Tenant.ativo.is_(True))
            )
            scalars = getattr(result, "scalars", None)
            if not callable(scalars):
                return []
            return [tid for tid in scalars().all() if isinstance(tid, UUID)]
        except Exception:
            return []

    def _idempotency_key(self, event: DomainEvent) -> str:
        namespace = self._namespace_for_event(event)
        source_id = str(event.entity_id or event.event_id)
        suffix = event.event_type.split(".", 1)[1] if "." in event.event_type else event.event_type
        return f"{namespace}:{suffix}:{source_id}"

    @staticmethod
    def _namespace_for_event(event: DomainEvent) -> str:
        origin = str(event.metadata.get("origin") or "").strip().lower()
        if origin == "processar_tarefa_campo" or event.event_type.startswith("pecuaria."):
            return "pecuaria"
        if origin == "sync_push" or event.event_type.startswith("campo."):
            return "campo"
        domain_value = getattr(event.domain, "value", event.domain)
        return str(domain_value).lower()

    @staticmethod
    def _backoff_delay(attempts: int) -> timedelta:
        return timedelta(minutes=2 ** max(attempts - 1, 0))

    @staticmethod
    def _error_message(error: Exception | str) -> str:
        if isinstance(error, Exception):
            return f"{error.__class__.__name__}: {error}"
        return error

    def _supports_skip_locked(self) -> bool:
        bind = self.session.get_bind()
        dialect = getattr(bind, "dialect", None)
        return getattr(dialect, "name", "") != "sqlite"

    def _is_sqlite(self) -> bool:
        bind = self.session.get_bind()
        dialect = getattr(bind, "dialect", None)
        return getattr(dialect, "name", "") == "sqlite"
