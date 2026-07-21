"""Contrato runtime formal para providers ERP.

Define o protocolo que qualquer implementação de provider ERP deve satisfazer
para ser utilizável pelas superfícies genéricas do core (router, readiness, etc).

Não depende de nenhum provider concreto.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ErpProviderRuntime(Protocol):
    """Contrato runtime que todo provider ERP deve implementar.

    Os métodos cobrem as superfícies genéricas expostas pelo router ERP.
    Os tipos de retorno são dicionários genéricos para evitar acoplamento
    com schemas provider-specific.

    Métodos deliberadamente excluídos desta fase:
        - get_configuration / save_configuration
        - test_connection / rotate_credentials
        - sync_people / sync_products / sync_all
        - field_definitions / schema_builders
    """

    @property
    def provider_slug(self) -> str:
        """Slug canônico do provider (ex: 'sankhya')."""
        ...

    async def get_status(self, tenant_id: str) -> dict[str, Any]:
        """Retorna o status operacional consolidado da integração ERP.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com campos de status compatíveis com o schema ERP.
        """
        ...

    async def get_health(self, tenant_id: str) -> dict[str, Any]:
        """Retorna o health check da integração ERP.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com campos de health compatíveis com o schema ERP.
        """
        ...

    async def get_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista os jobs de sincronização recentes.

        Args:
            tenant_id: Identificador do tenant.
            limit: Quantidade máxima de jobs.

        Returns:
            Lista de dicionários representando jobs.
        """
        ...

    async def get_timeline(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista a timeline operacional consolidada.

        Args:
            tenant_id: Identificador do tenant.
            status: Filtro por status do evento.
            feature_code: Filtro por código de feature.
            origem: Filtro por origem do dado.
            limit: Quantidade máxima de itens.

        Returns:
            Lista de dicionários representando eventos da timeline.
        """
        ...

    async def get_diagnosis(self, tenant_id: str) -> dict[str, Any]:
        """Retorna o diagnóstico operacional consolidado.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com campos de diagnóstico compatíveis com o schema ERP.
        """
        ...

    async def get_capabilities(self, tenant_id: str) -> list[dict[str, Any]]:
        """Lista as capabilities operacionais do provider para o tenant.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Lista de dicionários descrevendo capabilities habilitadas.
        """
        ...

    async def sync_feature(
        self,
        tenant_id: str,
        feature_code: str,
        *,
        scheduled: bool = False,
    ) -> dict[str, Any]:
        """Executar um fluxo usando o runtime legado oficial do provider."""
        ...

    async def get_person_by_external_id(
        self,
        tenant_id: str,
        external_id: str,
    ) -> dict[str, Any] | None:
        """Consultar uma pessoa no ERP pelo identificador externo."""
        ...

    async def list_people(self, tenant_id: str) -> list[dict[str, Any]]:
        """Listar pessoas somente para políticas automáticas de escopo total."""
        ...


__all__ = ["ErpProviderRuntime"]
