from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from alert_engine import dispatcher as alert_dispatcher_module
from alert_engine.dispatcher import AlertDispatcherResult, AlertDomainEvent
from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRegistry,
    AlertGeneratorResult,
    AlertGeneratorRunner,
    BaseAlertGenerator,
)
from alert_engine.models import Category, Domain
from events import (
    DomainEvent,
    EventPublisher,
    EventPublisherResult,
    EventSubscriber,
    EventSubscriberRegistry,
    EventSubscriberResult,
    publish_domain_event,
)
from events import helpers as events_helpers_module
from events import publisher as events_publisher_module
from events import subscribers as events_subscribers_module
from events.subscribers import AlertEngineEventSubscriber


class SuccessSubscriber(EventSubscriber):
    subscriber_name = "success-subscriber"
    event_types = ("campo.tarefa.invalidada",)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status="success",
            metadata={"tenant_id": str(event.tenant_id)},
        )


class SecondarySubscriber(EventSubscriber):
    subscriber_name = "secondary-subscriber"
    event_types = ("campo.tarefa.invalidada",)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        return EventSubscriberResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subscriber_name=self.subscriber_name,
            status="success",
            warnings=1,
        )


class FailingSubscriber(EventSubscriber):
    subscriber_name = "failing-subscriber"
    event_types = ("campo.tarefa.invalidada",)

    async def handle(self, event: DomainEvent) -> EventSubscriberResult:
        raise RuntimeError(f"boom:{event.event_type}")


class ChainGenerator(BaseAlertGenerator):
    generator_name = "chain-generator"
    domain = Domain.FIELD
    category = Category.OPERACIONAL
    event_types = ("campo.tarefa.invalidada",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(created=1, generator_name=self.generator_name)


class RunnerSpy(AlertGeneratorRunner):
    def __init__(self) -> None:
        self.calls: list[tuple[str, AlertGeneratorContext]] = []

    async def execute(
        self,
        generator: BaseAlertGenerator,
        context: AlertGeneratorContext,
    ) -> AlertGeneratorResult:
        self.calls.append((generator.generator_name, context))
        return await super().execute(generator, context)


class LoggerSpy:
    def __init__(self) -> None:
        self.bind_calls: list[dict[str, object]] = []
        self.info_messages: list[str] = []
        self.exception_messages: list[str] = []

    def bind(self, **kwargs: object) -> LoggerSpy:
        self.bind_calls.append(kwargs)
        return self

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def exception(self, message: str) -> None:
        self.exception_messages.append(message)


def test_domain_event_defaults_and_extensibility() -> None:
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        extra_hint="future",
    )

    assert event.event_id is not None
    assert event.occurred_at.tzinfo is not None
    assert event.model_extra["extra_hint"] == "future"


def test_registry_registers_and_filters_by_event_type() -> None:
    registry = EventSubscriberRegistry()
    registry.register(SuccessSubscriber)
    registry.register(SecondarySubscriber)

    assert registry.find_by_event_type("campo.tarefa.invalidada") == (
        SuccessSubscriber,
        SecondarySubscriber,
    )
    assert registry.list_subscribers() == (SuccessSubscriber, SecondarySubscriber)


def test_registry_rejects_subscriber_without_events() -> None:
    class EmptySubscriber(EventSubscriber):
        async def handle(self, event: DomainEvent) -> EventSubscriberResult:
            return EventSubscriberResult(
                event_id=event.event_id,
                event_type=event.event_type,
                subscriber_name="empty",
                status="success",
            )

    with pytest.raises(ValueError):
        EventSubscriberRegistry().register(EmptySubscriber)


@pytest.mark.asyncio
async def test_publisher_handles_event_without_subscribers() -> None:
    publisher = EventPublisher(registry=EventSubscriberRegistry())
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await publisher.publish(event)

    assert isinstance(result, EventPublisherResult)
    assert result.total_subscribers == 0
    assert result.executed == 0
    assert result.failed == 0
    assert result.executions == []


