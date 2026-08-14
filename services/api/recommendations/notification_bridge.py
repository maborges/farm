from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from notifications import (
    NotificationChannel,
    NotificationDispatchResult,
    NotificationDispatcher,
    NotificationEvent,
    NotificationPolicy,
    NotificationPriority,
    register_notification_policy,
)

from notificacoes.schemas import NotificacaoCreate
from notificacoes.service import NotificacaoService

from .enums import ACTIVE_RECOMMENDATION_STATUSES, RecommendationPriority

RECOMMENDATION_NOTIFICACAO_TIPO = "RECOMENDACAO"
RECOMMENDATION_NOTIFICACAO_ORIGEM = "recommendation"

RECOMMENDATION_NOTIFICATION_EVENT_TYPE = "recommendations.operational"
RECOMMENDATION_NOTIFICATION_DEDUPE_PREFIX = "recommendation"


class RecommendationOperationalNotificationPolicy(NotificationPolicy):
    """Policy hook reserved for operational recommendations."""

    policy_name = "recommendations.operational"
    event_type = RECOMMENDATION_NOTIFICATION_EVENT_TYPE


@dataclass(slots=True)
class RecommendationNotificationBridgeResult:
    """Outcome returned by the recommendation notification bridge."""

    recommendation_id: UUID | None
    eligible: bool
    reason: str | None = None
    dispatch_result: NotificationDispatchResult | None = None

    @property
    def dispatched(self) -> bool:
        return bool(self.dispatch_result and self.dispatch_result.delivered)


