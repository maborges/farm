from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from alert_engine.models import Domain
from campo.models import TarefaCampo
from events import DomainEvent, DomainEventOutboxRelay, DomainEventOutboxService
from events.outbox_model import DomainEventOutboxStatus
from events.registry import EventSubscriberRegistry
from recommendations.engine import RecommendationEngineExecution, RecommendationEngineResult
from recommendations.event_mapper import RecommendationEventMapper
from recommendations.event_subscriber import RecommendationEventSubscriber
from recommendations.models import RecommendationResult


def _event(tenant_id: uuid.UUID, task_id: uuid.UUID, unit_id: uuid.UUID) -> DomainEvent:
    return DomainEvent(
        tenant_id=tenant_id,
        unidade_produtiva_id=unit_id,
        domain=Domain.FIELD,
        event_type="campo.sync.falha",
        source_type="CAMPO_SYNC_FALHA",
        entity_type="sync_campo",
        entity_id=task_id,
        metadata={"origin": "sync_push", "status": "ERROR"},
    )


def test_mapper_builds_signal_and_context_from_eligible_event() -> None:
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    mapping = RecommendationEventMapper().map(event)

    assert mapping is not None
    assert mapping.signal.signal_id == event.event_id
    assert mapping.signal.payload["source_event_id"] == str(event.event_id)
    assert mapping.context.scope_id == str(event.entity_id)
    assert mapping.context.source_signal_ids == [event.event_id]
    assert mapping.provider_names == ("campo",)


def test_mapper_ignores_event_without_recommendation_mapping() -> None:
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    event.event_type = "campo.tarefa.invalidada"

    assert RecommendationEventMapper().map(event) is None


def test_mapper_rejects_eligible_event_without_entity_scope() -> None:
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    event.entity_id = None

    with pytest.raises(ValueError, match="entity scope"):
        RecommendationEventMapper().map(event)


def test_mapper_rejects_eligible_event_without_tenant() -> None:
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    event.tenant_id = None

    with pytest.raises(ValueError, match="tenant_id"):
        RecommendationEventMapper().map(event)


class _SessionSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []

    async def execute(self, statement, params=None):
        self.calls.append((statement, params))


class _EngineSpy:
    def __init__(self, session, tenant_id, registry=None) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.registry = registry

    async def generate(self, context, signals, provider_names=None):
        assert self.session.calls
        assert signals[0].signal_id == context.source_signal_ids[0]
        return RecommendationEngineResult(
            run_id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            recommendations_created=1,
            executions=[RecommendationEngineExecution(provider_name="campo", status="success")],
        )


@pytest.mark.asyncio
async def test_subscriber_applies_rls_and_uses_engine() -> None:
    session = _SessionSpy()
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    subscriber = RecommendationEventSubscriber(session=session, engine_factory=_EngineSpy)
    result = await subscriber.handle(event)

    assert result.status == "processed"
    assert result.created == 1
    assert result.metadata["providers_evaluated"] == ["campo"]
    assert session.calls[0][1] == {"tenant_id": str(event.tenant_id)}


@pytest.mark.asyncio
async def test_subscriber_rejects_invalid_contract_without_engine() -> None:
    session = _SessionSpy()
    event = _event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    event.entity_type = None

    subscriber = RecommendationEventSubscriber(session=session, engine_factory=_EngineSpy)
    result = await subscriber.handle(event)

    assert result.status == "rejected"
    assert result.ignored == 1
    assert result.errors == 0
    assert session.calls == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_outbox_relay_processes_sync_failure_without_duplicate_recommendation(
    session,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    task_id = uuid.uuid4()
    await _ensure_tenant(session, tenant_id)
    await _set_tenant(session, tenant_id)
    await _ensure_unit(session, tenant_id, unit_id)
    session.add(
        TarefaCampo(
            id=task_id,
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            origem="MANUAL",
            status_execucao="CONCLUIDA",
            prioridade="NORMAL",
            type="VACINACAO",
            module="pecuaria",
            unidade_produtiva_id=unit_id,
            status="CONCLUIDA",
            dados={"sync_pecuaria": {"status": "ERROR", "erros": ["falha"]}},
            fotos=[],
        )
    )
    event = _event(tenant_id, task_id, unit_id)
    outbox = await DomainEventOutboxService(session).enqueue(event, commit=False)
    await session.commit()

    registry = EventSubscriberRegistry()
    registry.register(RecommendationEventSubscriber)
    relay = DomainEventOutboxRelay(session=session, registry=registry)
    first = await relay.run_once(tenant_id=tenant_id)
    assert first.processed == 1

    await _set_tenant(session, tenant_id)
    first_results = await _recommendations_for_event(session, tenant_id, event.event_id)
    assert len(first_results) == 1
    assert first_results[0].status == "CREATED"
    assert first_results[0].tenant_id == tenant_id

    outbox.status = DomainEventOutboxStatus.PENDING.value
    outbox.next_attempt_at = datetime.now(timezone.utc)  # noqa: UP017
    await session.commit()
    second = await relay.run_once(tenant_id=tenant_id)
    assert second.processed == 1

    await _set_tenant(session, tenant_id)
    assert len(await _recommendations_for_event(session, tenant_id, event.event_id)) == 1


async def _ensure_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
            "storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Recommendation Event", "documento": tenant_id.hex[:11]},
    )
    await session.commit()


async def _set_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def _ensure_unit(session, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(unit_id), "tenant_id": str(tenant_id), "nome": "Unidade Event"},
    )


async def _recommendations_for_event(session, tenant_id: uuid.UUID, event_id: uuid.UUID):
    result = await session.execute(
        select(RecommendationResult).where(RecommendationResult.tenant_id == tenant_id)
    )
    return [
        recommendation
        for recommendation in result.scalars().all()
        if str(event_id) in recommendation.source_signal_ids
    ]
