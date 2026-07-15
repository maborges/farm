"""Implementação runtime do contrato ErpProviderRuntime para o provider Sankhya.

Delega para os services Sankhya existentes sem duplicar lógica.
Este módulo é a única dependência direta de integracoes.sankhya dentro do
pacote erp (além do bootstrap que o registra).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import IntegrationFeature, MarketplaceIntegracao, TenantIntegracao
from integracoes.sankhya.services import SankhyaSyncService


class SankhyaProviderRuntime:
    """Implementação do contrato ErpProviderRuntime para o Sankhya.

    Reutiliza o SankhyaSyncService existente para todas as operações,
    normalizando os retornos para o formato genérico esperado pelo core.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sync_service = SankhyaSyncService(session)

    @property
    def provider_slug(self) -> str:
        """Slug canônico do Sankhya."""
        return "sankhya"

    async def get_status(self, tenant_id: str) -> dict[str, Any]:
        """Retorna o status operacional via SankhyaSyncService.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com status consolidado.
        """
        return await self._sync_service.obter_status_detalhado(tenant_id)

    async def get_health(self, tenant_id: str) -> dict[str, Any]:
        """Retorna o health check via SankhyaSyncService.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com health consolidado.
        """
        return await self._sync_service.obter_health_detalhado(tenant_id)

    async def get_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista jobs recentes via SankhyaSyncService.

        Args:
            tenant_id: Identificador do tenant.
            limit: Quantidade máxima de jobs.

        Returns:
            Lista de jobs.
        """
        return await self._sync_service.listar_jobs(tenant_id, limit=limit)

    async def get_timeline(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista timeline operacional via SankhyaSyncService.

        Args:
            tenant_id: Identificador do tenant.
            status: Filtro por status.
            feature_code: Filtro por feature.
            origem: Filtro por origem.
            limit: Quantidade máxima.

        Returns:
            Lista de eventos da timeline.
        """
        return await self._sync_service.listar_timeline_operacional(
            tenant_id,
            status=status,
            feature_code=feature_code,
            origem=origem,
            limit=limit,
        )

    async def get_diagnosis(self, tenant_id: str) -> dict[str, Any]:
        """Retorna diagnóstico operacional via SankhyaSyncService.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Dicionário com diagnóstico consolidado.
        """
        return await self._sync_service.obter_diagnostico_operacional(tenant_id)

    async def get_capabilities(self, tenant_id: str) -> list[dict[str, Any]]:
        """Lista capabilities do Sankhya para o tenant.

        Carrega as features habilitadas do TenantIntegracao canônico do Sankhya
        e formata como capabilities genéricas.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            Lista de capabilities com código, status e habilitação.
        """
        config = await self._resolve_canonical_config(tenant_id)
        if config is None:
            return []

        stmt = select(IntegrationFeature).where(
            IntegrationFeature.config_id == config.id
        )
        features = (await self._session.execute(stmt)).scalars().all()

        return [
            {
                "feature_code": feature.codigo,
                "habilitada": feature.habilitada,
                "status": (feature.settings_payload or {}).get("status"),
                "maturity": (feature.settings_payload or {}).get("maturity"),
            }
            for feature in features
        ]

    async def _resolve_canonical_config(
        self,
        tenant_id: str,
    ) -> TenantIntegracao | None:
        """Resolve a TenantIntegracao canônica ativa do Sankhya.

        Args:
            tenant_id: Identificador do tenant.

        Returns:
            TenantIntegracao ou None se não configurado.
        """
        stmt = (
            select(TenantIntegracao)
            .join(
                MarketplaceIntegracao,
                TenantIntegracao.provider_id == MarketplaceIntegracao.id,
            )
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                TenantIntegracao.deleted_at.is_(None),
                MarketplaceIntegracao.slug == "sankhya",
                MarketplaceIntegracao.provider_type == "ERP",
            )
            .order_by(TenantIntegracao.installed_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


__all__ = ["SankhyaProviderRuntime"]
