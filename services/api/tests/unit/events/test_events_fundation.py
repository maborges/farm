from __future__ import annotations

import uuid

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

    subscriber = AlertEngineEventSubscriber(dispatcher=DispatcherSpy())
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
