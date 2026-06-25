from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRegistry,
    AlertGeneratorResult,
    AlertGeneratorRunner,
    BaseAlertGenerator,
    alert_generator_registry,
)
from alert_engine.models import Category, Domain, OperationalAlert
from alert_engine.scheduler import AlertSchedulerService, run_scheduled_alerts
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


async def _seed_task(session, tenant_id: uuid.UUID) -> TarefaCampo:
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=None,
        user_id=ADMIN_USER_ID,
        operador_id=None,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao="PENDENTE",
        titulo="Tarefa de Campo",
        data_programada=date.today() - timedelta(days=1),
        prioridade="NORMAL",
        type="VACINACAO",
        module="pecuaria",
        unidade_produtiva_id=None,
        area_rural_id=None,
        lote_id=None,
        status="PENDENTE",
        dados={},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        latitude=None,
        longitude=None,
        iniciada_em=None,
        concluida_em=None,
        invalidado_em=None,
        invalidado_por=None,
        motivo_invalidacao=None,
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()
    return task


class FieldScheduledGenerator(BaseAlertGenerator):
    generator_name = "field-scheduled"
    domain = Domain.FIELD
    category = Category.OPERACIONAL

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(
            created=2,
            updated=1,
            warnings=1,
            metadata={"unit": str(context.unidade_produtiva_id)},
        )


class PecuariaScheduledGenerator(BaseAlertGenerator):
    generator_name = "pecuaria-scheduled"
    domain = Domain.LIVESTOCK
    category = Category.PRODUCAO

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(created=3, ignored=1, skipped=2)


class FailingScheduledGenerator(BaseAlertGenerator):
    generator_name = "failing-scheduled"
    domain = Domain.FIELD
    category = Category.OPERACIONAL

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        raise RuntimeError(f"boom:{context.scope}")


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


def _registry(*generator_classes: type[BaseAlertGenerator]) -> AlertGeneratorRegistry:
    registry = AlertGeneratorRegistry()
    for generator_cls in generator_classes:
        registry.register(generator_cls)
    return registry


def test_scheduler_uses_default_registry_and_runner(session) -> None:
    service = AlertSchedulerService(session)

    assert isinstance(service.runner, AlertGeneratorRunner)
    assert service.registry is alert_generator_registry
    assert {cls.generator_name for cls in service.registry.find_scheduled_generators()} >= {
        "campo",
        "pecuaria",
    }


@pytest.mark.asyncio
async def test_scheduler_executes_by_tenant_and_domain_filter(session) -> None:
    tenant_id = uuid.uuid4()
    registry = _registry(FieldScheduledGenerator, PecuariaScheduledGenerator)
    runner = SpyRunner()
    service = AlertSchedulerService(session, registry=registry, runner=runner)

    result = await service.run_scheduled_alerts(tenant_id=tenant_id, domains=["FIELD"])

    assert result.generators_executed == 1
    assert result.alerts_created == 2
    assert result.alerts_updated == 1
    assert result.warnings == 1
    assert result.errors == 0
    assert runner.calls[0][0] == "field-scheduled"
    assert runner.calls[0][1].tenant_id == tenant_id
    assert runner.calls[0][1].reason == "scheduled"
    assert runner.calls[0][1].dry_run is False
    assert runner.calls[0][1].metadata["scheduler_run_id"] == str(result.scheduler_run_id)


@pytest.mark.asyncio
async def test_scheduler_filters_by_unit_produtiva(session) -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    registry = _registry(FieldScheduledGenerator)
    runner = SpyRunner()
    service = AlertSchedulerService(session, registry=registry, runner=runner)

    result = await service.run_scheduled_alerts(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )

    assert result.generators_executed == 1
    assert runner.calls[0][1].unidade_produtiva_id == unidade_produtiva_id
    assert runner.calls[0][1].metadata["execution_modes"] == ["scheduled", "hybrid"]


@pytest.mark.asyncio
async def test_scheduler_consolidates_results(session) -> None:
    tenant_id = uuid.uuid4()
    registry = _registry(FieldScheduledGenerator, PecuariaScheduledGenerator)
    runner = SpyRunner()
    service = AlertSchedulerService(session, registry=registry, runner=runner)

    result = await service.run_scheduled_alerts(tenant_id=tenant_id)

    assert result.generators_executed == 2
    assert result.alerts_created == 5
    assert result.alerts_updated == 1
    assert result.alerts_ignored == 1
    assert result.alerts_skipped == 2
    assert result.warnings == 1
    assert result.errors == 0
    assert len(result.executions) == 2


@pytest.mark.asyncio
async def test_scheduler_isolates_generator_failure_and_continues(session) -> None:
    tenant_id = uuid.uuid4()
    registry = _registry(
        FieldScheduledGenerator,
        FailingScheduledGenerator,
        PecuariaScheduledGenerator,
    )
    runner = SpyRunner()
    service = AlertSchedulerService(session, registry=registry, runner=runner)

    result = await service.run_scheduled_alerts(tenant_id=tenant_id, domains=["FIELD"])

    assert result.generators_executed == 2
    assert result.errors == 1
    assert [execution.status for execution in result.executions] == ["success", "failed"]
    assert len(runner.calls) == 2


@pytest.mark.asyncio
async def test_scheduler_dry_run_rolls_back_changes(session) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    await _seed_task(session, tenant_id)

    result = await run_scheduled_alerts(
        session,
        tenant_id=tenant_id,
        domains=["FIELD"],
        dry_run=True,
    )

    assert result.generators_executed == 1
    assert result.alerts_created == 1
    assert result.errors == 0
    assert result.executions[0].status == "dry_run"
    replay = await run_scheduled_alerts(session, tenant_id=tenant_id, domains=["FIELD"])
    assert replay.alerts_created == 1
    assert replay.alerts_updated == 0


@pytest.mark.asyncio
async def test_scheduler_preserves_idempotency(session) -> None:
    tenant_id = uuid.uuid4()
    await _seed_tenant(session, tenant_id)
    task = await _seed_task(session, tenant_id)
    dedupe_key = f"campo:tarefa_atrasada:{task.id}"

    first = await run_scheduled_alerts(session, tenant_id=tenant_id, domains=["FIELD"])
    second = await run_scheduled_alerts(session, tenant_id=tenant_id, domains=["FIELD"])

    assert first.alerts_created == 1
    assert second.alerts_updated == 1
    alerts = (
        await session.execute(
            select(OperationalAlert).where(
                OperationalAlert.tenant_id == tenant_id,
                OperationalAlert.dedupe_key == dedupe_key,
            )
        )
    ).scalars().all()
    assert len(alerts) == 1
