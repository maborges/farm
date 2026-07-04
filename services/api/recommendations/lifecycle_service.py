from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from core.services.audit_service import _serialize, write_audit_log

from .enums import (
    ACTIVE_RECOMMENDATION_STATUSES,
    RecommendationLifecycleActionType,
    RecommendationStatus,
)
from .models import RecommendationLifecycleEvent, RecommendationResult
from .schemas import RecommendationCandidate


class RecommendationLifecycleService:
    """Lifecycle service for canonical recommendation results."""

    SOURCE_CHANNEL = "ENGINE"

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def create_or_update_recommendation(
        self,
        candidate: RecommendationCandidate,
    ) -> RecommendationResult:
        """Create a new active recommendation or update the matching active one."""
        self._ensure_tenant(candidate.tenant_id)
        await self._set_rls_context()

        existing = await self._find_active_recommendation(candidate.dedupe_key)
        if existing:
            before = _serialize(existing)
            self._merge_recommendation(existing, candidate)
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            await write_audit_log(
                self.session,
                tenant_id=self.tenant_id,
                user_id=None,
                action="update",
                resource=RecommendationResult.__tablename__,
                resource_id=existing.id,
                payload_before=before,
                payload_after=_serialize(existing),
            )
            return existing

        recommendation = RecommendationResult(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            unidade_produtiva_id=candidate.unidade_produtiva_id,
            domain=candidate.domain.value,
            status=RecommendationStatus.CREATED.value,
            priority=candidate.priority.value,
            source_type=candidate.source_type.value,
            action_type=candidate.action_type.value,
            provider_name=candidate.provider_name,
            rule_code=candidate.rule_code,
            scope_type=candidate.scope_type,
            scope_id=candidate.scope_id,
            title=candidate.title,
            summary=candidate.summary,
            rationale=candidate.rationale,
            dedupe_key=candidate.dedupe_key,
            source_signal_ids=[str(value) for value in candidate.source_signal_ids],
            confidence=candidate.confidence,
            action_label=candidate.action_label,
            action_target=candidate.action_target,
            context=candidate.context,
            expires_at=candidate.expires_at,
        )
        self.session.add(recommendation)
        await self.session.flush()
        await self._create_lifecycle_event(
            recommendation=recommendation,
            action_type=RecommendationLifecycleActionType.CREATE,
            previous_status=RecommendationStatus.CREATED,
            new_status=RecommendationStatus.CREATED,
            payload={
                "dedupe_key": candidate.dedupe_key,
                "provider_name": candidate.provider_name,
                "rule_code": candidate.rule_code,
                "created_by": self.SOURCE_CHANNEL,
            },
            actor_id=None,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=None,
            action="create",
            resource=RecommendationResult.__tablename__,
            resource_id=recommendation.id,
            payload_before=None,
            payload_after=_serialize(recommendation),
        )
        return recommendation

    async def mark_viewed(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.VIEWED,
            action_type=RecommendationLifecycleActionType.VIEW,
            terminal_field="viewed_at",
        )

    async def accept(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.ACCEPTED,
            action_type=RecommendationLifecycleActionType.ACCEPT,
            terminal_field="accepted_at",
        )

    async def dismiss(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.DISMISSED,
            action_type=RecommendationLifecycleActionType.DISMISS,
            terminal_field="dismissed_at",
            payload={"reason": reason} if reason else None,
        )

    async def postpone(
        self,
        recommendation_id: uuid.UUID,
        until: datetime,
        actor_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> RecommendationResult:
        if until <= datetime.now(timezone.utc):
            raise BusinessRuleError("Postponed until must be in the future.")
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.POSTPONED,
            action_type=RecommendationLifecycleActionType.POSTPONE,
            terminal_field="postponed_until",
            terminal_value=until,
            payload={"reason": reason, "until": until.isoformat()},
        )

    async def execute(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        execution_note: str | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.EXECUTED,
            action_type=RecommendationLifecycleActionType.EXECUTE,
            terminal_field="executed_at",
            payload={"execution_note": execution_note} if execution_note else None,
        )

    async def expire(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        automatic: bool = False,
    ) -> RecommendationResult:
        status = (
            RecommendationStatus.AUTO_EXPIRED if automatic else RecommendationStatus.EXPIRED
        )
        action = (
            RecommendationLifecycleActionType.AUTO_EXPIRE
            if automatic
            else RecommendationLifecycleActionType.EXPIRE
        )
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=status,
            action_type=action,
            terminal_field="expired_at",
        )

    async def supersede(
        self,
        recommendation_id: uuid.UUID,
        superseded_by_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.SUPERSEDED,
            action_type=RecommendationLifecycleActionType.SUPERSEDE,
            terminal_field="superseded_at",
            extra_updates={"superseded_by_id": superseded_by_id},
            payload={"superseded_by_id": str(superseded_by_id)},
        )

    async def reopen(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> RecommendationResult:
        return await self._transition(
            recommendation_id,
            actor_id,
            new_status=RecommendationStatus.REOPENED,
            action_type=RecommendationLifecycleActionType.REOPEN,
        )

    async def _transition(
        self,
        recommendation_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        *,
        new_status: RecommendationStatus,
        action_type: RecommendationLifecycleActionType,
        terminal_field: str | None = None,
        terminal_value: datetime | None = None,
        extra_updates: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
    ) -> RecommendationResult:
        await self._set_rls_context()
        recommendation = await self._get_recommendation(recommendation_id)
        previous_status = RecommendationStatus(recommendation.status)
        if previous_status == new_status:
            return recommendation
        self._ensure_transition_allowed(previous_status, new_status)

        before = _serialize(recommendation)
        recommendation.status = new_status.value
        recommendation.updated_at = datetime.now(timezone.utc)
        if terminal_field:
            setattr(
                recommendation,
                terminal_field,
                terminal_value or datetime.now(timezone.utc),
            )
        if extra_updates:
            for key, value in extra_updates.items():
                setattr(recommendation, key, value)
        await self.session.flush()
        await self._create_lifecycle_event(
            recommendation=recommendation,
            action_type=action_type,
            previous_status=previous_status,
            new_status=new_status,
            payload=payload,
            actor_id=actor_id,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=actor_id,
            action="update",
            resource=RecommendationResult.__tablename__,
            resource_id=recommendation.id,
            payload_before=before,
            payload_after=_serialize(recommendation),
        )
        return recommendation

    async def _create_lifecycle_event(
        self,
        *,
        recommendation: RecommendationResult,
        action_type: RecommendationLifecycleActionType,
        previous_status: RecommendationStatus,
        new_status: RecommendationStatus,
        payload: dict[str, object] | None,
        actor_id: uuid.UUID | None,
    ) -> RecommendationLifecycleEvent:
        event = RecommendationLifecycleEvent(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            recommendation_id=recommendation.id,
            actor_id=actor_id,
            action_type=action_type.value,
            previous_status=previous_status.value,
            new_status=new_status.value,
            payload=payload,
            source_channel=self.SOURCE_CHANNEL,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def _find_active_recommendation(
        self,
        dedupe_key: str,
    ) -> RecommendationResult | None:
        stmt = select(RecommendationResult).where(
            RecommendationResult.tenant_id == self.tenant_id,
            RecommendationResult.dedupe_key == dedupe_key,
            RecommendationResult.status.in_(ACTIVE_RECOMMENDATION_STATUSES),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _get_recommendation(
        self,
        recommendation_id: uuid.UUID,
    ) -> RecommendationResult:
        stmt = select(RecommendationResult).where(
            RecommendationResult.id == recommendation_id,
            RecommendationResult.tenant_id == self.tenant_id,
        )
        recommendation = (await self.session.execute(stmt)).scalars().first()
        if recommendation is None:
            raise EntityNotFoundError(f"Recommendation {recommendation_id} not found.")
        return recommendation

    @staticmethod
    def _merge_recommendation(
        recommendation: RecommendationResult,
        candidate: RecommendationCandidate,
    ) -> None:
        recommendation.unidade_produtiva_id = candidate.unidade_produtiva_id
        recommendation.domain = candidate.domain.value
        recommendation.priority = candidate.priority.value
        recommendation.source_type = candidate.source_type.value
        recommendation.action_type = candidate.action_type.value
        recommendation.provider_name = candidate.provider_name
        recommendation.rule_code = candidate.rule_code
        recommendation.scope_type = candidate.scope_type
        recommendation.scope_id = candidate.scope_id
        recommendation.title = candidate.title
        recommendation.summary = candidate.summary
        recommendation.rationale = candidate.rationale
        recommendation.source_signal_ids = [str(value) for value in candidate.source_signal_ids]
        recommendation.confidence = candidate.confidence
        recommendation.action_label = candidate.action_label
        recommendation.action_target = candidate.action_target
        recommendation.context = candidate.context
        recommendation.expires_at = candidate.expires_at

    def _ensure_tenant(self, candidate_tenant_id: uuid.UUID) -> None:
        if candidate_tenant_id != self.tenant_id:
            raise TenantViolationError(
                "Recommendation candidate belongs to another tenant.",
                tenant_id=self.tenant_id,
            )

    async def _set_rls_context(self) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )

    @staticmethod
    def _ensure_transition_allowed(
        previous_status: RecommendationStatus,
        new_status: RecommendationStatus,
    ) -> None:
        allowed = {
            RecommendationStatus.CREATED: {
                RecommendationStatus.VIEWED,
                RecommendationStatus.ACCEPTED,
                RecommendationStatus.DISMISSED,
                RecommendationStatus.POSTPONED,
                RecommendationStatus.EXECUTED,
                RecommendationStatus.EXPIRED,
                RecommendationStatus.AUTO_EXPIRED,
                RecommendationStatus.SUPERSEDED,
            },
            RecommendationStatus.VIEWED: {
                RecommendationStatus.ACCEPTED,
                RecommendationStatus.DISMISSED,
                RecommendationStatus.POSTPONED,
                RecommendationStatus.EXECUTED,
                RecommendationStatus.EXPIRED,
                RecommendationStatus.AUTO_EXPIRED,
                RecommendationStatus.SUPERSEDED,
            },
            RecommendationStatus.ACCEPTED: {
                RecommendationStatus.EXECUTED,
                RecommendationStatus.POSTPONED,
                RecommendationStatus.DISMISSED,
                RecommendationStatus.SUPERSEDED,
            },
            RecommendationStatus.POSTPONED: {
                RecommendationStatus.REOPENED,
                RecommendationStatus.ACCEPTED,
                RecommendationStatus.DISMISSED,
                RecommendationStatus.AUTO_EXPIRED,
                RecommendationStatus.SUPERSEDED,
            },
            RecommendationStatus.DISMISSED: {RecommendationStatus.REOPENED},
            RecommendationStatus.EXPIRED: {RecommendationStatus.REOPENED},
            RecommendationStatus.AUTO_EXPIRED: {RecommendationStatus.REOPENED},
            RecommendationStatus.SUPERSEDED: {RecommendationStatus.REOPENED},
            RecommendationStatus.REOPENED: {
                RecommendationStatus.VIEWED,
                RecommendationStatus.ACCEPTED,
                RecommendationStatus.DISMISSED,
                RecommendationStatus.POSTPONED,
                RecommendationStatus.EXECUTED,
                RecommendationStatus.EXPIRED,
                RecommendationStatus.AUTO_EXPIRED,
                RecommendationStatus.SUPERSEDED,
            },
            RecommendationStatus.EXECUTED: set(),
        }
        if new_status not in allowed.get(previous_status, set()):
            raise BusinessRuleError(
                f"Transition from {previous_status.value} to {new_status.value} is not allowed."
            )
