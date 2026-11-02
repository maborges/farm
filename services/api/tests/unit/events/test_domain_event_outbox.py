from __future__ import annotations

# mypy: disable-error-code=untyped-decorator
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

import events.helpers as events_helpers_module
import events.outbox_relay as outbox_relay_module
from alert_engine.models import Domain
from events import (
    DomainEvent,
    DomainEventOutbox,
    DomainEventOutboxRelay,
    DomainEventOutboxService,
    DomainEventOutboxStatus,
)


class _FakeDialect:
    name = "sqlite"


class _FakeBind:
    dialect = _FakeDialect()


class _FakeScalarResult:
    def __init__(self, rows: list[DomainEventOutbox]) -> None:
        self._rows = rows

    def all(self) -> list[DomainEventOutbox]:
        return list(self._rows)

    def first(self) -> DomainEventOutbox | None:
        return self._rows[0] if self._rows else None


class _FakeQueryResult:
    def __init__(self, rows: list[DomainEventOutbox]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)


class _FakeTxn:
    async def __aenter__(self) -> _FakeTxn:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _FakeOutboxSession:
    def __init__(self) -> None:
        self.rows: list[DomainEventOutbox] = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def begin_nested(self) -> _FakeTxn:
        return _FakeTxn()

    def add(self, row: DomainEventOutbox) -> None:
        if row not in self.rows:
            self.rows.append(row)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    def get_bind(self) -> _FakeBind:
        return _FakeBind()

    async def execute(self, statement: Any) -> _FakeQueryResult:
        if isinstance(statement, tuple) and statement and statement[0] == "due":
            _, batch_size, tenant_id, event_type = statement
            rows = [
                row
                for row in self.rows
                if row.status in (
                    DomainEventOutboxStatus.PENDING.value,
                    DomainEventOutboxStatus.FAILED.value,
                )
                and row.next_attempt_at <= datetime.now(timezone.utc)  # noqa: UP017
                and (tenant_id is None or row.tenant_id == tenant_id)
                and (event_type is None or row.event_type == event_type)
            ]
            rows.sort(key=lambda row: (row.next_attempt_at, row.created_at))
            return _FakeQueryResult(rows[:batch_size])
        return _FakeQueryResult([])


def _event(tenant_id: UUID, event_type: str, source_type: str, entity_id: UUID) -> DomainEvent:
    return DomainEvent(
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD if event_type.startswith("campo.") else Domain.LIVESTOCK,
        event_type=event_type,
        source_type=source_type,
        entity_type="tarefa_campo",
        entity_id=entity_id,
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"origin": "sync_push"},
    )


def _service_and_store() -> tuple[DomainEventOutboxService, _FakeOutboxSession]:
    session = _FakeOutboxSession()
    service = DomainEventOutboxService(session=session)

    def _due_statement(
        *,
        batch_size: int,
        tenant_id: UUID | None,
        event_type: str | None = None,
    ) -> tuple[str, int, UUID | None, str | None]:
        return ("due", batch_size, tenant_id, event_type)

    service._due_statement = _due_statement  # type: ignore[method-assign]
    return service, session


@pytest.mark.asyncio
async def test_enqueue_persists_and_dedupes(tenant_id: UUID) -> None:
    service, store = _service_and_store()
    event = _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())

    async def _find_by_idempotency_key(
        tenant_id: UUID,
        idempotency_key: str,
    ) -> DomainEventOutbox | None:
        return next(
            (
                row
                for row in store.rows
                if row.tenant_id == tenant_id and row.idempotency_key == idempotency_key
            ),
            None,
        )

    service._find_by_idempotency_key = _find_by_idempotency_key  # type: ignore[method-assign]

    first = await service.enqueue(event)
    second = await service.enqueue(event)

    assert first.id == second.id
    assert first.idempotency_key == "campo:tarefa.invalidada:" + str(event.entity_id)
    assert len(store.rows) == 1


