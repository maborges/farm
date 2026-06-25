from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from alert_engine.generators.base import BaseAlertGenerator
from alert_engine.generators.context import AlertGeneratorContext
from alert_engine.generators.registry import AlertGeneratorRegistry, alert_generator_registry
from alert_engine.generators.result import AlertGeneratorResult
from alert_engine.generators.runner import AlertGeneratorRunner
from alert_engine.models import Category, Domain


class DummySuccessGenerator(BaseAlertGenerator):
    generator_name = "dummy-success"
    domain = Domain.SYSTEM
    category = Category.GOVERNANCA

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        return AlertGeneratorResult(
            created=2,
            updated=1,
            ignored=1,
            skipped=3,
            warnings=1,
            metadata={"echo": context.metadata.get("echo")},
        )


class DummyFailureGenerator(BaseAlertGenerator):
    generator_name = "dummy-failure"
    domain = Domain.SYSTEM
    category = Category.GOVERNANCA

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        raise RuntimeError(f"boom:{context.scope}")


def test_base_generator_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseAlertGenerator(object())  # type: ignore[abstract]


def test_context_is_extensible() -> None:
    context = AlertGeneratorContext(
        tenant_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        dry_run=True,
        metadata={"trace": "abc"},
        extra_hint="future-field",
    )

    assert context.dry_run is True
    assert context.metadata["trace"] == "abc"
    assert context.model_extra["extra_hint"] == "future-field"


def test_result_defaults_and_metadata() -> None:
    result = AlertGeneratorResult(metadata={"origin": "unit-test"})

    assert result.created == 0
    assert result.updated == 0
    assert result.ignored == 0
    assert result.skipped == 0
    assert result.warnings == 0
    assert result.errors == 0
    assert result.duration_ms == 0
    assert result.metadata["origin"] == "unit-test"


def test_result_supports_optional_execution_fields() -> None:
    now = datetime.now(timezone.utc)  # noqa: UP017
    result = AlertGeneratorResult(
        created=1,
        generator_name="dummy",
        started_at=now,
        finished_at=now,
    )

    assert result.generator_name == "dummy"
    assert result.started_at == now
    assert result.finished_at == now


def test_registry_registers_and_filters_generators() -> None:
    registry = AlertGeneratorRegistry()
    registry.register(DummySuccessGenerator)
    registry.register(DummyFailureGenerator)

    assert registry.get_generator("dummy-success") is DummySuccessGenerator
    assert registry.get_generator("dummy-failure") is DummyFailureGenerator
    assert registry.find_by_domain(Domain.SYSTEM) == (DummySuccessGenerator, DummyFailureGenerator)
    assert registry.find_by_category(Category.GOVERNANCA) == (
        DummySuccessGenerator,
        DummyFailureGenerator,
    )
    assert registry.list_generators() == (DummySuccessGenerator, DummyFailureGenerator)


def test_registry_rejects_duplicate_names() -> None:
    registry = AlertGeneratorRegistry()
    registry.register(DummySuccessGenerator)

    with pytest.raises(ValueError):
        registry.register(DummySuccessGenerator)


def test_global_registry_includes_canonical_generators() -> None:
    names = {generator.generator_name for generator in alert_generator_registry.list_generators()}

    assert "campo" in names
    assert "pecuaria" in names


@pytest.mark.asyncio
async def test_runner_executes_and_finalizes_result(session) -> None:
    generator = DummySuccessGenerator(session)
    context = AlertGeneratorContext(
        tenant_id=uuid.uuid4(), scope="unit-test", metadata={"echo": "yes"}
    )

    result = await AlertGeneratorRunner().execute(generator, context)

    assert result.generator_name == "dummy-success"
    assert result.created == 2
    assert result.updated == 1
    assert result.ignored == 1
    assert result.skipped == 3
    assert result.warnings == 1
    assert result.errors == 0
    assert result.duration_ms >= 0
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.metadata["echo"] == "yes"


@pytest.mark.asyncio
async def test_runner_captures_exceptions(session) -> None:
    generator = DummyFailureGenerator(session)
    context = AlertGeneratorContext(tenant_id=uuid.uuid4(), scope="broken")

    result = await AlertGeneratorRunner().execute(generator, context)

    assert result.generator_name == "dummy-failure"
    assert result.errors == 1
    assert result.metadata["exception_type"] == "RuntimeError"
    assert "boom:broken" in result.metadata["exception_message"]
    assert result.duration_ms >= 0
