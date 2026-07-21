"""Implementação runtime do contrato ErpProviderRuntime para o provider Sankhya.

Delega para os services Sankhya existentes sem duplicar lógica.
Este módulo é a única dependência direta de integracoes.sankhya dentro do
pacote erp (além do bootstrap que o registra).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.erp.person_service import ErpPersonImportService
from integracoes.erp.schemas import ErpPersonRecord
from integracoes.models import (
    IntegrationFeature,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.services import (
    SankhyaPessoaService,
    SankhyaProdutoService,
    SankhyaSyncService,
    SankhyaWSClient,
)


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

        stmt = select(IntegrationFeature).where(IntegrationFeature.config_id == config.id)
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

    async def sync_feature(
        self,
        tenant_id: str,
        feature_code: str,
        *,
        scheduled: bool = False,
    ) -> dict[str, Any]:
        """Executar Pessoas ou Produtos reutilizando os services Sankhya existentes."""
        if feature_code == "pessoas" and scheduled:
            return await self._sync_scheduled_people(tenant_id)
        services = {
            "pessoas": SankhyaPessoaService(self._session),
            "produtos": SankhyaProdutoService(self._session),
        }
        service = services.get(feature_code)
        if service is None:
            raise ValueError(f"Fluxo sem executor Sankhya: {feature_code}")
        operation = "sync" if scheduled else "import"
        log = await self._sync_service.iniciar_sync_log(tenant_id, feature_code, operation)
        try:
            if feature_code == "pessoas":
                processed = await service.importar_pessoas(tenant_id)
            else:
                processed = await service.importar_produtos(tenant_id)
            await self._sync_service.finalizar_sync_log(log.id, True, processed)
            return {"feature_code": feature_code, "processados": processed, "sucesso": True}
        except Exception as exc:
            await self._sync_service.finalizar_sync_log(log.id, False, 0, 1, str(exc))
            raise

    async def _sync_scheduled_people(self, tenant_id: str) -> dict[str, Any]:
        """Executar Pessoas pelo escopo salvo na política canônica."""
        scope, config_id = await self._people_policy_context(tenant_id)
        processed = await ErpPersonImportService(
            self._session, self, config_id=config_id
        ).sincronizar(
            uuid.UUID(tenant_id), scope
        )
        return {"feature_code": "pessoas", "processados": processed, "sucesso": True}

    async def _people_policy_context(self, tenant_id: str) -> tuple[str, int | None]:
        config = await self._resolve_canonical_config(tenant_id)
        stmt = (
            select(IntegrationSyncPolicy)
            .join(IntegrationFeature, IntegrationFeature.id == IntegrationSyncPolicy.feature_id)
            .where(
                IntegrationSyncPolicy.tenant_id == tenant_id,
                IntegrationFeature.codigo == "pessoas",
                IntegrationSyncPolicy.deleted_at.is_(None),
            )
        )
        if config is not None:
            stmt = stmt.where(IntegrationSyncPolicy.config_id == config.id)
        policy = await self._session.scalar(stmt.limit(1))
        if policy is None:
            return "LINKED_ONLY", config.id if config is not None else None
        scope = (policy.settings_payload or {}).get("record_scope", "LINKED_ONLY")
        return scope, policy.config_id

    async def get_person_by_external_id(
        self,
        tenant_id: str,
        external_id: str,
    ) -> dict[str, Any] | None:
        """Consultar Parceiro no Sankhya e devolver o contrato canônico."""
        config = await self._sync_service._get_operational_config(tenant_id)
        if config is None:
            return None
        async with SankhyaWSClient(config) as client:
            data = await client.buscar_registro("PessoaJuridica", "findAll", external_id)
            if not data:
                data = await client.buscar_registro("PessoaFisica", "findAll", external_id)
        return self._normalize_person(data).model_dump() if data else None

    async def list_people(self, tenant_id: str) -> list[dict[str, Any]]:
        """Listar Parceiros somente para a política explícita ALL_EXTERNAL."""
        config = await self._sync_service._get_operational_config(tenant_id)
        if config is None:
            return []
        async with SankhyaWSClient(config) as client:
            physical = await client.executar_ws("PessoaFisica", "findAll", {})
            legal = await client.executar_ws("PessoaJuridica", "findAll", {})
        records = physical.get("pessoas", []) + legal.get("pessoas", [])
        return [self._normalize_person(item).model_dump() for item in records]

    @staticmethod
    def _normalize_person(data: dict[str, Any]) -> ErpPersonRecord:
        """Normalizar campos permitidos do Parceiro para Pessoa ERP."""
        tipo = "PF" if str(data.get("TIPPESSOA", "")).upper() == "F" else "PJ"
        document = str(data.get("CGC_CPF") or "") or None
        return ErpPersonRecord(
            external_id=str(data.get("CODPARC", "")),
            tipo=tipo,
            nome_exibicao=str(data.get("NOME") or data.get("NOMEFANTASIA") or ""),
            cpf=document if tipo == "PF" else None,
            cnpj=document if tipo == "PJ" else None,
            razao_social=data.get("NOME") if tipo == "PJ" else None,
            nome_fantasia=data.get("NOMEFANTASIA") if tipo == "PJ" else None,
            inscricao_estadual=data.get("INSCRICAO"),
            email=data.get("EMAIL"),
            telefone=data.get("TELEFONE"),
            cep=data.get("CEP"),
            logradouro=data.get("ENDERECO"),
            numero=data.get("NUMEND"),
            complemento=data.get("COMPLEMENTO"),
            bairro=data.get("BAIRRO"),
            cidade=data.get("CIDADE"),
            estado=data.get("UF"),
            ativo_no_erp=str(data.get("ATIVO", "S")).upper() == "S",
        )

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
