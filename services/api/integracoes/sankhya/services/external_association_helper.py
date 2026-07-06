"""Helper Sankhya P0 para associacao oficial com registros externos."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.pessoas.models import Pessoa, PessoaDocumento
from core.cadastros.produtos.models import Produto
from financeiro.models.conciliacao import ContaBancaria
from core.measurements.models import UnidadeMedida
from financeiro.models.despesa import Despesa
from financeiro.models.nota_fiscal import NotaFiscal
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.receita import Receita
from operacional.models.estoque import Deposito
from agricola.models import OperacaoTipoFase
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationConfidence,
    ExternalRecordAssociationOrigin,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.schemas import (
    ExternalRecordAssociationCreate,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationUpdate,
)
from integracoes.services import DuplicateAssociationError, ExternalRecordAssociationService
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.canonical_adapter import SankhyaCanonicalAdapter

_PROVIDER_SLUG = "sankhya"


class SankhyaExternalAssociationHelper:
    """Liga o staging Sankhya ao vinculo oficial de associacao externa."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = ExternalRecordAssociationService(db)
        self.adapter = SankhyaCanonicalAdapter(db)

    async def sync_pessoa(self, tenant_id: str, data: dict[str, Any]) -> ExternalRecordAssociation | None:
        context = await self._ensure_context(tenant_id, "pessoas")
        if context is None:
            return None

        documento = self._normalize_document(data.get("CGC_CPF"))
        local = await self._find_pessoa(tenant_id, documento)
        secondary_keys: dict[str, Any] = {
            "documento": documento,
            "tipo": "PF" if len(documento) == 11 else "PJ" if len(documento) == 14 else None,
            "nome": data.get("NOME"),
            "email": data.get("EMAIL"),
            "telefone": data.get("TELEFONE"),
        }
        return await self._sync_entity_association(
            context=context,
            local_entity="Pessoa",
            external_entity="Parceiro",
            external_record_id=str(data.get("CODPARC", "")),
            local_record_id=str(local.id) if local else None,
            secondary_keys=secondary_keys,
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Pessoa local nao identificada de forma segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

    async def sync_produto(self, tenant_id: str, data: dict[str, Any]) -> ExternalRecordAssociation | None:
        context = await self._ensure_context(tenant_id, "produtos")
        if context is None:
            return None

        local = await self._find_produto(tenant_id, data)
        association = await self._sync_entity_association(
            context=context,
            local_entity="Produto",
            external_entity="Produto",
            external_record_id=str(data.get("CODPROD", "")),
            local_record_id=str(local.id) if local else None,
            secondary_keys={
                "codigo_interno": data.get("CODPROD"),
                "sku": data.get("CODPROD"),
                "codigo_barras": data.get("CODBARRA") or data.get("CODBARRAS"),
                "unidade": self._normalize_code(data.get("UNIDADE", "UN")),
                "descricao": data.get("DESCRPROD"),
            },
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Produto local nao identificado de forma segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )
        await self.sync_unidade_medida(tenant_id, data.get("UNIDADE"), context=context)
        return association

    async def sync_unidade_medida(
        self,
        tenant_id: str,
        unidade_codigo: str | None,
        *,
        context: dict[str, Any] | None = None,
    ) -> ExternalRecordAssociation | None:
        normalized = self._normalize_code(unidade_codigo)
        if not normalized:
            return None

        runtime = context or await self._ensure_context(tenant_id, "produtos")
        if runtime is None:
            return None

        local = await self._find_unidade_medida(tenant_id, normalized)
        return await self._sync_entity_association(
            context=runtime,
            local_entity="UnidadeMedida",
            external_entity="Unidade",
            external_record_id=normalized,
            local_record_id=str(local.id) if local else None,
            secondary_keys={"codigo": normalized, "nome": unidade_codigo},
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Unidade de medida sem equivalencia segura no AgroSaaS.",
        )

    async def sync_nfe(self, tenant_id: str, data: dict[str, Any]) -> ExternalRecordAssociation | None:
        context = await self._ensure_context(tenant_id, "nfe")
        if context is None:
            return None

        chave_acesso = (data.get("CHAVEACESSO") or "").strip()
        if not chave_acesso:
            return None

        local = await self._find_nota_fiscal(tenant_id, chave_acesso)
        return await self._sync_entity_association(
            context=context,
            local_entity="NotaFiscal",
            external_entity="NFe",
            external_record_id=chave_acesso,
            local_record_id=str(local.id) if local else None,
            secondary_keys={
                "nunota": data.get("NUNOTA") or data.get("CODNEG"),
                "numnota": data.get("NUMNOTA"),
                "serie": data.get("SERIE"),
                "modelo": data.get("MODNOTA"),
            },
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.MEDIUM
            ),
            notes=None if local is not None else "Nota fiscal local nao localizada por chave de acesso.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

    async def sync_financeiro(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        context = await self._ensure_context(tenant_id, "financeiro")
        if context is None:
            return None

        tipo = (data.get("TIPO") or "CONTAS_PAGAR").strip().upper()
        local_entity = "Receita" if "RECEBER" in tipo else "Despesa"
        local = await self._find_financeiro(tenant_id, local_entity, data)
        secondary_keys = self._build_financeiro_secondary_keys(data)
        external_record_id = self._build_financeiro_external_id(data)
        association = await self._sync_entity_association(
            context=context,
            local_entity=local_entity,
            external_entity="TituloFinanceiro",
            external_record_id=external_record_id,
            local_record_id=str(local.id) if local else None,
            secondary_keys=secondary_keys,
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Titulo financeiro local nao identificado de forma segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

        await self.sync_plano_natureza(tenant_id, data.get("CODNAT"), context=context)
        return association

    async def sync_organizacao(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> tuple[ExternalRecordAssociation | None, ExternalRecordAssociation | None]:
        """Registra associacoes pendentes para empresa e filial externas.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload do ERP com `CODEMP` e `CODFILIAL`, quando disponiveis.

        Returns:
            Tupla com as associacoes de empresa e filial, nesta ordem.

        Raises:
            None.
        """

        context = await self._ensure_context(tenant_id, "financeiro")
        if context is None:
            return None, None

        empresa = await self._sync_pending_reference(
            context=context,
            local_entity="Empresa",
            external_entity="Empresa",
            external_record_id=self._clean_optional(
                data.get("CODEMP") or data.get("CODEMPRESA")
            ),
            secondary_keys={"codemp": self._clean_optional(data.get("CODEMP") or data.get("CODEMPRESA"))},
            notes="Empresa externa sem master local seguro.",
        )
        filial = await self._sync_pending_reference(
            context=context,
            local_entity="Filial",
            external_entity="Filial",
            external_record_id=self._clean_optional(data.get("CODFILIAL") or data.get("CODFIL")),
            secondary_keys={
                "codemp": self._clean_optional(data.get("CODEMP") or data.get("CODEMPRESA")),
                "codfilial": self._clean_optional(data.get("CODFILIAL") or data.get("CODFIL")),
            },
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
            notes="Filial externa sem master local seguro.",
        )
        return empresa, filial

    async def sync_deposito(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        """Registra a associacao de deposito com CODLOCAL ou referencia textual.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload Sankhya do estoque.

        Returns:
            Associacao oficial criada ou atualizada, quando houver codigo util.

        Raises:
            None.
        """

        context = await self._ensure_context(tenant_id, "estoque")
        if context is None:
            return None

        external_record_id = self._first_identifier(
            data.get("CODLOCAL"),
            data.get("NOMELOCAL"),
            data.get("DESCRLOCAL"),
            data.get("LOCAL"),
        )
        if external_record_id is None:
            return None

        local = await self._find_deposito(tenant_id, data)
        return await self._sync_entity_association(
            context=context,
            local_entity="Deposito",
            external_entity="LocalEstoque",
            external_record_id=external_record_id,
            local_record_id=str(local.id) if local else None,
            secondary_keys={
                "codlocal": self._clean_optional(data.get("CODLOCAL")),
                "nome": self._clean_optional(data.get("NOMELOCAL") or data.get("DESCRLOCAL") or data.get("LOCAL")),
                "tipo": self._clean_optional(data.get("TIPOLOCAL") or data.get("TIPO")),
            },
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Deposito externo sem equivalencia local segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

    async def sync_conta_bancaria(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        """Registra a associacao da conta corrente e pendencias bancarias auxiliares.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload Sankhya com dados bancarios.

        Returns:
            Associacao da conta corrente local, quando localmente identificada.

        Raises:
            None.
        """

        context = await self._ensure_context(tenant_id, "financeiro")
        if context is None:
            return None

        local = await self._find_conta_bancaria(tenant_id, data)
        external_record_id = self._build_conta_bancaria_external_id(data)
        if external_record_id is None:
            return None
        primary = await self._sync_entity_association(
            context=context,
            local_entity="ContaBancaria",
            external_entity="ContaCorrente",
            external_record_id=external_record_id,
            local_record_id=str(local.id) if local else None,
            secondary_keys={
                "banco": self._clean_optional(data.get("CODBANCO") or data.get("BANCO")),
                "agencia": self._clean_optional(data.get("CODAGENCIA") or data.get("AGENCIA")),
                "conta": self._clean_optional(data.get("CONTA") or data.get("NUMCONTA") or data.get("CONTA_CORRENTE")),
                "carteira": self._clean_optional(data.get("CARTEIRA") or data.get("CODCARTEIRA")),
            },
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Conta bancária externa sem equivalencia local segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

        await self._sync_pending_reference(
            context=context,
            local_entity="Banco",
            external_entity="Banco",
            external_record_id=self._first_identifier(data.get("CODBANCO"), data.get("BANCO")),
            secondary_keys={"codbanco": self._clean_optional(data.get("CODBANCO") or data.get("BANCO"))},
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
            notes="Banco externo sem master local.",
        )
        await self._sync_pending_reference(
            context=context,
            local_entity="Agencia",
            external_entity="Agencia",
            external_record_id=self._first_identifier(data.get("CODAGENCIA"), data.get("AGENCIA")),
            secondary_keys={"codagencia": self._clean_optional(data.get("CODAGENCIA") or data.get("AGENCIA"))},
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
            notes="Agencia externa sem master local.",
        )
        await self._sync_pending_reference(
            context=context,
            local_entity="Carteira",
            external_entity="Carteira",
            external_record_id=self._first_identifier(data.get("CARTEIRA"), data.get("CODCARTEIRA")),
            secondary_keys={"carteira": self._clean_optional(data.get("CARTEIRA") or data.get("CODCARTEIRA"))},
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
            notes="Carteira externa sem master local.",
        )
        return primary

    async def sync_centro_custo(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        """Registra a pendencia de centro de custo externo.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload Sankhya com o codigo do centro.

        Returns:
            Associacao pendente quando o codigo externo estiver presente.

        Raises:
            None.
        """

        return await self._sync_pendente_financeiro(
            tenant_id,
            data,
            local_entity="CentroCusto",
            external_entity="CentroCusto",
            external_keys=("CODCENCUS", "CODCCUSTO", "CODCC"),
            notes="Centro de custo externo sem master local seguro.",
        )

    async def sync_centro_resultado(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        """Registra a pendencia de centro de resultado externo.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload Sankhya com o codigo do centro.

        Returns:
            Associacao pendente quando o codigo externo estiver presente.

        Raises:
            None.
        """

        return await self._sync_pendente_financeiro(
            tenant_id,
            data,
            local_entity="CentroResultado",
            external_entity="CentroResultado",
            external_keys=("CODCENRES", "CODCENTRORESULTADO", "CODCCRES"),
            notes="Centro de resultado externo sem master local seguro.",
        )

    async def sync_tipo_operacao(
        self,
        tenant_id: str,
        data: dict[str, Any],
    ) -> ExternalRecordAssociation | None:
        """Registra a associacao de tipo de operacao quando o lookup local existe.

        Args:
            tenant_id: Identificador do tenant em escopo.
            data: Payload Sankhya com codigo e descricao do tipo operacional.

        Returns:
            Associacao oficial ativa ou pendente, quando o tipo for identificado.

        Raises:
            None.
        """

        context = await self._ensure_context(tenant_id, "estoque")
        if context is None:
            return None

        external_record_id = self._first_identifier(
            data.get("CODTIPOPER"),
            data.get("CODTIPOPERACAO"),
            data.get("TIPOOPERACAO"),
            data.get("DESCRTIPOPER"),
        )
        if external_record_id is None:
            return None

        local = await self._find_tipo_operacao(data)
        return await self._sync_entity_association(
            context=context,
            local_entity="OperacaoTipoFase",
            external_entity="TipoOperacao",
            external_record_id=external_record_id,
            local_record_id=str(local.id) if local else None,
            secondary_keys={
                "codigo": self._clean_optional(data.get("CODTIPOPER") or data.get("CODTIPOPERACAO")),
                "tipo_operacao": self._clean_optional(data.get("TIPOOPERACAO") or data.get("DESCRTIPOPER")),
            },
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Tipo de operacao externo sem equivalencia local segura.",
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
        )

    async def sync_plano_natureza(
        self,
        tenant_id: str,
        codnat: str | None,
        *,
        context: dict[str, Any] | None = None,
    ) -> ExternalRecordAssociation | None:
        normalized = (codnat or "").strip()
        if not normalized:
            return None

        runtime = context or await self._ensure_context(tenant_id, "financeiro")
        if runtime is None:
            return None

        local = await self._find_plano_conta(tenant_id, normalized)
        return await self._sync_entity_association(
            context=runtime,
            local_entity="PlanoConta",
            external_entity="NaturezaFinanceira",
            external_record_id=normalized,
            local_record_id=str(local.id) if local else None,
            secondary_keys={"codigo": normalized},
            confidence=(
                ExternalRecordAssociationConfidence.HIGH
                if local is not None
                else ExternalRecordAssociationConfidence.LOW
            ),
            notes=None if local is not None else "Natureza/plano local nao identificado de forma segura.",
        )

    async def _sync_pendente_financeiro(
        self,
        tenant_id: str,
        data: dict[str, Any],
        *,
        local_entity: str,
        external_entity: str,
        external_keys: tuple[str, ...],
        notes: str,
    ) -> ExternalRecordAssociation | None:
        context = await self._ensure_context(tenant_id, "financeiro")
        if context is None:
            return None

        external_record_id = self._first_identifier(*(data.get(key) for key in external_keys))
        if external_record_id is None:
            return None

        return await self._sync_pending_reference(
            context=context,
            local_entity=local_entity,
            external_entity=external_entity,
            external_record_id=external_record_id,
            secondary_keys={
                key.lower(): self._clean_optional(data.get(key))
                for key in external_keys
                if self._clean_optional(data.get(key)) is not None
            },
            external_company_id=self._extract_external_company_id(data),
            external_branch_id=self._extract_external_branch_id(data),
            notes=notes,
        )

    async def _sync_entity_association(
        self,
        *,
        context: dict[str, Any],
        local_entity: str,
        external_entity: str,
        external_record_id: str,
        local_record_id: str | None,
        secondary_keys: dict[str, Any],
        confidence: ExternalRecordAssociationConfidence,
        notes: str | None,
        external_company_id: str | None = None,
        external_branch_id: str | None = None,
    ) -> ExternalRecordAssociation:
        existing = await self._find_existing_association(
            tenant_id=context["tenant_id"],
            provider_id=context["provider_id"],
            config_id=context["config_id"],
            environment=context["environment"],
            external_entity=external_entity,
            external_record_id=external_record_id,
            external_company_id=external_company_id,
            external_branch_id=external_branch_id,
        )
        if local_record_id:
            if existing and existing.local_record_id not in (None, local_record_id):
                return await self.service.mark_conflict(
                    existing,
                    reason="external_record_points_to_different_local_record",
                )
            if existing and existing.local_record_id is None:
                await self.service.detect_duplicate(
                    tenant_id=context["tenant_id"],
                    provider_id=context["provider_id"],
                    config_id=context["config_id"],
                    environment=context["environment"],
                    local_entity=local_entity,
                    local_record_id=local_record_id,
                    external_entity=external_entity,
                    external_record_id=external_record_id,
                    external_company_id=external_company_id,
                    external_branch_id=external_branch_id,
                    ignore_link_id=existing.id,
                )
                return await self.service.reconcile_pending(
                    existing,
                    ExternalRecordAssociationReconcile(
                        local_entity=local_entity,
                        local_record_id=local_record_id,
                        reason="safe_local_match_found",
                        confidence=confidence,
                        notes=notes,
                    ),
                )

        if existing is not None:
            return await self.service.update_association(
                existing,
                ExternalRecordAssociationUpdate(
                    local_entity=local_entity,
                    local_record_id=local_record_id,
                    secondary_keys=secondary_keys,
                    confidence=confidence,
                    notes=notes,
                ),
            )

        status = (
            ExternalRecordAssociationStatus.ACTIVE
            if local_record_id
            else ExternalRecordAssociationStatus.PENDING
        )
        return await self.service.create_association(
            ExternalRecordAssociationCreate(
                tenant_id=context["tenant_id"],
                provider_id=context["provider_id"],
                config_id=context["config_id"],
                feature_id=context["feature_id"],
                environment=context["environment"],
                external_company_id=external_company_id,
                external_branch_id=external_branch_id,
                local_entity=local_entity,
                local_record_id=local_record_id,
                external_entity=external_entity,
                external_record_id=external_record_id,
                secondary_keys=secondary_keys,
                status=status,
                origin=ExternalRecordAssociationOrigin.SYNC_JOB,
                confidence=confidence,
                notes=notes,
            )
        )

    async def _ensure_context(self, tenant_id: str, feature_code: str) -> dict[str, Any] | None:
        context = await self._get_context(tenant_id, feature_code)
        if context is not None:
            return context

        provider_config = await self.db.scalar(
            select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id)
        )
        if provider_config is None:
            return None
        await self.adapter.sync_provider_config(provider_config, reason="external_association_context")
        return await self._get_context(tenant_id, feature_code)

    async def _get_context(self, tenant_id: str, feature_code: str) -> dict[str, Any] | None:
        stmt = (
            select(TenantIntegracao, MarketplaceIntegracao, IntegrationFeature)
            .join(MarketplaceIntegracao, MarketplaceIntegracao.id == TenantIntegracao.integracao_id)
            .join(IntegrationFeature, IntegrationFeature.config_id == TenantIntegracao.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                MarketplaceIntegracao.slug == _PROVIDER_SLUG,
                IntegrationFeature.codigo == feature_code,
            )
        )
        row = (await self.db.execute(stmt)).first()
        if row is None:
            return None
        config, provider, feature = row
        return {
            "tenant_id": tenant_id,
            "provider_id": provider.id,
            "config_id": config.id,
            "feature_id": feature.id,
            "environment": self._resolve_environment(config),
        }

    def _resolve_environment(self, config: TenantIntegracao) -> str:
        payload = config.connection_payload or {}
        return (
            payload.get("sankhya_environment")
            or payload.get("environment")
            or "producao"
        )

    async def _find_existing_association(
        self,
        *,
        tenant_id: str,
        provider_id: int,
        config_id: int,
        environment: str,
        external_entity: str,
        external_record_id: str,
        external_company_id: str | None,
        external_branch_id: str | None,
    ) -> ExternalRecordAssociation | None:
        stmt = select(ExternalRecordAssociation).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == provider_id,
            ExternalRecordAssociation.config_id == config_id,
            ExternalRecordAssociation.environment == environment,
            ExternalRecordAssociation.external_entity == external_entity,
            ExternalRecordAssociation.external_record_id == external_record_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if external_company_id is None:
            stmt = stmt.where(or_(ExternalRecordAssociation.external_company_id.is_(None), ExternalRecordAssociation.external_company_id == ""))
        else:
            stmt = stmt.where(ExternalRecordAssociation.external_company_id == external_company_id)
        if external_branch_id is None:
            stmt = stmt.where(or_(ExternalRecordAssociation.external_branch_id.is_(None), ExternalRecordAssociation.external_branch_id == ""))
        else:
            stmt = stmt.where(ExternalRecordAssociation.external_branch_id == external_branch_id)
        stmt = stmt.order_by(ExternalRecordAssociation.created_at.asc())
        return await self.db.scalar(stmt.limit(1))

    async def _find_pessoa(self, tenant_id: str, documento: str) -> Pessoa | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None or not documento:
            return None
        doc_type = "CPF" if len(documento) == 11 else "CNPJ" if len(documento) == 14 else None
        if doc_type is None:
            return None
        stmt = (
            select(Pessoa)
            .join(PessoaDocumento, PessoaDocumento.pessoa_id == Pessoa.id)
            .where(
                Pessoa.tenant_id == tenant_uuid,
                Pessoa.ativo.is_(True),
                PessoaDocumento.tipo == doc_type,
                PessoaDocumento.numero == documento,
            )
        )
        return await self._scalar_unique(stmt)

    async def _find_produto(self, tenant_id: str, data: dict[str, Any]) -> Produto | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None
        codprod = (str(data.get("CODPROD", "")) or "").strip()
        codigo_barras = (data.get("CODBARRA") or data.get("CODBARRAS") or "").strip()
        nome = (data.get("DESCRPROD") or "").strip()
        unidade = self._normalize_code(data.get("UNIDADE", "UN"))

        exact_codes = [value for value in (codprod, codigo_barras) if value]
        if exact_codes:
            stmt = select(Produto).where(
                or_(Produto.tenant_id == tenant_uuid, Produto.tenant_id.is_(None)),
                Produto.ativo.is_(True),
                or_(
                    Produto.codigo_interno.in_(exact_codes),
                    Produto.sku.in_(exact_codes),
                    Produto.codigo_barras.in_(exact_codes),
                ),
            )
            match = await self._scalar_unique(stmt)
            if match is not None:
                return match

        if nome and unidade:
            stmt = select(Produto).where(
                or_(Produto.tenant_id == tenant_uuid, Produto.tenant_id.is_(None)),
                Produto.ativo.is_(True),
                func.upper(Produto.nome) == nome.upper(),
                func.upper(Produto.unidade_medida) == unidade,
            )
            return await self._scalar_unique(stmt)
        return None

    async def _find_unidade_medida(self, tenant_id: str, codigo: str) -> UnidadeMedida | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None
        stmt = select(UnidadeMedida).where(
            or_(UnidadeMedida.tenant_id == tenant_uuid, UnidadeMedida.tenant_id.is_(None)),
            UnidadeMedida.ativo.is_(True),
            func.upper(UnidadeMedida.codigo) == codigo,
        )
        return await self._scalar_unique(stmt)

    async def _find_nota_fiscal(self, tenant_id: str, chave_acesso: str) -> NotaFiscal | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None
        stmt = select(NotaFiscal).where(
            NotaFiscal.tenant_id == tenant_uuid,
            NotaFiscal.chave_acesso == chave_acesso,
        )
        return await self._scalar_unique(stmt)

    async def _find_financeiro(
        self,
        tenant_id: str,
        local_entity: str,
        data: dict[str, Any],
    ) -> Despesa | Receita | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None

        model = Receita if local_entity == "Receita" else Despesa
        numero_documento = (data.get("NUMDOC") or "").strip()
        data_vencimento = self._parse_date(data.get("DTVENC"))
        valor = self._parse_decimal(data.get("VLRDESDOB"))
        if not numero_documento or data_vencimento is None or valor is None:
            return None

        stmt = select(model).where(
            model.tenant_id == tenant_uuid,
            model.ativo.is_(True),
            or_(model.numero_nf == numero_documento, model.nota_fiscal == numero_documento),
            model.data_vencimento == data_vencimento,
            model.valor_total == valor,
        )
        return await self._scalar_unique(stmt)

    async def _find_plano_conta(self, tenant_id: str, codigo: str) -> PlanoConta | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None
        stmt = select(PlanoConta).where(
            PlanoConta.tenant_id == tenant_uuid,
            PlanoConta.ativo.is_(True),
            PlanoConta.codigo == codigo,
        )
        return await self._scalar_unique(stmt)

    async def _find_deposito(self, tenant_id: str, data: dict[str, Any]) -> Deposito | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None

        candidates = [
            self._normalize_code(data.get("NOMELOCAL")),
            self._normalize_code(data.get("DESCRLOCAL")),
            self._normalize_code(data.get("LOCAL")),
        ]
        candidates = [candidate for candidate in candidates if candidate]
        if not candidates:
            return None

        stmt = select(Deposito).where(
            Deposito.tenant_id == tenant_uuid,
            Deposito.ativo.is_(True),
            or_(
                func.upper(Deposito.nome).in_(candidates),
                func.upper(func.coalesce(Deposito.localizacao_desc, "")).in_(candidates),
            ),
        )
        return await self._scalar_unique(stmt)

    async def _find_conta_bancaria(self, tenant_id: str, data: dict[str, Any]) -> ContaBancaria | None:
        tenant_uuid = self._parse_uuid(tenant_id)
        if tenant_uuid is None:
            return None

        banco = self._clean_optional(data.get("CODBANCO") or data.get("BANCO"))
        agencia = self._clean_optional(data.get("CODAGENCIA") or data.get("AGENCIA"))
        conta = self._clean_optional(data.get("CONTA") or data.get("NUMCONTA") or data.get("CONTA_CORRENTE"))
        nome = self._clean_optional(data.get("NOMECONTA") or data.get("NOME"))

        filters = [ContaBancaria.tenant_id == tenant_uuid, ContaBancaria.ativa.is_(True)]
        if banco is not None:
            filters.append(func.upper(func.coalesce(ContaBancaria.banco, "")) == banco.upper())
        if agencia is not None:
            filters.append(func.upper(func.coalesce(ContaBancaria.agencia, "")) == agencia.upper())
        if conta is not None:
            filters.append(func.upper(func.coalesce(ContaBancaria.conta, "")) == conta.upper())
        if nome is not None:
            filters.append(func.upper(ContaBancaria.nome) == nome.upper())
        if len(filters) == 2:
            return None

        stmt = select(ContaBancaria).where(*filters)
        return await self._scalar_unique(stmt)

    async def _find_tipo_operacao(self, data: dict[str, Any]) -> OperacaoTipoFase | None:
        candidates = [
            self._normalize_code(data.get("TIPOOPERACAO")),
            self._normalize_code(data.get("DESCRTIPOPER")),
        ]
        candidates = [candidate for candidate in candidates if candidate]
        if not candidates:
            return None

        stmt = select(OperacaoTipoFase).where(
            func.upper(OperacaoTipoFase.tipo_operacao).in_(candidates)
        )
        return await self._scalar_unique(stmt)

    async def _sync_pending_reference(
        self,
        *,
        context: dict[str, Any],
        local_entity: str,
        external_entity: str,
        external_record_id: str | None,
        secondary_keys: dict[str, Any] | None = None,
        external_company_id: str | None = None,
        external_branch_id: str | None = None,
        notes: str | None = None,
    ) -> ExternalRecordAssociation | None:
        if external_record_id is None:
            return None
        return await self._sync_entity_association(
            context=context,
            local_entity=local_entity,
            external_entity=external_entity,
            external_record_id=external_record_id,
            local_record_id=None,
            secondary_keys=secondary_keys or {},
            confidence=ExternalRecordAssociationConfidence.LOW,
            notes=notes,
            external_company_id=external_company_id,
            external_branch_id=external_branch_id,
        )

    async def _scalar_unique(self, stmt):
        rows = list((await self.db.execute(stmt.limit(2))).scalars().all())
        if len(rows) == 1:
            return rows[0]
        return None

    def _first_identifier(self, *values: Any) -> str | None:
        for value in values:
            cleaned = self._clean_optional(value)
            if cleaned:
                return cleaned
        return None

    def _build_conta_bancaria_external_id(self, data: dict[str, Any]) -> str | None:
        parts = [
            self._clean_optional(data.get("CODBANCO") or data.get("BANCO")),
            self._clean_optional(data.get("CODAGENCIA") or data.get("AGENCIA")),
            self._clean_optional(data.get("CONTA") or data.get("NUMCONTA") or data.get("CONTA_CORRENTE")),
            self._clean_optional(data.get("CARTEIRA") or data.get("CODCARTEIRA")),
        ]
        values = [part for part in parts if part]
        return "|".join(values) if values else None

    def _build_financeiro_secondary_keys(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "tipo": data.get("TIPO"),
            "codparc": str(data.get("CODPARC", "") or ""),
            "numdoc": data.get("NUMDOC"),
            "desdob": data.get("DESDOB"),
            "vencimento": data.get("DTVENC"),
            "valor": data.get("VLRDESDOB"),
            "codnat": data.get("CODNAT"),
            "codemp": self._extract_external_company_id(data),
            "codfilial": self._extract_external_branch_id(data),
        }

    def _build_financeiro_external_id(self, data: dict[str, Any]) -> str:
        parts = self._build_financeiro_secondary_keys(data)
        ordered = [
            str(parts.get("tipo") or ""),
            str(parts.get("codparc") or ""),
            str(parts.get("numdoc") or ""),
            str(parts.get("desdob") or ""),
            str(parts.get("vencimento") or ""),
            str(parts.get("valor") or ""),
            str(parts.get("codemp") or ""),
            str(parts.get("codfilial") or ""),
        ]
        return "|".join(ordered)

    def _extract_external_company_id(self, data: dict[str, Any]) -> str | None:
        return self._clean_optional(data.get("CODEMP") or data.get("CODEMPRESA"))

    def _extract_external_branch_id(self, data: dict[str, Any]) -> str | None:
        return self._clean_optional(data.get("CODFILIAL") or data.get("CODFIL"))

    def _parse_uuid(self, value: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(str(value))
        except Exception:
            return None

    def _normalize_document(self, value: Any) -> str:
        return re.sub(r"\D+", "", str(value or ""))

    def _normalize_code(self, value: Any) -> str:
        return str(value or "").strip().upper()

    def _clean_optional(self, value: Any) -> str | None:
        cleaned = str(value or "").strip()
        return cleaned or None

    def _parse_date(self, value: Any):
        from datetime import datetime

        if not value:
            return None
        if hasattr(value, "year"):
            return value
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            return None

    def _parse_decimal(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