@pytest.mark.asyncio
async def test_publisher_executes_single_subscriber(session) -> None:
    registry = EventSubscriberRegistry()
    registry.register(SuccessSubscriber)
    publisher = EventPublisher(session=session, registry=registry)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await publisher.publish(event)

    assert result.executed == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.executions[0].subscriber_name == "success-subscriber"


@pytest.mark.asyncio
async def test_publisher_executes_multiple_subscribers(session) -> None:
    registry = EventSubscriberRegistry()
    registry.register(SuccessSubscriber)
    registry.register(SecondarySubscriber)
    publisher = EventPublisher(session=session, registry=registry)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await publisher.publish(event)

    assert result.total_subscribers == 2
    assert result.executed == 2
    assert result.succeeded == 2
    assert result.failed == 0
    assert result.warnings == 1


@pytest.mark.asyncio
async def test_publisher_isolates_subscriber_failure(session) -> None:
    registry = EventSubscriberRegistry()
    registry.register(SuccessSubscriber)
    registry.register(FailingSubscriber)
    registry.register(SecondarySubscriber)
    publisher = EventPublisher(session=session, registry=registry)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await publisher.publish(event)

    assert result.executed == 3
    assert result.failed == 1
    assert [execution.status for execution in result.executions] == [
        "success",
        "failed",
        "success",
    ]


@pytest.mark.asyncio
async def test_alert_engine_subscriber_calls_dispatcher() -> None:
    captured: dict[str, object] = {}

    class DispatcherSpy:
        async def dispatch(self, event: AlertDomainEvent) -> AlertDispatcherResult:
            captured["event"] = event
            return AlertDispatcherResult(
                dispatch_id=uuid.uuid4(),
                event_id=event.event_id,
                alerts_created=1,
            )

    subscriber = AlertEngineEventSubscriber(dispatcher=cast(Any, DispatcherSpy()))
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="TarefaCampo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"origin": "unit-test"},
    )

    result = await subscriber.handle(event)
    dispatcher_event = captured["event"]

    assert result.status == "success"
    assert result.created == 1
    assert isinstance(dispatcher_event, AlertDomainEvent)
    assert dispatcher_event.tenant_id == event.tenant_id
    assert dispatcher_event.unidade_produtiva_id == event.unidade_produtiva_id
    assert dispatcher_event.correlation_id == event.correlation_id
    assert dispatcher_event.causation_id == event.causation_id
    assert dispatcher_event.metadata["origin"] == "unit-test"


@pytest.mark.asyncio
async def test_publish_domain_event_helper_uses_registry(session) -> None:
    registry = EventSubscriberRegistry()
    registry.register(SuccessSubscriber)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await publish_domain_event(event, session=session, registry=registry)

    assert result.executed == 1
    assert result.succeeded == 1
    assert result.event_id == event.event_id


@pytest.mark.asyncio
async def test_full_chain_publisher_to_dispatcher_runner_and_generator(
    session, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = AlertGeneratorRegistry()
    registry.register(ChainGenerator)
    runner = RunnerSpy()
    monkeypatch.setattr(alert_dispatcher_module, "alert_generator_registry", registry)
    monkeypatch.setattr(alert_dispatcher_module, "AlertGeneratorRunner", lambda: runner)

    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"origin": "unit-test"},
    )

    result = await publish_domain_event(event, session=session)

    assert result.executed == 1
    assert result.succeeded == 1
    assert result.errors == 0
    assert runner.calls[0][0] == "chain-generator"
    assert runner.calls[0][1].event_id == event.event_id
    assert runner.calls[0][1].metadata["origin"] == "unit-test"


