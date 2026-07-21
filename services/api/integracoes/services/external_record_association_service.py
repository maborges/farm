"""Service transversal para associacoes oficiais com sistemas externos."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationHistory,
    ExternalRecordAssociationHistoryEvent,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
)
from integracoes.schemas import (
    ExternalRecordAssociationCreate,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationUpdate,
)


class DuplicateAssociationError(ValueError):
    """Erro funcional para conflitos de duplicidade na associacao externa."""


class ExternalRecordAssociationService:
    """Gerencia a associacao oficial entre registros locais e externos."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_association(
        self,
        payload: ExternalRecordAssociationCreate,
    ) -> ExternalRecordAssociation:
        self._validate_active_requires_local(payload.status, payload.local_record_id)
        existing = await self._find_exact(payload)
        if existing is not None:
            return await self._upsert_exact_match(existing, payload)

        await self.detect_duplicate(
            tenant_id=payload.tenant_id,
            provider_id=payload.provider_id,
            config_id=payload.config_id,
            environment=payload.environment,
            local_entity=payload.local_entity,
            local_record_id=payload.local_record_id,
            external_entity=payload.external_entity,
            external_record_id=payload.external_record_id,
            external_company_id=payload.external_company_id,
            external_branch_id=payload.external_branch_id,
        )

        association = ExternalRecordAssociation(
            tenant_id=payload.tenant_id,
            provider_id=payload.provider_id,
            config_id=payload.config_id,
            feature_id=payload.feature_id,
            environment=payload.environment,
            scope_type=self._enum_value(payload.scope_type),
            scope_id=payload.scope_id,
            external_company_id=payload.external_company_id,
            external_branch_id=payload.external_branch_id,
            local_entity=payload.local_entity,
            local_record_id=payload.local_record_id,
            external_entity=payload.external_entity,
            external_record_id=payload.external_record_id,
            secondary_keys=payload.secondary_keys,
            status=self._enum_value(payload.status),
            origin=self._enum_value(payload.origin),
            confidence=self._enum_value(payload.confidence),
            last_sync_at=payload.last_sync_at,
            last_job_id=payload.last_job_id,
            notes=payload.notes,
            metadata_json=payload.metadata_json,
            created_by_usuario_id=payload.created_by_usuario_id,
        )
        self.db.add(association)
        await self.db.flush()
        await self._record_history(
            association=association,
            event_type=ExternalRecordAssociationHistoryEvent.CREATED.value,
            actor_usuario_id=payload.created_by_usuario_id,
            reason="association_created",
        )
        await self._commit_preserving_rls()
        await self.db.refresh(association)
        return association

    async def update_association(
        self,
        association: ExternalRecordAssociation,
        payload: ExternalRecordAssociationUpdate,
    ) -> ExternalRecordAssociation:
        previous_status = association.status
        updated = False

        for field in (
            "feature_id",
            "external_company_id",
            "external_branch_id",
            "local_entity",
            "local_record_id",
            "secondary_keys",
            "confidence",
            "last_sync_at",
            "last_job_id",
            "notes",
            "metadata_json",
        ):
            value = getattr(payload, field)
            if field == "confidence" and value is not None:
                value = self._enum_value(value)
            if value is not None and getattr(association, field) != value:
                setattr(association, field, value)
                updated = True

        if payload.status is not None and association.status != self._enum_value(payload.status):
            association.status = self._enum_value(payload.status)
            updated = True

        self._validate_active_requires_local(association.status, association.local_record_id)

        if not updated:
            return association

        event_type = self._resolve_status_event(previous_status, association.status)
        await self._record_history(
            association=association,
            event_type=event_type,
            actor_usuario_id=payload.actor_usuario_id,
            reason=payload.reason,
            previous_status=previous_status,
            new_status=association.status,
        )
        await self._commit_preserving_rls()
        await self.db.refresh(association)
        return association

    async def find_local_by_external(
        self,
        *,
        tenant_id: str,
        provider_id: int,
        environment: str,
        external_entity: str,
        external_record_id: str,
        external_company_id: str | None = None,
        external_branch_id: str | None = None,
        config_id: int | None = None,
        status: ExternalRecordAssociationStatus = ExternalRecordAssociationStatus.ACTIVE,
    ) -> ExternalRecordAssociation | None:
        query = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == provider_id,
            ExternalRecordAssociation.environment == environment,
            ExternalRecordAssociation.external_entity == external_entity,
            ExternalRecordAssociation.external_record_id == external_record_id,
            ExternalRecordAssociation.status == status.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if config_id is not None:
            query = query.where(ExternalRecordAssociation.config_id == config_id)
        if external_company_id is not None:
            query = query.where(
                ExternalRecordAssociation.external_company_id == external_company_id
            )
        if external_branch_id is not None:
            query = query.where(ExternalRecordAssociation.external_branch_id == external_branch_id)
        return await self.db.scalar(query.limit(1))

    async def find_external_by_local(
        self,
        *,
        tenant_id: str,
        environment: str,
        local_entity: str,
        local_record_id: str,
        external_entity: str,
        provider_id: int | None = None,
        config_id: int | None = None,
        status: ExternalRecordAssociationStatus = ExternalRecordAssociationStatus.ACTIVE,
    ) -> ExternalRecordAssociation | None:
        query = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.environment == environment,
            ExternalRecordAssociation.local_entity == local_entity,
            ExternalRecordAssociation.local_record_id == local_record_id,
            ExternalRecordAssociation.external_entity == external_entity,
            ExternalRecordAssociation.status == status.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            query = query.where(ExternalRecordAssociation.provider_id == provider_id)
        if config_id is not None:
            query = query.where(ExternalRecordAssociation.config_id == config_id)
        return await self.db.scalar(query.limit(1))

    async def detect_duplicate(
        self,
        *,
        tenant_id: str,
        provider_id: int,
        config_id: int,
        environment: str,
        local_entity: str,
        local_record_id: str,
        external_entity: str,
        external_record_id: str,
        external_company_id: str | None = None,
        external_branch_id: str | None = None,
        ignore_link_id: UUID | None = None,
    ) -> tuple[ExternalRecordAssociation | None, ExternalRecordAssociation | None]:
        external_query = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.provider_id == provider_id,
            ExternalRecordAssociation.config_id == config_id,
            ExternalRecordAssociation.environment == environment,
            ExternalRecordAssociation.external_entity == external_entity,
            ExternalRecordAssociation.external_record_id == external_record_id,
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.ACTIVE.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        local_query = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.config_id == config_id,
            ExternalRecordAssociation.environment == environment,
            ExternalRecordAssociation.local_entity == local_entity,
            ExternalRecordAssociation.local_record_id == local_record_id,
            ExternalRecordAssociation.external_entity == external_entity,
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.ACTIVE.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if external_company_id is not None:
            external_query = external_query.where(
                ExternalRecordAssociation.external_company_id == external_company_id,
            )
        if external_branch_id is not None:
            external_query = external_query.where(
                ExternalRecordAssociation.external_branch_id == external_branch_id,
            )
        if ignore_link_id is not None:
            external_query = external_query.where(ExternalRecordAssociation.id != ignore_link_id)
            local_query = local_query.where(ExternalRecordAssociation.id != ignore_link_id)

        external_duplicate = await self.db.scalar(external_query.limit(1))
        local_duplicate = await self.db.scalar(local_query.limit(1))
        if external_duplicate is not None:
            raise DuplicateAssociationError(
                "Ja existe uma associacao ativa para o identificador externo informado.",
            )
        if local_duplicate is not None:
            raise DuplicateAssociationError(
                "Ja existe uma associacao ativa para o registro local informado.",
            )
        return external_duplicate, local_duplicate

    async def mark_conflict(
        self,
        association: ExternalRecordAssociation,
        *,
        actor_usuario_id: str | None = None,
        reason: str | None = None,
        last_job_id: UUID | None = None,
    ) -> ExternalRecordAssociation:
        previous_status = association.status
        association.status = ExternalRecordAssociationStatus.CONFLICT.value
        association.last_job_id = last_job_id or association.last_job_id
        await self._record_history(
            association=association,
            event_type=ExternalRecordAssociationHistoryEvent.CONFLICT_MARKED.value,
            actor_usuario_id=actor_usuario_id,
            reason=reason,
            previous_status=previous_status,
            new_status=association.status,
        )
        await self._commit_preserving_rls()
        await self.db.refresh(association)
        return association

    async def replace_association(
        self,
        association: ExternalRecordAssociation,
        replacement: ExternalRecordAssociationCreate,
        *,
        actor_usuario_id: str | None = None,
        reason: str | None = None,
    ) -> ExternalRecordAssociation:
        previous_external_record_id = association.external_record_id
        previous_status = association.status
        association.status = ExternalRecordAssociationStatus.SUPERSEDED.value
        await self._record_history(
            association=association,
            event_type=ExternalRecordAssociationHistoryEvent.SUPERSEDED.value,
            actor_usuario_id=actor_usuario_id,
            reason=reason,
            previous_external_record_id=previous_external_record_id,
            new_external_record_id=replacement.external_record_id,
            previous_status=previous_status,
            new_status=association.status,
        )
        await self.db.flush()
        new_association = await self.create_association(replacement)
        return new_association

    async def deactivate_association(
        self,
        association: ExternalRecordAssociation,
        *,
        actor_usuario_id: str | None = None,
        reason: str | None = None,
    ) -> ExternalRecordAssociation:
        previous_status = association.status
        association.status = ExternalRecordAssociationStatus.INACTIVE.value
        await self._record_history(
            association=association,
            event_type=ExternalRecordAssociationHistoryEvent.DEACTIVATED.value,
            actor_usuario_id=actor_usuario_id,
            reason=reason,
            previous_status=previous_status,
            new_status=association.status,
        )
        await self._commit_preserving_rls()
        await self.db.refresh(association)
        return association

    async def reconcile_pending(
        self,
        association: ExternalRecordAssociation,
        payload: ExternalRecordAssociationReconcile,
    ) -> ExternalRecordAssociation:
        previous_status = association.status
        association.status = ExternalRecordAssociationStatus.ACTIVE.value
        association.confidence = self._enum_value(payload.confidence)
        association.last_job_id = payload.last_job_id or association.last_job_id
        if payload.local_entity is not None:
            association.local_entity = payload.local_entity
        if payload.local_record_id is not None:
            association.local_record_id = payload.local_record_id
        if payload.notes is not None:
            association.notes = payload.notes
        self._validate_active_requires_local(association.status, association.local_record_id)
        await self._record_history(
            association=association,
            event_type=ExternalRecordAssociationHistoryEvent.RECONCILED.value,
            actor_usuario_id=payload.actor_usuario_id,
            reason=payload.reason,
            previous_status=previous_status,
            new_status=association.status,
        )
        await self._commit_preserving_rls()
        await self.db.refresh(association)
        return association

    async def list_history(
        self,
        *,
        tenant_id: str,
        link_id: UUID,
    ) -> list[ExternalRecordAssociationHistory]:
        result = await self.db.scalars(
            select(ExternalRecordAssociationHistory)
            .where(
                ExternalRecordAssociationHistory.tenant_id == tenant_id,
                ExternalRecordAssociationHistory.link_id == link_id,
            )
            .order_by(ExternalRecordAssociationHistory.created_at.asc()),
        )
        return list(result)

    async def list_pending_associations(
        self,
        *,
        tenant_id: str,
        provider_id: int | None = None,
        feature_id: int | None = None,
        feature_code: str | None = None,
        config_id: int | None = None,
        environment: str | None = None,
        local_entity: str | None = None,
        external_entity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExternalRecordAssociation]:
        stmt = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.PENDING.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.provider_id == provider_id)
        if feature_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.feature_id == feature_id)
        if config_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.config_id == config_id)
        if environment is not None:
            stmt = stmt.where(ExternalRecordAssociation.environment == environment)
        if local_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.local_entity == local_entity)
        if external_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.external_entity == external_entity)
        if feature_code is not None:
            stmt = stmt.join(
                IntegrationFeature,
                ExternalRecordAssociation.feature_id == IntegrationFeature.id,
            ).where(IntegrationFeature.codigo == feature_code)
        stmt = (
            stmt.order_by(ExternalRecordAssociation.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.scalars(stmt)
        return list(result)

    async def count_pending_associations(
        self,
        *,
        tenant_id: str,
        provider_id: int | None = None,
        feature_id: int | None = None,
        feature_code: str | None = None,
        config_id: int | None = None,
        environment: str | None = None,
        local_entity: str | None = None,
        external_entity: str | None = None,
    ) -> int:
        stmt = select(func.count(ExternalRecordAssociation.id)).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.status == ExternalRecordAssociationStatus.PENDING.value,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.provider_id == provider_id)
        if feature_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.feature_id == feature_id)
        if config_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.config_id == config_id)
        if environment is not None:
            stmt = stmt.where(ExternalRecordAssociation.environment == environment)
        if local_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.local_entity == local_entity)
        if external_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.external_entity == external_entity)
        if feature_code is not None:
            stmt = stmt.join(
                IntegrationFeature,
                ExternalRecordAssociation.feature_id == IntegrationFeature.id,
            ).where(IntegrationFeature.codigo == feature_code)

        result = await self.db.scalar(stmt)
        return result or 0

    async def list_associations(
        self,
        *,
        tenant_id: str,
        provider_id: int | None = None,
        feature_id: int | None = None,
        feature_code: str | None = None,
        config_id: int | None = None,
        environment: str | None = None,
        local_entity: str | None = None,
        external_entity: str | None = None,
        status: ExternalRecordAssociationStatus | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExternalRecordAssociation]:
        stmt = self._base_query().where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.provider_id == provider_id)
        if feature_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.feature_id == feature_id)
        if config_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.config_id == config_id)
        if environment is not None:
            stmt = stmt.where(ExternalRecordAssociation.environment == environment)
        if local_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.local_entity == local_entity)
        if external_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.external_entity == external_entity)
        if status is not None:
            stmt = stmt.where(ExternalRecordAssociation.status == self._enum_value(status))
        if feature_code is not None:
            stmt = stmt.join(
                IntegrationFeature,
                ExternalRecordAssociation.feature_id == IntegrationFeature.id,
            ).where(IntegrationFeature.codigo == feature_code)

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ExternalRecordAssociation.external_record_id.ilike(search_term),
                    ExternalRecordAssociation.local_record_id.ilike(search_term),
                )
            )

        stmt = (
            stmt.order_by(ExternalRecordAssociation.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.scalars(stmt)
        return list(result)

    async def count_associations(
        self,
        *,
        tenant_id: str,
        provider_id: int | None = None,
        feature_id: int | None = None,
        feature_code: str | None = None,
        config_id: int | None = None,
        environment: str | None = None,
        local_entity: str | None = None,
        external_entity: str | None = None,
        status: ExternalRecordAssociationStatus | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count(ExternalRecordAssociation.id)).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.provider_id == provider_id)
        if feature_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.feature_id == feature_id)
        if config_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.config_id == config_id)
        if environment is not None:
            stmt = stmt.where(ExternalRecordAssociation.environment == environment)
        if local_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.local_entity == local_entity)
        if external_entity is not None:
            stmt = stmt.where(ExternalRecordAssociation.external_entity == external_entity)
        if status is not None:
            stmt = stmt.where(ExternalRecordAssociation.status == self._enum_value(status))
        if feature_code is not None:
            stmt = stmt.join(
                IntegrationFeature,
                ExternalRecordAssociation.feature_id == IntegrationFeature.id,
            ).where(IntegrationFeature.codigo == feature_code)

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ExternalRecordAssociation.external_record_id.ilike(search_term),
                    ExternalRecordAssociation.local_record_id.ilike(search_term),
                )
            )

        result = await self.db.scalar(stmt)
        return result or 0

    async def get_association_summary(
        self,
        *,
        tenant_id: str,
        provider_id: int | None = None,
        config_id: int | None = None,
        environment: str | None = None,
    ) -> dict[str, int]:
        stmt = select(
            ExternalRecordAssociation.status, func.count(ExternalRecordAssociation.id)
        ).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if provider_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.provider_id == provider_id)
        if config_id is not None:
            stmt = stmt.where(ExternalRecordAssociation.config_id == config_id)
        if environment is not None:
            stmt = stmt.where(ExternalRecordAssociation.environment == environment)

        stmt = stmt.group_by(ExternalRecordAssociation.status)

        result = await self.db.execute(stmt)
        summary = {status.value: 0 for status in ExternalRecordAssociationStatus}

        for row_status, count in result:
            summary[row_status] = count

        summary["TOTAL"] = sum(summary.values())
        return summary

    def _base_query(self) -> Select[tuple[ExternalRecordAssociation]]:
        return select(ExternalRecordAssociation)

    async def _find_exact(
        self,
        payload: ExternalRecordAssociationCreate,
    ) -> ExternalRecordAssociation | None:
        query = self._base_query().where(
            ExternalRecordAssociation.tenant_id == payload.tenant_id,
            ExternalRecordAssociation.provider_id == payload.provider_id,
            ExternalRecordAssociation.config_id == payload.config_id,
            ExternalRecordAssociation.environment == payload.environment,
            ExternalRecordAssociation.local_entity == payload.local_entity,
            ExternalRecordAssociation.external_entity == payload.external_entity,
            ExternalRecordAssociation.external_record_id == payload.external_record_id,
            ExternalRecordAssociation.deleted_at.is_(None),
        )
        if payload.local_record_id is None:
            query = query.where(ExternalRecordAssociation.local_record_id.is_(None))
        else:
            query = query.where(
                ExternalRecordAssociation.local_record_id == payload.local_record_id
            )
        company_match = self._optional_match(
            ExternalRecordAssociation.external_company_id,
            payload.external_company_id,
        )
        branch_match = self._optional_match(
            ExternalRecordAssociation.external_branch_id,
            payload.external_branch_id,
        )
        query = query.where(company_match, branch_match)
        return await self.db.scalar(query.limit(1))

    async def _upsert_exact_match(
        self,
        association: ExternalRecordAssociation,
        payload: ExternalRecordAssociationCreate,
    ) -> ExternalRecordAssociation:
        previous_status = association.status
        event_type: str | None = None
        payload_status = self._enum_value(payload.status)
        if association.status != payload_status:
            association.status = payload_status
            event_type = self._resolve_status_event(previous_status, association.status)

        mutable_fields = {
            "feature_id": payload.feature_id,
            "local_entity": payload.local_entity,
            "local_record_id": payload.local_record_id,
            "secondary_keys": payload.secondary_keys,
            "confidence": self._enum_value(payload.confidence),
            "last_sync_at": payload.last_sync_at,
            "last_job_id": payload.last_job_id,
            "notes": payload.notes,
            "metadata_json": payload.metadata_json,
            "external_company_id": payload.external_company_id,
            "external_branch_id": payload.external_branch_id,
        }
        updated = event_type is not None
        for field, value in mutable_fields.items():
            if value is not None and getattr(association, field) != value:
                setattr(association, field, value)
                updated = True

        self._validate_active_requires_local(association.status, association.local_record_id)
        if updated:
            await self._record_history(
                association=association,
                event_type=event_type or ExternalRecordAssociationHistoryEvent.UPDATED.value,
                actor_usuario_id=payload.created_by_usuario_id,
                reason="association_upserted",
                previous_status=previous_status,
                new_status=association.status,
            )
            await self._commit_preserving_rls()
            await self.db.refresh(association)
        return association

    async def _record_history(
        self,
        *,
        association: ExternalRecordAssociation,
        event_type: str,
        actor_usuario_id: str | None = None,
        reason: str | None = None,
        previous_external_record_id: str | None = None,
        new_external_record_id: str | None = None,
        previous_status: str | None = None,
        new_status: str | None = None,
    ) -> None:
        history = ExternalRecordAssociationHistory(
            tenant_id=association.tenant_id,
            link_id=association.id,
            event_type=event_type,
            previous_external_record_id=previous_external_record_id,
            new_external_record_id=new_external_record_id or association.external_record_id,
            previous_status=previous_status,
            new_status=new_status or association.status,
            job_id=association.last_job_id,
            actor_usuario_id=actor_usuario_id,
            reason=reason,
            details_payload={
                "provider_id": association.provider_id,
                "config_id": association.config_id,
                "environment": association.environment,
                "local_entity": association.local_entity,
                "local_record_id": association.local_record_id,
                "external_entity": association.external_entity,
            },
        )
        self.db.add(history)
        await self.db.flush()

    async def _commit_preserving_rls(self) -> None:
        """Confirma alterações e restaura o SET LOCAL usado pelo isolamento tenant."""
        await self.db.commit()
        tenant_id = self.db.info.get("tenant_id")
        bind = self.db.get_bind()
        if tenant_id and bind.dialect.name == "postgresql":
            await self.db.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )

    def _resolve_status_event(self, previous_status: str, new_status: str) -> str:
        if previous_status == ExternalRecordAssociationStatus.INACTIVE.value and new_status == (
            ExternalRecordAssociationStatus.ACTIVE.value
        ):
            return ExternalRecordAssociationHistoryEvent.REACTIVATED.value
        if new_status == ExternalRecordAssociationStatus.CONFLICT.value:
            return ExternalRecordAssociationHistoryEvent.CONFLICT_MARKED.value
        if new_status == ExternalRecordAssociationStatus.INACTIVE.value:
            return ExternalRecordAssociationHistoryEvent.DEACTIVATED.value
        return ExternalRecordAssociationHistoryEvent.UPDATED.value

    def _optional_match(self, column, value: str | None):
        if value is None:
            return or_(column.is_(None), column == "")
        return and_(column == value)

    def _enum_value(self, value):
        return getattr(value, "value", value)

    def _validate_active_requires_local(self, status, local_record_id: str | None) -> None:
        if (
            self._enum_value(status) == ExternalRecordAssociationStatus.ACTIVE.value
            and not local_record_id
        ):
            raise ValueError("Associacao ativa exige local_record_id resolvido.")
