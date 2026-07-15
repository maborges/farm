"""Registry runtime de providers ERP.

Responsável por:
- registrar implementações executáveis de ErpProviderRuntime
- resolver implementação por slug
- informar se o runtime está disponível
- rejeitar provider sem implementação
- permitir substituição controlada em testes

O registry não persiste dados e não armazena configuração do Tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from integracoes.erp.provider_contract import ErpProviderRuntime

    ErpProviderFactory = Callable[[AsyncSession], ErpProviderRuntime]


class ErpProviderNotRegisteredError(Exception):
    """Erro levantado quando se tenta resolver um provider não registrado."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Provider ERP não registrado: {slug}")


class ErpProviderDuplicateError(Exception):
    """Erro levantado quando se tenta registrar um provider já existente."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Provider ERP já registrado: {slug}")


class ErpProviderRegistry:
    """Registry singleton em memória para factories de providers ERP.

    Cada provider é registrado com um slug normalizado e uma factory
    que recebe AsyncSession e retorna uma implementação de ErpProviderRuntime.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ErpProviderFactory] = {}

    def register(self, slug: str, factory: ErpProviderFactory) -> None:
        """Registra uma factory de provider ERP.

        Args:
            slug: Slug canônico do provider (normalizado para lowercase).
            factory: Callable que recebe AsyncSession e retorna ErpProviderRuntime.

        Raises:
            ErpProviderDuplicateError: Se o slug já estiver registrado.
        """
        normalized = slug.strip().lower()
        if normalized in self._providers:
            raise ErpProviderDuplicateError(normalized)
        self._providers[normalized] = factory

    def resolve(self, slug: str, session: AsyncSession) -> ErpProviderRuntime:
        """Resolve a implementação de um provider por slug.

        Args:
            slug: Slug canônico do provider.
            session: Sessão de banco de dados para injeção.

        Returns:
            Instância de ErpProviderRuntime.

        Raises:
            ErpProviderNotRegisteredError: Se o slug não estiver registrado.
        """
        normalized = slug.strip().lower()
        factory = self._providers.get(normalized)
        if factory is None:
            raise ErpProviderNotRegisteredError(normalized)
        return factory(session)

    def is_registered(self, slug: str) -> bool:
        """Verifica se um provider está registrado.

        Args:
            slug: Slug canônico do provider.

        Returns:
            True se registrado, False caso contrário.
        """
        return slug.strip().lower() in self._providers

    def _reset(self) -> None:
        """Remove todos os registros. Uso exclusivo em testes."""
        self._providers.clear()


# Instância global do registry.
erp_provider_registry = ErpProviderRegistry()

__all__ = [
    "ErpProviderDuplicateError",
    "ErpProviderNotRegisteredError",
    "ErpProviderRegistry",
    "erp_provider_registry",
]