@pytest.mark.asyncio
async def test_publish_domain_event_safe_swallows_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    logger_spy = LoggerSpy()
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"origin": "unit-test"},
    )
    monkeypatch.setattr(events_helpers_module, "logger", logger_spy)
    monkeypatch.setattr(
        events_helpers_module,
        "publish_domain_event",
        AsyncMock(side_effect=RuntimeError("publisher boom")),
    )

    result = await events_helpers_module.publish_domain_event_safe(event)

    assert result is None
    assert logger_spy.info_messages[0] == "domain_event_publish_started"
    assert logger_spy.exception_messages[-1] == "domain_event_publish_failed"
    assert logger_spy.bind_calls[0]["correlation_id"] == str(event.correlation_id)
    assert logger_spy.bind_calls[0]["causation_id"] == str(event.causation_id)


@pytest.mark.asyncio
async def test_publish_domain_event_safe_routes_to_outbox_without_forcing_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger_spy = LoggerSpy()
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
        metadata={"origin": "unit-test"},
    )
    enqueue_spy = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4(), idempotency_key="k"))
    monkeypatch.setattr(events_helpers_module, "logger", logger_spy)
    monkeypatch.setattr(events_helpers_module, "enqueue_domain_event", enqueue_spy)

    result = await events_helpers_module.publish_domain_event_safe(
        event,
        session=object(),
        commit=False,
    )

    assert result is not None
    enqueue_spy.assert_awaited_once()
    assert enqueue_spy.await_args is not None
    assert enqueue_spy.await_args.kwargs["commit"] is False
    assert logger_spy.exception_messages == []


@pytest.mark.asyncio
async def test_event_publisher_logs_canonical_context(monkeypatch: pytest.MonkeyPatch) -> None:
    logger_spy = LoggerSpy()
    registry = EventSubscriberRegistry()
    monkeypatch.setattr(events_publisher_module, "logger", logger_spy)
    publisher = EventPublisher(registry=registry)
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
    )

    await publisher.publish(event)

    assert logger_spy.info_messages[0] == "event_publisher_started"
    assert logger_spy.bind_calls[0]["correlation_id"] == str(event.correlation_id)
    assert logger_spy.bind_calls[0]["causation_id"] == str(event.causation_id)


@pytest.mark.asyncio
async def test_alert_engine_subscriber_logs_canonical_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger_spy = LoggerSpy()

    class DispatcherSpy:
        async def dispatch(self, event: AlertDomainEvent) -> AlertDispatcherResult:
            return AlertDispatcherResult(
                dispatch_id=uuid.uuid4(),
                event_id=event.event_id,
                alerts_created=1,
            )

    monkeypatch.setattr(events_subscribers_module, "logger", logger_spy)
    subscriber = AlertEngineEventSubscriber(dispatcher=cast(Any, DispatcherSpy()))
    event = DomainEvent(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        causation_id=uuid.uuid4(),
    )

    await subscriber.handle(event)

    assert logger_spy.info_messages[0] == "alert_engine_event_subscriber_started"
    assert logger_spy.bind_calls[0]["correlation_id"] == str(event.correlation_id)
    assert logger_spy.bind_calls[0]["causation_id"] == str(event.causation_id)
    assert logger_spy.exception_messages == []


def test_domain_services_do_not_import_dispatcher_internals() -> None:
    project_root = Path(__file__).resolve().parents[5]
    campo_source = (project_root / "services/api/campo/router.py").read_text(encoding="utf-8")
    pecuaria_router_source = (
        project_root / "services/api/pecuaria/routers/manejos.py"
    ).read_text(encoding="utf-8")
    pecuaria_service_source = (
        project_root / "services/api/pecuaria/services/manejo_sync_service.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "AlertDispatcherService",
        "dispatch_alert_event",
        "AlertGeneratorRegistry",
        "AlertGeneratorRunner",
        "CampoAlertGenerator",
        "PecuariaAlertGenerator",
    )
    allowed = (
        "DomainEvent",
        "publish_domain_event",
        "publish_domain_event_safe",
    )

    for source in (campo_source, pecuaria_router_source, pecuaria_service_source):
        assert any(token in source for token in allowed)
        assert all(token not in source for token in forbidden)
