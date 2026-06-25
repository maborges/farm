from __future__ import annotations

from alert_engine.models import Category, Domain

from .base import BaseAlertGenerator


class AlertGeneratorRegistry:
    """Explicit in-memory registry for canonical Alert Engine generators."""

    def __init__(self) -> None:
        self._generators: dict[str, type[BaseAlertGenerator]] = {}

    def register(self, generator_cls: type[BaseAlertGenerator]) -> type[BaseAlertGenerator]:
        """Register a generator class by its canonical name."""

        generator_name = self._resolve_name(generator_cls)
        if generator_name in self._generators:
            raise ValueError(f"Generator already registered: {generator_name}")
        self._generators[generator_name] = generator_cls
        return generator_cls

    def get_generator(self, generator_name: str) -> type[BaseAlertGenerator] | None:
        """Return a registered generator by name."""

        return self._generators.get(generator_name)

    def list_generators(self) -> tuple[type[BaseAlertGenerator], ...]:
        """Return all registered generators in registration order."""

        return tuple(self._generators.values())

    def find_by_domain(self, domain: Domain | str) -> tuple[type[BaseAlertGenerator], ...]:
        """Return generators bound to a specific domain."""

        return tuple(
            generator_cls
            for generator_cls in self._generators.values()
            if self._enum_value(getattr(generator_cls, "domain", None)) == self._enum_value(domain)
        )

    def find_by_category(self, category: Category | str) -> tuple[type[BaseAlertGenerator], ...]:
        """Return generators bound to a specific category."""

        return tuple(
            generator_cls
            for generator_cls in self._generators.values()
            if self._enum_value(getattr(generator_cls, "category", None))
            == self._enum_value(category)
        )

    def find_scheduled_generators(self) -> tuple[type[BaseAlertGenerator], ...]:
        """Return generators eligible for scheduled execution."""

        return tuple(
            generator_cls
            for generator_cls in self._generators.values()
            if self._is_scheduled(generator_cls)
        )

    @staticmethod
    def _resolve_name(generator_cls: type[BaseAlertGenerator]) -> str:
        generator_name = getattr(generator_cls, "generator_name", None)
        if not generator_name:
            return generator_cls.__name__
        return str(generator_name)

    @staticmethod
    def _enum_value(value: Domain | Category | str | None) -> str | None:
        if value is None:
            return None
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    @staticmethod
    def _is_scheduled(generator_cls: type[BaseAlertGenerator]) -> bool:
        modes = getattr(generator_cls, "execution_modes", ())
        return any(mode in {"scheduled", "hybrid"} for mode in modes)


alert_generator_registry = AlertGeneratorRegistry()


def register_alert_generator(generator_cls: type[BaseAlertGenerator]) -> type[BaseAlertGenerator]:
    """Decorator that registers a generator in the canonical registry."""

    return alert_generator_registry.register(generator_cls)
