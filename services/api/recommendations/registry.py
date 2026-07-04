from __future__ import annotations

from typing import Iterable

from .provider import RecommendationProvider


class RecommendationProviderRegistry:
    """Explicit in-memory registry for recommendation providers."""

    def __init__(self) -> None:
        self._providers: dict[str, type[RecommendationProvider]] = {}

    def register(self, provider_cls: type[RecommendationProvider]) -> type[RecommendationProvider]:
        provider_name = self._resolve_name(provider_cls)
        if provider_name in self._providers:
            raise ValueError(f"Provider already registered: {provider_name}")
        self._providers[provider_name] = provider_cls
        return provider_cls

    def get_provider(self, provider_name: str) -> type[RecommendationProvider] | None:
        return self._providers.get(provider_name)

    def list_providers(self) -> tuple[type[RecommendationProvider], ...]:
        return tuple(self._providers.values())

    def find_by_domain(self, domain: str) -> tuple[type[RecommendationProvider], ...]:
        normalized = domain.upper()
        return tuple(
            provider_cls
            for provider_cls in self._providers.values()
            if normalized in self._provider_domains(provider_cls)
        )

    def register_many(
        self,
        provider_classes: Iterable[type[RecommendationProvider]],
    ) -> tuple[type[RecommendationProvider], ...]:
        registered: list[type[RecommendationProvider]] = []
        for provider_cls in provider_classes:
            provider_name = self._resolve_name(provider_cls)
            if provider_name in self._providers:
                continue
            self._providers[provider_name] = provider_cls
            registered.append(provider_cls)
        return tuple(registered)

    @staticmethod
    def _resolve_name(provider_cls: type[RecommendationProvider]) -> str:
        provider_name = getattr(provider_cls, "provider_name", None)
        if not provider_name:
            return provider_cls.__name__
        return str(provider_name)

    @staticmethod
    def _provider_domains(provider_cls: type[RecommendationProvider]) -> tuple[str, ...]:
        values = getattr(provider_cls, "domains", ())
        return tuple(str(value).upper() for value in values if str(value).strip())


recommendation_provider_registry = RecommendationProviderRegistry()


def register_recommendation_provider(
    provider_cls: type[RecommendationProvider],
) -> type[RecommendationProvider]:
    return recommendation_provider_registry.register(provider_cls)
