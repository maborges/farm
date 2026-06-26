from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from alert_engine.dispatcher import (
    AlertDispatcherService,
    AlertDomainEvent,
    dispatch_alert_event,
)
from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRegistry,
    AlertGeneratorResult,
    AlertGeneratorRunner,
    BaseAlertGenerator,
    alert_generator_registry,
)
from alert_engine.models import Category, Domain, OperationalAlert
from campo.models import TarefaCampo
from core.models.tenant import Tenant

ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _seed_tenant(session, tenant_id: uuid.UUID) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            nome=f"Tenant {tenant_id.hex[:8]}",
            documento=tenant_id.hex[:11],
            ativo=True,
        )
    )
    await session.commit()


async def _seed_invalidated_task(session, tenant_id: uuid.UUID) -> TarefaCampo:
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=None,
        user_id=ADMIN_USER_ID,
        operador_id=None,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao="INVALIDADA",
        titulo="Tarefa inválida",
        data_programada=date.today() - timedelta(days=1),
        prioridade="NORMAL",
        type="VACINACAO",
        module="pecuaria",
        unidade_produtiva_id=None,
        area_rural_id=None,
        lote_id=None,
        status="INVALIDADA",
        dados={"motivo": "dados inconsistentes"},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        latitude=None,
        longitude=None,
        iniciada_em=None,
        concluida_em=None,
        invalidado_em=datetime.utcnow(),
        invalidado_por=ADMIN_USER_ID,
        motivo_invalidacao="dados inconsistentes",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()
    return task


async def _count_alerts(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(OperationalAlert.id)).where(OperationalAlert.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


class FieldDispatchGenerator(BaseAlertGenerator):
    generator_name = "field-dispatch"
    domain = Domain.FIELD
    category = Category.OPERACIONAL
    event_types = ("campo.tarefa.invalidada",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(
            created=1,
            generator_name=self.generator_name,
            metadata={
                "event_id": str(context.event_id),
                "scope": context.scope,
                "reason": context.reason,
            },
        )


class SecondaryFieldDispatchGenerator(BaseAlertGenerator):
    generator_name = "field-dispatch-secondary"
    domain = Domain.FIELD
    category = Category.OPERACIONAL
    event_types = ("campo.tarefa.invalidada",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(created=2, ignored=1, generator_name=self.generator_name)


class FailingFieldDispatchGenerator(BaseAlertGenerator):
    generator_name = "field-dispatch-failing"
    domain = Domain.FIELD
    category = Category.OPERACIONAL
    event_types = ("campo.tarefa.invalidada",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        raise RuntimeError(f"boom:{context.event_id}")


class PecuariaDispatchGenerator(BaseAlertGenerator):
    generator_name = "pecuaria-dispatch"
    domain = Domain.LIVESTOCK
    category = Category.PRODUCAO
    event_types = ("pecuaria.vacinacao.registrada",)

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(created=1, generator_name=self.generator_name)


class SpyRunner(AlertGeneratorRunner):
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


def _registry(*generator_classes: type[BaseAlertGenerator]) -> AlertGeneratorRegistry:
    registry = AlertGeneratorRegistry()
    for generator_cls in generator_classes:
        registry.register(generator_cls)
    return registry


def test_alert_domain_event_can_be_created_with_defaults() -> None:
    event = AlertDomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    assert event.event_id is not None
    assert event.occurred_at.tzinfo is not None
    assert event.metadata == {}


def test_dispatcher_uses_default_registry_and_runner(session) -> None:
    service = AlertDispatcherService(session)

    assert isinstance(service.runner, AlertGeneratorRunner)
    assert service.registry is alert_generator_registry
    assert {
        cls.generator_name for cls in service.registry.find_by_event_type("campo.tarefa.invalidada")
    } >= {"campo"}


@pytest.mark.asyncio
async def test_dispatcher_logs_canonical_context(monkeypatch: pytest.MonkeyPatch, session) -> None:
    logger_spy = LoggerSpy()
    monkeypatch.setattr("alert_engine.dispatcher.logger", logger_spy)
    service = AlertDispatcherService(session, registry=_registry())
    event = AlertDomainEvent(
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

    await service.dispatch(event)

    assert logger_spy.info_messages[0] == "alert_dispatcher_started"
    assert logger_spy.bind_calls[0]["correlation_id"] == str(event.correlation_id)
    assert logger_spy.bind_calls[0]["causation_id"] == str(event.causation_id)


@pytest.mark.asyncio
async def test_dispatcher_routes_event_and_uses_runner(session) -> None:
    tenant_id = uuid.uuid4()
    registry = _registry(FieldDispatchGenerator, PecuariaDispatchGenerator)
    runner = SpyRunner()
    service = AlertDispatcherService(session, registry=registry, runner=runner)
    event = AlertDomainEvent(
        tenant_id=tenant_id,
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="TarefaCampo",
    )

    result = await service.dispatch(event)

    assert result.generators_executed == 1
    assert result.alerts_created == 1
    assert result.errors == 0
    assert runner.calls[0][0] == "field-dispatch"
    assert runner.calls[0][1].event_id == event.event_id
    assert runner.calls[0][1].scope == "event"
    assert runner.calls[0][1].reason == "event_dispatch"
    assert runner.calls[0][1].metadata["dispatch_id"] == str(result.dispatch_id)


@pytest.mark.asyncio
async def test_dispatcher_isolates_failures_and_continues(session) -> None:
    registry = _registry(
        FieldDispatchGenerator,
        FailingFieldDispatchGenerator,
        SecondaryFieldDispatchGenerator,
    )
    runner = SpyRunner()
    service = AlertDispatcherService(session, registry=registry, runner=runner)
    event = AlertDomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await service.dispatch(event)

    assert result.generators_executed == 3
    assert result.errors == 1
    assert [execution.status for execution in result.executions] == [
        "success",
        "failed",
        "success",
    ]
    assert len(runner.calls) == 3


@pytest.mark.asyncio
async def test_dispatcher_handles_event_without_generators(session) -> None:
    service = AlertDispatcherService(session, registry=_registry())
    event = AlertDomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await service.dispatch(event)

    assert result.generators_executed == 0
    assert result.errors == 0
    assert result.executions == []


@pytest.mark.asyncio
async def test_dispatcher_consolidates_multiple_generators(session) -> None:
    registry = _registry(FieldDispatchGenerator, SecondaryFieldDispatchGenerator)
    runner = SpyRunner()
    service = AlertDispatcherService(session, registry=registry, runner=runner)
    event = AlertDomainEvent(
        tenant_id=uuid.uuid4(),
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
    )

    result = await service.dispatch(event)

    assert result.generators_executed == 2
    assert result.alerts_created == 3
    assert result.alerts_updated == 0
    assert result.alerts_ignored == 1
    assert len(result.executions) == 2


@pytest.mark.asyncio
async def test_dispatcher_preserves_idempotency(session) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    task = await _seed_invalidated_task(session, tenant_id)
    event = AlertDomainEvent(
        tenant_id=tenant_id,
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="TarefaCampo",
        entity_id=task.id,
    )

    first = await dispatch_alert_event(session, event)
    second = await dispatch_alert_event(session, event)

    assert first.alerts_created == 1
    assert second.alerts_updated == 1
    assert await _count_alerts(session, tenant_id) == 1
