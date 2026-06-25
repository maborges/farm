from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from loguru import logger

from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .result import AlertGeneratorResult


class AlertGeneratorRunner:
    """Infrastructure executor for canonical Alert Engine generators."""

    async def execute(
        self,
        generator: BaseAlertGenerator,
        context: AlertGeneratorContext,
    ) -> AlertGeneratorResult:
        """Execute a generator with timing and structured logging."""

        started_at = datetime.now(timezone.utc)  # noqa: UP017
        start = perf_counter()
        bound_logger = logger.bind(
            component="alert_generator_runner",
            generator=self._generator_name(generator),
            tenant_id=str(context.tenant_id),
            unidade_produtiva_id=str(context.unidade_produtiva_id)
            if context.unidade_produtiva_id
            else None,
            batch_id=str(context.batch_id) if context.batch_id else None,
            event_id=str(context.event_id) if context.event_id else None,
            scope=context.scope,
            dry_run=context.dry_run,
            reason=context.reason,
        )
        bound_logger.info("alert_generator_started")
        try:
            result = await generator.run(context)
        except Exception as exc:  # pragma: no cover - exercised in error-path tests
            result = AlertGeneratorResult(
                errors=1,
                generator_name=self._generator_name(generator),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),  # noqa: UP017
                metadata={
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                },
            )
            bound_logger.exception("alert_generator_failed")
            return self._finalize(result, start, started_at)

        normalized = self._normalize_result(result, generator)
        bound_logger.bind(
            created=normalized.created,
            updated=normalized.updated,
            ignored=normalized.ignored,
            skipped=normalized.skipped,
            warnings=normalized.warnings,
            errors=normalized.errors,
        ).info("alert_generator_finished")
        return self._finalize(normalized, start, started_at)

    @staticmethod
    def _normalize_result(
        result: AlertGeneratorResult | dict[str, Any],
        generator: BaseAlertGenerator,
    ) -> AlertGeneratorResult:
        if isinstance(result, AlertGeneratorResult):
            return result.model_copy(
                update={"generator_name": result.generator_name or generator.generator_name}
            )
        return AlertGeneratorResult.model_validate(result).model_copy(
            update={"generator_name": generator.generator_name}
        )

    @staticmethod
    def _finalize(
        result: AlertGeneratorResult,
        start: float,
        started_at: datetime,
    ) -> AlertGeneratorResult:
        finished_at = result.finished_at or datetime.now(timezone.utc)  # noqa: UP017
        duration_ms = int((perf_counter() - start) * 1000)
        return result.model_copy(
            update={
                "started_at": result.started_at or started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
            }
        )

    @staticmethod
    def _generator_name(generator: BaseAlertGenerator) -> str:
        return getattr(generator, "generator_name", generator.__class__.__name__)
