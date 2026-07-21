"""Promoção controlada de pessoas do ERP para o cadastro canônico."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.pessoas.models import (
    Pessoa,
    PessoaContato,
    PessoaDocumento,
    PessoaEndereco,
    PessoaPII,
    PessoaRelacionamento,
    TipoRelacionamento,
)
from integracoes.erp.provider_contract import ErpProviderRuntime
from integracoes.erp.schemas import (
    ErpPersonImportRequest,
    ErpPersonImportResponse,
    ErpPersonRecord,
)
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationConfidence,
    ExternalRecordAssociationOrigin,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.schemas import (
    ExternalRecordAssociationCreate,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationUpdate,
)
from integracoes.services import ExternalRecordAssociationService


class ErpPersonNotFoundError(LookupError):
    """Pessoa inexistente no provider ERP ativo."""


class ErpPersonConflictError(ValueError):
    """ID externo ou documento já associado de forma incompatível."""


@dataclass(frozen=True)
class ErpPersonContext:
    """Contexto tenant-safe da capability Pessoas."""

    provider_id: int
    config_id: int
    feature_id: int
    environment: str


class ErpPersonImportService:
    """Consulta o provider e atualiza somente o cadastro canônico do tenant."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: ErpProviderRuntime,
        *,
        config_id: int | None = None,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.config_id = config_id
        self.associations = ExternalRecordAssociationService(session)

    async def consultar(self, tenant_id: uuid.UUID, external_id: str) -> ErpPersonRecord:
        """Consultar e validar uma pessoa pelo ID no ERP ativo."""
        payload = await self.runtime.get_person_by_external_id(str(tenant_id), external_id.strip())
        if payload is None:
            raise ErpPersonNotFoundError(f"Pessoa {external_id} não encontrada no ERP.")
        return ErpPersonRecord.model_validate(payload)

    async def importar(
        self,
        tenant_id: uuid.UUID,
        request: ErpPersonImportRequest,
    ) -> ErpPersonImportResponse:
        """Criar ou atualizar uma Pessoa e seu vínculo externo de forma idempotente."""
        record = await self.consultar(tenant_id, request.external_id)
        return await self._persist_record(tenant_id, request, record)

    async def sincronizar(self, tenant_id: uuid.UUID, record_scope: str) -> int:
        """Executar atualização automática no escopo autorizado pela política."""
        if record_scope == "ALL_EXTERNAL":
            records = await self.runtime.list_people(str(tenant_id))
            return await self._sync_all_records(tenant_id, records)
        return await self._sync_linked_records(tenant_id)

    async def _sync_linked_records(self, tenant_id: uuid.UUID) -> int:
        context = await self._load_context(tenant_id)
        stmt = select(ExternalRecordAssociation).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == context.provider_id,
            ExternalRecordAssociation.config_id == context.config_id,
            ExternalRecordAssociation.local_entity == "Pessoa",
            ExternalRecordAssociation.local_record_id.is_not(None),
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.ACTIVE.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        links = list((await self.session.scalars(stmt)).all())
        for link in links:
            request = ErpPersonImportRequest(
                external_id=link.external_record_id, pessoa_id=link.local_record_id
            )
            await self.importar(tenant_id, request)
        return len(links)

    async def _sync_all_records(
        self, tenant_id: uuid.UUID, payloads: list[dict[str, object]]
    ) -> int:
        processed = 0
        for payload in payloads:
            record = ErpPersonRecord.model_validate(payload)
            await self._persist_record(
                tenant_id,
                ErpPersonImportRequest(external_id=record.external_id),
                record,
            )
            processed += 1
        return processed

    async def _persist_record(
        self,
        tenant_id: uuid.UUID,
        request: ErpPersonImportRequest,
        record: ErpPersonRecord,
    ) -> ErpPersonImportResponse:
        context = await self._load_context(tenant_id)
        try:
            pessoa, created = await self._resolve_person(tenant_id, request, record, context)
            self._apply_person_fields(pessoa, record)
            await self._upsert_pii(pessoa, record)
            await self._upsert_contacts(pessoa, record)
            await self._upsert_endereco(pessoa, record)
            await self._add_relationships(pessoa, request.relacionamento_tipo_ids, tenant_id)
            await self.session.flush()
            await self._link_external(tenant_id, pessoa, record, context)
            await self._commit_preserving_rls()
        except Exception:
            await self.session.rollback()
            raise
        return self._build_response(pessoa, record, created)

    async def _load_context(self, tenant_id: uuid.UUID) -> ErpPersonContext:
        stmt = (
            select(TenantIntegracao, MarketplaceIntegracao, IntegrationFeature)
            .join(MarketplaceIntegracao, MarketplaceIntegracao.id == TenantIntegracao.integracao_id)
            .join(IntegrationFeature, IntegrationFeature.config_id == TenantIntegracao.id)
            .join(IntegrationSyncPolicy, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                TenantIntegracao.deleted_at.is_(None),
                MarketplaceIntegracao.slug == self.runtime.provider_slug,
                MarketplaceIntegracao.ativa.is_(True),
                IntegrationFeature.codigo == "pessoas",
                IntegrationFeature.habilitada.is_(True),
                IntegrationSyncPolicy.ativa.is_(True),
                IntegrationSyncPolicy.deleted_at.is_(None),
            )
        )
        if self.config_id is not None:
            stmt = stmt.where(TenantIntegracao.id == self.config_id)
        row = (await self.session.execute(stmt)).first()
        if row is None:
            raise ErpPersonNotFoundError("Integração de Pessoas não configurada para o tenant.")
        config, provider, feature = row
        connection = config.connection_payload or {}
        environment = connection.get("environment") or connection.get("sankhya_environment")
        return ErpPersonContext(provider.id, config.id, feature.id, environment or "producao")

    async def _resolve_person(
        self,
        tenant_id: uuid.UUID,
        request: ErpPersonImportRequest,
        record: ErpPersonRecord,
        context: ErpPersonContext,
    ) -> tuple[Pessoa, bool]:
        association = await self._find_association(tenant_id, record.external_id, context)
        requested = await self._load_requested_person(tenant_id, request.pessoa_id)
        if association and association.local_record_id:
            linked = await self._load_person(tenant_id, association.local_record_id)
            if requested and requested.id != linked.id:
                raise ErpPersonConflictError("ID do ERP já está vinculado a outra pessoa.")
            return linked, False
        if requested:
            return requested, False
        matched = await self._find_document_match(tenant_id, record)
        if matched:
            return matched, False
        pessoa = Pessoa(tenant_id=tenant_id, tipo=record.tipo, nome_exibicao=record.nome_exibicao)
        pessoa.base_legal = request.base_legal
        self.session.add(pessoa)
        await self.session.flush()
        return pessoa, True

    async def _load_requested_person(
        self, tenant_id: uuid.UUID, pessoa_id: str | None
    ) -> Pessoa | None:
        if not pessoa_id:
            return None
        return await self._load_person(tenant_id, pessoa_id)

    async def _load_person(self, tenant_id: uuid.UUID, pessoa_id: str) -> Pessoa:
        try:
            parsed_id = uuid.UUID(str(pessoa_id))
        except ValueError as exc:
            raise ErpPersonConflictError("Identificador local de pessoa inválido.") from exc
        pessoa = await self.session.scalar(
            select(Pessoa).where(Pessoa.id == parsed_id, Pessoa.tenant_id == tenant_id)
        )
        if pessoa is None:
            raise ErpPersonNotFoundError("Pessoa local não encontrada neste tenant.")
        return pessoa

    async def _find_association(
        self, tenant_id: uuid.UUID, external_id: str, context: ErpPersonContext
    ) -> ExternalRecordAssociation | None:
        stmt = select(ExternalRecordAssociation).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == context.provider_id,
            ExternalRecordAssociation.config_id == context.config_id,
            ExternalRecordAssociation.external_entity == "Parceiro",
            ExternalRecordAssociation.external_record_id == external_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        return await self.session.scalar(stmt.limit(1))

    async def _find_document_match(
        self, tenant_id: uuid.UUID, record: ErpPersonRecord
    ) -> Pessoa | None:
        document = self._normalize_document(record.cpf or record.cnpj)
        if not document:
            return None
        candidates = self._document_candidates(document)
        field = PessoaPII.cpf if record.tipo == "PF" else PessoaPII.cnpj
        stmt = select(Pessoa).join(PessoaPII, PessoaPII.pessoa_id == Pessoa.id).where(
            Pessoa.tenant_id == tenant_id, field.in_(candidates)
        )
        matches = list((await self.session.scalars(stmt.limit(2))).all())
        if len(matches) > 1:
            raise ErpPersonConflictError("Documento corresponde a mais de uma pessoa local.")
        return matches[0] if matches else None

    @staticmethod
    def _apply_person_fields(pessoa: Pessoa, record: ErpPersonRecord) -> None:
        """Atualizar somente campos cadastrais governados pelo ERP."""
        pessoa.tipo = record.tipo
        pessoa.nome_exibicao = record.nome_exibicao

    async def _upsert_pii(self, pessoa: Pessoa, record: ErpPersonRecord) -> None:
        pii = await self.session.scalar(select(PessoaPII).where(PessoaPII.pessoa_id == pessoa.id))
        if pii is None:
            pii = PessoaPII(pessoa_id=pessoa.id)
            self.session.add(pii)
        pii.nome_completo = record.nome_exibicao if record.tipo == "PF" else None
        pii.cpf = record.cpf if record.tipo == "PF" else None
        pii.razao_social = record.razao_social if record.tipo == "PJ" else None
        pii.nome_fantasia = record.nome_fantasia if record.tipo == "PJ" else None
        pii.cnpj = record.cnpj if record.tipo == "PJ" else None
        pii.ie = record.inscricao_estadual if record.tipo == "PJ" else None
        await self._upsert_document(pessoa, record)

    async def _upsert_document(self, pessoa: Pessoa, record: ErpPersonRecord) -> None:
        number = record.cpf if record.tipo == "PF" else record.cnpj
        doc_type = "CPF" if record.tipo == "PF" else "CNPJ"
        document = await self.session.scalar(
            select(PessoaDocumento).where(
                PessoaDocumento.pessoa_id == pessoa.id, PessoaDocumento.tipo == doc_type
            )
        )
        if not number:
            if document is not None:
                await self.session.delete(document)
            return
        if document is None:
            document = PessoaDocumento(pessoa_id=pessoa.id, tipo=doc_type, numero=number)
            self.session.add(document)
        document.numero = number
        document.nome_completo = record.nome_exibicao if record.tipo == "PF" else None
        document.razao_social = record.razao_social if record.tipo == "PJ" else None
        document.nome_fantasia = record.nome_fantasia if record.tipo == "PJ" else None

    async def _upsert_contacts(self, pessoa: Pessoa, record: ErpPersonRecord) -> None:
        await self._upsert_contact(pessoa, "EMAIL", record.email)
        await self._upsert_contact(pessoa, "TELEFONE", record.telefone)

    async def _upsert_contact(self, pessoa: Pessoa, kind: str, value: str | None) -> None:
        contact = await self.session.scalar(
            select(PessoaContato).where(
                PessoaContato.pessoa_id == pessoa.id,
                PessoaContato.tipo == kind,
                PessoaContato.principal.is_(True),
            )
        )
        if not value:
            if contact is not None:
                contact.ativo = False
            return
        if contact is None:
            contact = PessoaContato(pessoa_id=pessoa.id, tipo=kind, valor=value, principal=True)
            self.session.add(contact)
        contact.valor = value
        contact.ativo = True

    async def _upsert_endereco(self, pessoa: Pessoa, record: ErpPersonRecord) -> None:
        has_data = any(
            [record.cep, record.logradouro, record.bairro, record.cidade, record.estado]
        )
        endereco = await self.session.scalar(
            select(PessoaEndereco).where(
                PessoaEndereco.pessoa_id == pessoa.id,
                PessoaEndereco.tipo == "PRINCIPAL",
            )
        )
        if not has_data:
            if endereco is not None:
                endereco.ativo = False
            return
        if endereco is None:
            endereco = PessoaEndereco(pessoa_id=pessoa.id, tipo="PRINCIPAL", principal=True)
            self.session.add(endereco)
        endereco.cep = record.cep
        endereco.logradouro = record.logradouro
        endereco.numero = record.numero
        endereco.complemento = record.complemento
        endereco.bairro = record.bairro
        endereco.cidade = record.cidade
        endereco.estado = record.estado
        endereco.ativo = True

    async def _add_relationships(
        self, pessoa: Pessoa, raw_ids: list[str], tenant_id: uuid.UUID
    ) -> None:
        for raw_id in raw_ids:
            try:
                type_id = uuid.UUID(raw_id)
            except ValueError as exc:
                raise ErpPersonConflictError(
                    "Tipo de relacionamento inválido para o tenant."
                ) from exc
            relationship_type = await self.session.scalar(
                select(TipoRelacionamento).where(
                    TipoRelacionamento.id == type_id,
                    or_(
                        TipoRelacionamento.tenant_id == tenant_id,
                        TipoRelacionamento.tenant_id.is_(None),
                    ),
                )
            )
            if relationship_type is None:
                raise ErpPersonConflictError("Tipo de relacionamento inválido para o tenant.")
            existing = await self.session.scalar(
                select(PessoaRelacionamento).where(
                    PessoaRelacionamento.pessoa_id == pessoa.id,
                    PessoaRelacionamento.tipo_id == type_id,
                )
            )
            if existing is None:
                self.session.add(PessoaRelacionamento(pessoa_id=pessoa.id, tipo_id=type_id))

    async def _link_external(
        self,
        tenant_id: uuid.UUID,
        pessoa: Pessoa,
        record: ErpPersonRecord,
        context: ErpPersonContext,
    ) -> None:
        existing = await self._find_association(tenant_id, record.external_id, context)
        if existing and existing.local_record_id not in (None, str(pessoa.id)):
            raise ErpPersonConflictError("ID do ERP já está vinculado a outra pessoa.")
        payload = self._association_payload(tenant_id, pessoa, record, context)
        current = await self._find_active_local_association(tenant_id, pessoa, context)
        if existing and existing.local_record_id is None:
            if current and current.external_record_id != record.external_id:
                await self.associations.deactivate_association(
                    current,
                    reason="manual_erp_reassociation",
                )
            await self.associations.reconcile_pending(
                existing,
                ExternalRecordAssociationReconcile(
                    local_entity="Pessoa",
                    local_record_id=str(pessoa.id),
                    reason="manual_erp_import",
                ),
            )
            return
        if current and current.external_record_id != record.external_id:
            await self.associations.replace_association(
                current,
                payload,
                reason="manual_erp_reassociation",
            )
            return
        if existing:
            await self.associations.update_association(
                existing,
                ExternalRecordAssociationUpdate(
                    secondary_keys=payload.secondary_keys,
                    last_sync_at=payload.last_sync_at,
                    confidence=ExternalRecordAssociationConfidence.MANUAL_CONFIRMED,
                    reason="manual_erp_refresh",
                ),
            )
            return
        await self.associations.create_association(payload)

    async def _find_active_local_association(
        self,
        tenant_id: uuid.UUID,
        pessoa: Pessoa,
        context: ErpPersonContext,
    ) -> ExternalRecordAssociation | None:
        stmt = select(ExternalRecordAssociation).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == context.provider_id,
            ExternalRecordAssociation.config_id == context.config_id,
            ExternalRecordAssociation.local_entity == "Pessoa",
            ExternalRecordAssociation.local_record_id == str(pessoa.id),
            ExternalRecordAssociation.external_entity == "Parceiro",
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.ACTIVE.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        return await self.session.scalar(stmt.limit(1))

    def _association_payload(
        self,
        tenant_id: uuid.UUID,
        pessoa: Pessoa,
        record: ErpPersonRecord,
        context: ErpPersonContext,
    ) -> ExternalRecordAssociationCreate:
        return ExternalRecordAssociationCreate(
            tenant_id=str(tenant_id),
            provider_id=context.provider_id,
            config_id=context.config_id,
            feature_id=context.feature_id,
            environment=context.environment,
            local_entity="Pessoa",
            local_record_id=str(pessoa.id),
            external_entity="Parceiro",
            external_record_id=record.external_id,
            secondary_keys={"documento": record.cpf or record.cnpj, "email": record.email},
            status=ExternalRecordAssociationStatus.ACTIVE,
            origin=ExternalRecordAssociationOrigin.MANUAL_RECONCILIATION,
            confidence=ExternalRecordAssociationConfidence.MANUAL_CONFIRMED,
            last_sync_at=datetime.now(timezone.utc),  # noqa: UP017 - runtime Python 3.10
            metadata_json={"ativo_no_erp": record.ativo_no_erp},
        )

    def _build_response(
        self, pessoa: Pessoa, record: ErpPersonRecord, created: bool
    ) -> ErpPersonImportResponse:
        action = "criada" if created else "atualizada"
        return ErpPersonImportResponse(
            pessoa_id=str(pessoa.id),
            external_id=record.external_id,
            created=created,
            provider_slug=self.runtime.provider_slug,
            message=f"Pessoa {action} com dados do ERP.",
        )

    @staticmethod
    def _normalize_document(value: str | None) -> str:
        return re.sub(r"\D", "", value or "")

    @staticmethod
    def _document_candidates(document: str) -> set[str]:
        candidates = {document}
        if len(document) == 11:
            candidates.add(f"{document[:3]}.{document[3:6]}.{document[6:9]}-{document[9:]}")
        if len(document) == 14:
            candidates.add(
                f"{document[:2]}.{document[2:5]}.{document[5:8]}/{document[8:12]}-{document[12:]}"
            )
        return candidates

    async def _commit_preserving_rls(self) -> None:
        """Confirmar a promoção e restaurar o contexto SET LOCAL do tenant."""
        await self.session.commit()
        tenant_id = self.session.info.get("tenant_id")
        bind = self.session.get_bind()
        if tenant_id and bind.dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