@pytest.mark.asyncio
async def test_idempotency_key_distinguishes_pecuaria_sync_failure_origin(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    event = _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    event.metadata["origin"] = "processar_tarefa_campo"

    row = await service.enqueue(event)

    assert row.idempotency_key == "pecuaria:sync.falha:" + str(event.entity_id)


@pytest.mark.asyncio
async def test_outbox_round_trip_rebuilds_domain_event(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    event = _event(
        tenant_id,
        "pecuaria.vacinacao.registrada",
        "PECUARIA_VACINACAO_REGISTRADA",
        uuid.uuid4(),
    )

    row = await service.enqueue(event)
    rebuilt = row.to_domain_event()

    assert rebuilt.event_id == event.event_id
    assert rebuilt.tenant_id == event.tenant_id
    assert rebuilt.correlation_id == event.correlation_id
    assert rebuilt.metadata["origin"] == "sync_push"


@pytest.mark.asyncio
async def test_claim_batch_marks_processing_and_increments_attempts(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    event = _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    await service.enqueue(event)

    claimed = await service.claim_batch(batch_size=1, tenant_id=tenant_id, relay_id="relay-a")

    assert len(claimed) == 1
    assert claimed[0].status == DomainEventOutboxStatus.PROCESSING.value
    assert claimed[0].attempts == 1
    assert claimed[0].locked_by == "relay-a"


@pytest.mark.asyncio
async def test_failed_row_updates_retry_window(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    event = _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    await service.enqueue(event)
    claimed = await service.claim_batch(batch_size=1, tenant_id=tenant_id)

    failed = await service.mark_failed(claimed[0], RuntimeError("boom"))

    assert failed.status == DomainEventOutboxStatus.FAILED.value
    assert failed.attempts == 1
    assert failed.next_attempt_at > datetime.now(timezone.utc)  # noqa: UP017
    assert "RuntimeError" in (failed.last_error or "")


@pytest.mark.asyncio
async def test_dead_letter_after_excess_attempts(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    event = _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    service.max_attempts = 1
    await service.enqueue(event)
    claimed = await service.claim_batch(batch_size=1, tenant_id=tenant_id)

    dead_letter = await service.mark_failed(claimed[0], RuntimeError("boom"))

    assert dead_letter.status == DomainEventOutboxStatus.DEAD_LETTER.value
    assert dead_letter.failed_at is not None


@pytest.mark.asyncio
async def test_publish_domain_event_safe_uses_outbox_when_session_present(
    tenant_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = _service_and_store()
    event = _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    publish_spy = AsyncMock()
    monkeypatch.setattr(events_helpers_module, "publish_domain_event", publish_spy)
    monkeypatch.setattr(events_helpers_module, "DomainEventOutboxService", lambda session: service)

    outbox_row = await events_helpers_module.publish_domain_event_safe(
        event,
        session=service.session,
    )

    assert outbox_row is not None
    assert outbox_row.status == DomainEventOutboxStatus.PENDING.value
    publish_spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_calls_event_publisher_and_marks_processed(
    tenant_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, store = _service_and_store()
    event = _event(
        tenant_id,
        "pecuaria.planejamento.sanitario.atualizado",
        "PECUARIA_PLANEJAMENTO_SANITARIO_ATUALIZADO",
        uuid.uuid4(),
    )
    await service.enqueue(event)

    publisher_spy = AsyncMock(
        return_value=SimpleNamespace(errors=0, warnings=0, executions=[], total_subscribers=1)
    )
    monkeypatch.setattr(outbox_relay_module, "publish_domain_event", publisher_spy)
    relay = DomainEventOutboxRelay(session=service.session, service=service)

    result = await relay.run_once(batch_size=10, tenant_id=tenant_id)

    assert result.total_claimed == 1
    assert result.processed == 1
    assert publisher_spy.await_count == 1
    assert store.rows[0].status == DomainEventOutboxStatus.PROCESSED.value


@pytest.mark.asyncio
async def test_relay_marks_failed_and_requeues(
    tenant_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, store = _service_and_store()
    event = _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    await service.enqueue(event)

    monkeypatch.setattr(
        outbox_relay_module,
        "publish_domain_event",
        AsyncMock(side_effect=RuntimeError("publisher boom")),
    )
    relay = DomainEventOutboxRelay(session=service.session, service=service)

    result = await relay.run_once(batch_size=10, tenant_id=tenant_id)

    assert result.failed == 1
    assert store.rows[0].status == DomainEventOutboxStatus.FAILED.value
    assert store.rows[0].attempts == 1
    assert store.rows[0].next_attempt_at > datetime.now(timezone.utc)  # noqa: UP017


@pytest.mark.asyncio
async def test_relay_moves_to_dead_letter_after_max_attempts(
    tenant_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, store = _service_and_store()
    event = _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    service.max_attempts = 1
    await service.enqueue(event)
    monkeypatch.setattr(
        outbox_relay_module,
        "publish_domain_event",
        AsyncMock(side_effect=RuntimeError("publisher boom")),
    )
    relay = DomainEventOutboxRelay(session=service.session, service=service)

    result = await relay.run_once(batch_size=10, tenant_id=tenant_id)

    assert result.dead_letter == 1
    assert store.rows[0].status == DomainEventOutboxStatus.DEAD_LETTER.value


@pytest.mark.asyncio
async def test_list_pending_respects_tenant_isolation(
    tenant_id: UUID,
    outro_tenant_id: UUID,
) -> None:
    service, _ = _service_and_store()
    await service.enqueue(
        _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    )
    await service.enqueue(
        _event(outro_tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    )

    tenant_rows = await service.list_pending(tenant_id=tenant_id)
    other_rows = await service.list_pending(tenant_id=outro_tenant_id)

    assert len(tenant_rows) == 1
    assert len(other_rows) == 1
    assert tenant_rows[0].tenant_id == tenant_id
    assert other_rows[0].tenant_id == outro_tenant_id


@pytest.mark.asyncio
async def test_list_pending_can_filter_by_event_type(tenant_id: UUID) -> None:
    service, _ = _service_and_store()
    await service.enqueue(
        _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    )
    await service.enqueue(
        _event(tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    )

    rows = await service.list_pending(tenant_id=tenant_id, event_type="campo.sync.falha")

    assert len(rows) == 1
    assert rows[0].event_type == "campo.sync.falha"


@pytest.mark.asyncio
async def test_claim_batch_without_tenant_iterates_active_tenants_under_rls(
    tenant_id: UUID,
    outro_tenant_id: UUID,
) -> None:
    service, store = _service_and_store()
    await service.enqueue(
        _event(tenant_id, "campo.tarefa.invalidada", "CAMPO_TAREFA_INVALIDADA", uuid.uuid4())
    )
    await service.enqueue(
        _event(outro_tenant_id, "campo.sync.falha", "CAMPO_SYNC_FALHA", uuid.uuid4())
    )

    # Simulate PostgreSQL RLS where unscoped query (tenant_id=None) returns 0 rows
    orig_execute = store.execute

    async def rls_execute(statement: Any, params: Any = None) -> _FakeQueryResult:
        if isinstance(statement, tuple) and statement and statement[0] == "due":
            _, batch_size, tid, event_type = statement
            if tid is None:
                return _FakeQueryResult([])
        return await orig_execute(statement)

    store.execute = rls_execute  # type: ignore[method-assign]
    service._is_sqlite = lambda: False  # type: ignore[method-assign]
    service._resolve_rls_tenant_ids = AsyncMock(return_value=[tenant_id, outro_tenant_id])  # type: ignore[method-assign]

    claimed = await service.claim_batch(batch_size=10, tenant_id=None)

    assert len(claimed) == 2
    assert {r.tenant_id for r in claimed} == {tenant_id, outro_tenant_id}