class RecommendationNotificationBridge:
    """Translate persisted recommendations into optional notifications."""

    def __init__(self, dispatcher: NotificationDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or NotificationDispatcher()

    async def notify(
        self,
        recommendation: Any,
        *,
        session: AsyncSession | None = None,
        was_created: bool = True,
    ) -> RecommendationNotificationBridgeResult:
        """Dispatch a notification for an eligible recommendation.

        Além do dispatch via policy engine (email/log), grava a notificação em
        `notificacoes` quando `session` é informada, para que ela apareça no
        sino/WS do frontend — os dois pacotes eram desconectados e recomendações
        nunca chegavam à UI (ver memória project_notifications_dois_pacotes_duplicados).
        """

        recommendation_id = self._recommendation_id(recommendation)
        tenant_id = self._tenant_id(recommendation)
        logger.bind(
            component="recommendation_notification_bridge",
            recommendation_id=str(recommendation_id) if recommendation_id else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            status=getattr(recommendation, "status", None),
            priority=getattr(recommendation, "priority", None),
        ).info("recommendation_notification_bridge_started")

        eligible, reason = self._is_eligible(recommendation, was_created=was_created)
        if not eligible:
            return RecommendationNotificationBridgeResult(
                recommendation_id=recommendation_id,
                eligible=False,
                reason=reason,
            )

        if session is not None and tenant_id is not None:
            try:
                await self._criar_notificacao(session, tenant_id, recommendation)
            except Exception as exc:  # pragma: no cover - defensive isolation
                logger.bind(
                    component="recommendation_notification_bridge",
                    recommendation_id=str(recommendation_id) if recommendation_id else None,
                    tenant_id=str(tenant_id),
                    exception_type=exc.__class__.__name__,
                ).exception("recommendation_notificacao_persist_failed")

        event = self._build_event(recommendation)
        try:
            dispatch_result = await self.dispatcher.dispatch(event)
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.bind(
                component="recommendation_notification_bridge",
                recommendation_id=str(recommendation_id) if recommendation_id else None,
                tenant_id=str(tenant_id) if tenant_id is not None else None,
                exception_type=exc.__class__.__name__,
            ).exception("recommendation_notification_dispatch_failed")
            return RecommendationNotificationBridgeResult(
                recommendation_id=recommendation_id,
                eligible=True,
                reason="dispatch_failed",
            )

        logger.bind(
            component="recommendation_notification_bridge",
            recommendation_id=str(recommendation_id) if recommendation_id else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            notification_id=str(dispatch_result.notification_id),
            status=dispatch_result.status.value,
            delivered=dispatch_result.delivered,
            skipped=dispatch_result.skipped,
            failed=dispatch_result.failed,
            reason=dispatch_result.error,
        ).info("recommendation_notification_bridge_finished")
        return RecommendationNotificationBridgeResult(
            recommendation_id=recommendation_id,
            eligible=True,
            reason=dispatch_result.error,
            dispatch_result=dispatch_result,
        )

    async def _criar_notificacao(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        recommendation: Any,
    ) -> None:
        svc = NotificacaoService(session, tenant_id)
        await svc.criar_sem_duplicar(
            NotificacaoCreate(
                tipo=RECOMMENDATION_NOTIFICACAO_TIPO,
                titulo=self._subject(recommendation),
                mensagem=self._message(recommendation),
                nivel="DANGER" if self._priority_value(recommendation) == RecommendationPriority.URGENT.value else "WARNING",
                origem=RECOMMENDATION_NOTIFICACAO_ORIGEM,
                origem_id=str(self._recommendation_id(recommendation)),
                meta={
                    "recommendation_id": str(self._recommendation_id(recommendation)),
                    "recommendation_domain": self._domain_value(recommendation),
                    "rule_code": getattr(recommendation, "rule_code", None),
                    "acoes": [
                        {"label": "Aceitar", "acao": "accept", "endpoint": f"/recommendations/{self._recommendation_id(recommendation)}/accept", "method": "POST"},
                        {"label": "Adiar", "acao": "postpone", "endpoint": f"/recommendations/{self._recommendation_id(recommendation)}/postpone", "method": "POST"},
                        {"label": "Descartar", "acao": "dismiss", "endpoint": f"/recommendations/{self._recommendation_id(recommendation)}/dismiss", "method": "POST"},
                    ],
                },
            )
        )

    def _is_eligible(
        self,
        recommendation: Any,
        *,
        was_created: bool,
    ) -> tuple[bool, str | None]:
        if not was_created:
            return False, "not_a_new_recommendation"
        if not self._is_active(recommendation):
            return False, "status_not_eligible"
        if not self._is_high_priority(recommendation):
            return False, "priority_not_eligible"
        if self._is_expired(recommendation):
            return False, "expired"
        if self._tenant_id(recommendation) is None:
            return False, "tenant_missing"
        if not self._dedupe_key(recommendation):
            return False, "dedupe_key_missing"
        return True, None

    def _build_event(self, recommendation: Any) -> NotificationEvent:
        notification_priority = self._notification_priority(recommendation)
        recipients = self._notification_recipients(recommendation)
        preferred_channels = (
            [NotificationChannel.EMAIL.value, NotificationChannel.LOG.value]
            if recipients
            else [NotificationChannel.LOG.value]
        )
        dedupe_key = self._stable_dedupe_key(recommendation)
        metadata = {
            "event_type": RECOMMENDATION_NOTIFICATION_EVENT_TYPE,
            "recommendation_id": str(self._recommendation_id(recommendation)),
            "recommendation_status": self._status_value(recommendation),
            "recommendation_priority": self._priority_value(recommendation),
            "recommendation_domain": self._domain_value(recommendation),
            "provider_name": getattr(recommendation, "provider_name", None),
            "rule_code": getattr(recommendation, "rule_code", None),
            "scope_type": getattr(recommendation, "scope_type", None),
            "scope_id": getattr(recommendation, "scope_id", None),
            "dedupe_key": dedupe_key,
            "notification_preferences": {
                "preferred_channels": preferred_channels,
                "priority": notification_priority.value,
                "dedupe_key": dedupe_key,
                "recipients": recipients,
            },
        }
        return NotificationEvent(
            tenant_id=self._tenant_id(recommendation),
            unidade_produtiva_id=getattr(recommendation, "unidade_produtiva_id", None),
            channel=NotificationChannel.EMAIL,
            priority=notification_priority,
            subject=self._subject(recommendation),
            message=self._message(recommendation),
            source_type="RECOMMENDATION_RESULT",
            source_id=str(self._recommendation_id(recommendation)),
            correlation_id=self._uuid_or_none(
                getattr(recommendation, "correlation_id", None)
            ),
            causation_id=self._uuid_or_none(
                getattr(recommendation, "causation_id", None)
            ),
            metadata=metadata,
        )

    @staticmethod
    def _subject(recommendation: Any) -> str:
        title = str(getattr(recommendation, "title", "")).strip()
        return title or "Recomendação operacional"

    def _message(self, recommendation: Any) -> str:
        summary = str(getattr(recommendation, "summary", "")).strip()
        rationale = str(getattr(recommendation, "rationale", "")).strip()
        details = [item for item in (summary, rationale) if item]
        if details:
            return "\n\n".join(details)
        return "Recomendação operacional de alta prioridade disponível."

    @staticmethod
    def _recommendation_id(recommendation: Any) -> UUID | None:
        return RecommendationNotificationBridge._uuid_or_none(
            getattr(recommendation, "id", None)
        )

    @staticmethod
    def _tenant_id(recommendation: Any) -> UUID | None:
        return RecommendationNotificationBridge._uuid_or_none(
            getattr(recommendation, "tenant_id", None)
        )

    def _stable_dedupe_key(self, recommendation: Any) -> str:
        dedupe_key = self._dedupe_key(recommendation)
        return f"{RECOMMENDATION_NOTIFICATION_DEDUPE_PREFIX}:{dedupe_key}"

    @staticmethod
    def _dedupe_key(recommendation: Any) -> str:
        return str(getattr(recommendation, "dedupe_key", "")).strip()

    def _notification_priority(self, recommendation: Any) -> NotificationPriority:
        priority = self._priority_value(recommendation)
        if priority == RecommendationPriority.URGENT.value:
            return NotificationPriority.CRITICAL
        return NotificationPriority.HIGH

    @staticmethod
    def _priority_value(recommendation: Any) -> str:
        return str(getattr(recommendation, "priority", "")).strip().upper()

    @staticmethod
    def _domain_value(recommendation: Any) -> str | None:
        domain = getattr(recommendation, "domain", None)
        if domain is None:
            return None
        return str(getattr(domain, "value", domain))

    @staticmethod
    def _status_value(recommendation: Any) -> str:
        status = getattr(recommendation, "status", "")
        return str(getattr(status, "value", status)).strip().upper()

    def _is_active(self, recommendation: Any) -> bool:
        status = self._status_value(recommendation)
        return status in ACTIVE_RECOMMENDATION_STATUSES

    def _is_high_priority(self, recommendation: Any) -> bool:
        return self._priority_value(recommendation) in {
            RecommendationPriority.HIGH.value,
            RecommendationPriority.URGENT.value,
        }

    def _is_expired(self, recommendation: Any) -> bool:
        expires_at = getattr(recommendation, "expires_at", None)
        if expires_at is None:
            return False
        if not isinstance(expires_at, datetime):
            return False
        current = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= current

    @staticmethod
    def _notification_recipients(recommendation: Any) -> list[str]:
        context = getattr(recommendation, "context", None)
        if not isinstance(context, dict):
            return []
        raw_recipients = context.get("notification_recipients")
        if not isinstance(raw_recipients, (list, tuple, set)):
            return []
        recipients: list[str] = []
        for value in raw_recipients:
            recipient = str(value).strip()
            if recipient:
                recipients.append(recipient)
        return recipients

    @staticmethod
    def _uuid_or_none(value: Any) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None


recommendation_notification_bridge = RecommendationNotificationBridge()
register_notification_policy(RecommendationOperationalNotificationPolicy())
