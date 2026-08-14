from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import case, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from core.services.audit_service import _serialize, write_audit_log
from alert_engine.models import (
    ACTIVE_ALERT_STATUSES,
    AlertLifecycleEvent,
    AlertStatus,
    Category,
    Domain,
    LifecycleActionType,
    Priority,
    Severity,
    OperationalAlert,
)
from alert_engine.schemas import (
    AlertQueryResponse,
    AlertSummary,
    AlertSummaryByDomain,
    OperationalAlertCreate,
    OperationalAlertResponse,
)


class AlertLifecycleService:
    """Lifecycle service for canonical operational alerts."""

    SOURCE_CHANNEL = "ENGINE"
    DEFAULT_QUERY_LIMIT = 100
    DEFAULT_SUMMARY_TOP_LIMIT = 5
    SEVERITY_ORDER = {
        Severity.EMERGENCY.value: 4,
        Severity.CRITICAL.value: 3,
        Severity.WARNING.value: 2,
        Severity.INFO.value: 1,
    }
    PRIORITY_ORDER = {
        Priority.URGENT.value: 4,
        Priority.HIGH.value: 3,
        Priority.NORMAL.value: 2,
        Priority.LOW.value: 1,
    }

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def create_or_update_alert(self, obj_in: OperationalAlertCreate) -> OperationalAlert:
        """Creates a new active alert or updates the existing one matching the dedupe key.

        Args:
            obj_in: Canonical alert payload.

        Returns:
            The created or updated alert row.

        Raises:
            TenantViolationError: If the payload tenant differs from the service tenant.
            BusinessRuleError: If the payload attempts to create a non-open alert.
        """
        self._ensure_tenant(obj_in.tenant_id)
        await self._set_rls_context()
        if obj_in.status != AlertStatus.OPEN:
            raise BusinessRuleError("Novos alertas devem iniciar em OPEN.")

        existing = await self._find_active_alert(obj_in.dedupe_key)
        if existing:
            before = _serialize(existing)
            self._merge_alert(existing, obj_in)
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            await write_audit_log(
                self.session,
                tenant_id=self.tenant_id,
                user_id=None,
                action="update",
                resource=OperationalAlert.__tablename__,
                resource_id=existing.id,
                payload_before=before,
                payload_after=_serialize(existing),
            )
            return existing

        alert = OperationalAlert(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            unidade_produtiva_id=obj_in.unidade_produtiva_id,
            domain=obj_in.domain.value,
            category=obj_in.category.value,
            title=obj_in.title,
            message=obj_in.message,
            severity=obj_in.severity.value,
            priority=obj_in.priority.value,
            status=AlertStatus.OPEN.value,
            confidence=obj_in.confidence,
            trigger_type=obj_in.trigger_type.value,
            source_type=obj_in.source_type,
            source_id=obj_in.source_id,
            source_event_ids=[str(value) for value in obj_in.source_event_ids],
            source_indicator_ids=[str(value) for value in obj_in.source_indicator_ids],
            dedupe_key=obj_in.dedupe_key,
            action_label=obj_in.action_label,
            action_url=obj_in.action_url,
            context=obj_in.context,
            expires_at=obj_in.expires_at,
            acknowledged_at=obj_in.acknowledged_at,
            resolved_at=obj_in.resolved_at,
            acknowledged_by=obj_in.acknowledged_by,
            resolved_by=obj_in.resolved_by,
        )
        self.session.add(alert)
        await self.session.flush()
        await self._create_lifecycle_event(
            alert=alert,
            action_type=LifecycleActionType.CREATE,
            previous_status=AlertStatus.OPEN,
            new_status=AlertStatus.OPEN,
            payload={
                "dedupe_key": obj_in.dedupe_key,
                "source_type": obj_in.source_type,
                "source_id": obj_in.source_id,
                "source_event_ids": [str(value) for value in obj_in.source_event_ids],
                "source_indicator_ids": [str(value) for value in obj_in.source_indicator_ids],
                "created_by": self.SOURCE_CHANNEL,
            },
            actor_id=None,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=None,
            action="create",
            resource=OperationalAlert.__tablename__,
            resource_id=alert.id,
            payload_before=None,
            payload_after=_serialize(alert),
        )
        logger.debug("Alert created with dedupe key {}", obj_in.dedupe_key)
        await self._notificar_usuarios(alert)
        return alert

    async def _notificar_usuarios(self, alert: OperationalAlert) -> None:
        """Espelha o alerta recém-criado em `Notificacao` para aparecer no sino do frontend.

        `alert_engine/` grava em `operational_alerts`, visível só no card-resumo
        do dashboard (`GET /alerts/summary`) — sem isso os alertas nunca chegam
        ao usuário via WS/sino. Só na criação (não em update de alerta já ativo),
        para não reabrir notificação de algo que já estava sendo tratado.

        Usa uma sessão própria (`async_session_maker`), não `self.session`: o
        chamador (scheduler/dispatcher) pode estar dentro de um SAVEPOINT
        (`session.begin_nested()`, usado no modo `dry_run`) e
        `NotificacaoService.criar_e_push` faz `commit()` internamente — chamar
        commit() dentro do savepoint do caller quebra a transação dele
        (`ResourceClosedError` observado em produção deste fix). Trade-off aceito:
        em `dry_run` (preview, sem persistir o alerta de verdade) a notificação
        ainda seria criada — não crítico hoje porque `dry_run` só roda sob demanda,
        não no scheduler periódico.
        """
        from core.database import async_session_maker
        from notificacoes.schemas import NotificacaoCreate
        from notificacoes.service import NotificacaoService

        nivel_map = {
            Severity.INFO.value: "INFO",
            Severity.WARNING.value: "WARNING",
            Severity.CRITICAL.value: "DANGER",
            Severity.EMERGENCY.value: "DANGER",
        }
        try:
            meta = {"alert_id": str(alert.id), "dedupe_key": alert.dedupe_key, "domain": alert.domain}
            acoes = self._acoes_para_alerta(alert)
            if acoes:
                meta["acoes"] = acoes
            async with async_session_maker() as bg_session:
                svc = NotificacaoService(bg_session, self.tenant_id)
                await svc.criar_sem_duplicar(
                    NotificacaoCreate(
                        tipo=alert.source_type,
                        titulo=alert.title,
                        mensagem=alert.message,
                        nivel=nivel_map.get(alert.severity, "INFO"),
                        origem="alert_engine",
                        origem_id=alert.source_id or str(alert.id),
                        meta=meta,
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.exception(f"Falha ao espelhar alert_engine alert {alert.id} em Notificacao: {exc}")

    @staticmethod
    def _acoes_para_alerta(alert: OperationalAlert) -> list[dict] | None:
        """Mapa fixo de ações one-click por `source_type`, quando a permissão
        já é resolvível em `notificacoes/service.py::_filtrar_acoes_por_permissao`.

        Não confiável para todo `source_type` — só os mapeados aqui ganham botão;
        os demais aparecem só como texto informativo (comportamento anterior).
        """
        if alert.source_type == "AGRICULTURA_OPERACAO_ATRASADA" and alert.source_id:
            nova_data = (date.today() + timedelta(days=3)).isoformat()
            return [
                {
                    "label": "Adiar +3 dias",
                    "acao": "adiar",
                    "endpoint": f"/operacoes/{alert.source_id}",
                    "method": "PATCH",
                    "body": {"data_prevista": nova_data},
                }
            ]
        return None

    async def acknowledge_alert(
        self,
        alert_id: uuid.UUID,
        actor_id: uuid.UUID,
        comment: str | None = None,
    ) -> OperationalAlert:
        await self._set_rls_context()
        alert = await self._get_alert(alert_id)
        if alert.status not in {AlertStatus.OPEN.value, AlertStatus.SNOOZED.value}:
            raise BusinessRuleError("Only OPEN or SNOOZED alerts can be acknowledged.")

        before = _serialize(alert)
        previous_status = AlertStatus(alert.status)
        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = actor_id
        alert.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self._create_lifecycle_event(
            alert=alert,
            action_type=LifecycleActionType.ACKNOWLEDGE,
            previous_status=previous_status,
            new_status=AlertStatus.ACKNOWLEDGED,
            payload={"comment": comment} if comment else None,
            actor_id=actor_id,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=actor_id,
            action="update",
            resource=OperationalAlert.__tablename__,
            resource_id=alert.id,
            payload_before=before,
            payload_after=_serialize(alert),
        )
        return alert

    async def snooze_alert(
        self,
        alert_id: uuid.UUID,
        actor_id: uuid.UUID,
        until: datetime,
        reason: str | None = None,
    ) -> OperationalAlert:
        await self._set_rls_context()
        if until <= datetime.now(timezone.utc):
            raise BusinessRuleError("Snooze must be scheduled in the future.")

        alert = await self._get_alert(alert_id)
        if alert.status not in {AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value}:
            raise BusinessRuleError("Only OPEN or ACKNOWLEDGED alerts can be snoozed.")

        before = _serialize(alert)
        previous_status = AlertStatus(alert.status)
        alert.status = AlertStatus.SNOOZED.value
        alert.expires_at = until
        alert.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self._create_lifecycle_event(
            alert=alert,
            action_type=LifecycleActionType.SNOOZE,
            previous_status=previous_status,
            new_status=AlertStatus.SNOOZED,
            payload={
                "until": until.isoformat(),
                "reason": reason,
            },
            actor_id=actor_id,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=actor_id,
            action="update",
            resource=OperationalAlert.__tablename__,
            resource_id=alert.id,
            payload_before=before,
            payload_after=_serialize(alert),
        )
        return alert

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
        actor_id: uuid.UUID,
        resolution_note: str | None = None,
    ) -> OperationalAlert:
        await self._set_rls_context()
        alert = await self._get_alert(alert_id)
        if alert.status not in {
            AlertStatus.OPEN.value,
            AlertStatus.ACKNOWLEDGED.value,
            AlertStatus.SNOOZED.value,
        }:
            raise BusinessRuleError("Only active alerts can be resolved.")

        before = _serialize(alert)
        previous_status = AlertStatus(alert.status)
        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = actor_id
        alert.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self._create_lifecycle_event(
            alert=alert,
            action_type=LifecycleActionType.RESOLVE,
            previous_status=previous_status,
            new_status=AlertStatus.RESOLVED,
            payload={"resolution_note": resolution_note} if resolution_note else None,
            actor_id=actor_id,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=actor_id,
            action="update",
            resource=OperationalAlert.__tablename__,
            resource_id=alert.id,
            payload_before=before,
            payload_after=_serialize(alert),
        )
        return alert

    async def dismiss_alert(
        self,
        alert_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str | None = None,
    ) -> OperationalAlert:
        await self._set_rls_context()
        alert = await self._get_alert(alert_id)
        if alert.status not in {
            AlertStatus.OPEN.value,
            AlertStatus.ACKNOWLEDGED.value,
            AlertStatus.SNOOZED.value,
        }:
            raise BusinessRuleError("Only active alerts can be dismissed.")

        before = _serialize(alert)
        previous_status = AlertStatus(alert.status)
        alert.status = AlertStatus.CANCELLED.value
        alert.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self._create_lifecycle_event(
            alert=alert,
            action_type=LifecycleActionType.DISMISS,
            previous_status=previous_status,
            new_status=AlertStatus.CANCELLED,
            payload={"reason": reason} if reason else None,
            actor_id=actor_id,
        )
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=actor_id,
            action="update",
            resource=OperationalAlert.__tablename__,
            resource_id=alert.id,
            payload_before=before,
            payload_after=_serialize(alert),
        )
        return alert

    async def list_alerts(
        self,
        *,
        domain: Domain | None = None,
        category: Category | None = None,
        severity: Severity | None = None,
        priority: Priority | None = None,
        status: AlertStatus | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> AlertQueryResponse:
        """List alerts for the tenant using canonical sort order and filters."""
        self._ensure_pagination(limit=limit, offset=offset)
        await self._set_rls_context()
        base_stmt = self._build_filtered_alerts_stmt(
            domain=domain,
            category=category,
            severity=severity,
            priority=priority,
            status=status,
            source_type=source_type,
            source_id=source_id,
            date_from=date_from,
            date_to=date_to,
        )

        total_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = int((await self.session.execute(total_stmt)).scalar_one() or 0)

        stmt = self._apply_ordering(base_stmt).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        alerts = [
            OperationalAlertResponse.model_validate(self._alert_response_data(alert))
            for alert in result.scalars().all()
        ]
        return AlertQueryResponse(alerts=alerts, total=total, limit=limit, offset=offset)

    async def get_alert_summary(
        self,
        *,
        domain: Domain | None = None,
        category: Category | None = None,
        severity: Severity | None = None,
        priority: Priority | None = None,
        status: AlertStatus | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        top_limit: int = DEFAULT_SUMMARY_TOP_LIMIT,
    ) -> AlertSummary:
        """Return the canonical alert summary for dashboard and Copilot consumers."""
        if top_limit < 1:
            raise BusinessRuleError("top_limit must be greater than zero.")

        await self._set_rls_context()
        stmt = self._build_filtered_alerts_stmt(
            domain=domain,
            category=category,
            severity=severity,
            priority=priority,
            status=status,
            source_type=source_type,
            source_id=source_id,
            date_from=date_from,
            date_to=date_to,
        )
        if status is None:
            stmt = stmt.where(OperationalAlert.status.in_(ACTIVE_ALERT_STATUSES))
        result = await self.session.execute(stmt)
        alerts = list(result.scalars().all())

        by_domain = self._empty_domain_summary()
        if not alerts:
            return AlertSummary(
                total_open=0,
                max_severity=None,
                max_priority=None,
                most_critical_domain=None,
                by_domain=by_domain,
                top_alerts=[],
            )

        for alert in alerts:
            domain_key = alert.domain
            if domain_key not in by_domain:
                by_domain[domain_key] = AlertSummaryByDomain(open=0, critical=0, urgent=0)
            domain_summary = by_domain[domain_key]
            domain_summary.open += 1
            if alert.severity in {Severity.CRITICAL.value, Severity.EMERGENCY.value}:
                domain_summary.critical += 1
            if alert.priority == Priority.URGENT.value:
                domain_summary.urgent += 1

        max_severity = self._max_enum_value((alert.severity for alert in alerts), self.SEVERITY_ORDER)
        max_priority = self._max_enum_value((alert.priority for alert in alerts), self.PRIORITY_ORDER)
        most_critical_domain = self._most_critical_domain(by_domain)
        top_alerts = [
            OperationalAlertResponse.model_validate(self._alert_response_data(alert))
            for alert in self._sort_alerts(alerts)[:top_limit]
        ]

        return AlertSummary(
            total_open=len(alerts),
            max_severity=Severity(max_severity) if max_severity else None,
            max_priority=Priority(max_priority) if max_priority else None,
            most_critical_domain=Domain(most_critical_domain) if most_critical_domain else None,
            by_domain=by_domain,
            top_alerts=top_alerts,
        )

    async def _find_active_alert(self, dedupe_key: str) -> OperationalAlert | None:
        stmt = select(OperationalAlert).where(
            OperationalAlert.tenant_id == self.tenant_id,
            OperationalAlert.dedupe_key == dedupe_key,
            OperationalAlert.status.in_(ACTIVE_ALERT_STATUSES),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_alert(self, alert_id: uuid.UUID) -> OperationalAlert:
        stmt = select(OperationalAlert).where(
            OperationalAlert.id == alert_id,
            OperationalAlert.tenant_id == self.tenant_id,
        )
        alert = (await self.session.execute(stmt)).scalar_one_or_none()
        if not alert:
            raise EntityNotFoundError("Alert not found for tenant.")
        return alert

    async def _create_lifecycle_event(
        self,
        *,
        alert: OperationalAlert,
        action_type: LifecycleActionType,
        previous_status: AlertStatus,
        new_status: AlertStatus,
        payload: dict | None,
        actor_id: uuid.UUID | None,
    ) -> AlertLifecycleEvent:
        event = AlertLifecycleEvent(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            alert_id=alert.id,
            actor_id=actor_id,
            action_type=action_type.value,
            previous_status=previous_status.value,
            new_status=new_status.value,
            payload=payload,
            source_channel=self.SOURCE_CHANNEL,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    def _merge_alert(self, target: OperationalAlert, source: OperationalAlertCreate) -> None:
        target.title = source.title
        target.message = source.message
        target.severity = source.severity.value
        target.priority = source.priority.value
        target.confidence = source.confidence
        target.trigger_type = source.trigger_type.value
        target.source_type = source.source_type
        target.source_id = source.source_id
        target.source_event_ids = self._merge_unique_ids(
            target.source_event_ids,
            [str(value) for value in source.source_event_ids],
        )
        target.source_indicator_ids = self._merge_unique_ids(
            target.source_indicator_ids,
            [str(value) for value in source.source_indicator_ids],
        )
        target.action_label = source.action_label
        target.action_url = source.action_url
        target.context = self._merge_context(target.context, source.context)
        target.expires_at = source.expires_at or target.expires_at
        target.unidade_produtiva_id = source.unidade_produtiva_id or target.unidade_produtiva_id

    @staticmethod
    def _merge_unique_ids(existing: list, new: list) -> list:
        merged = []
        for value in [*existing, *new]:
            if value not in merged:
                merged.append(value)
        return merged

    @staticmethod
    def _merge_context(existing: dict | None, new: dict | None) -> dict | None:
        if existing is None and new is None:
            return None
        if existing is None:
            return new
        if new is None:
            return existing
        merged = dict(existing)
        merged.update(new)
        return merged

    def _ensure_tenant(self, tenant_id: uuid.UUID) -> None:
        if tenant_id != self.tenant_id:
            raise TenantViolationError(
                "Payload tenant does not match service tenant.",
                tenant_id=self.tenant_id,
                resource=OperationalAlert.__tablename__,
            )

    @staticmethod
    def _alert_response_data(alert: OperationalAlert) -> dict:
        data = _serialize(alert) or {}
        if "metadata_" in data:
            data["metadata"] = data.pop("metadata_")
        return data

    async def _set_rls_context(self) -> None:
        await self.session.execute(text(f"SET LOCAL app.current_tenant_id = '{self.tenant_id}';"))

    def _build_filtered_alerts_stmt(
        self,
        *,
        domain: Domain | None,
        category: Category | None,
        severity: Severity | None,
        priority: Priority | None,
        status: AlertStatus | None,
        source_type: str | None,
        source_id: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ):
        stmt = select(OperationalAlert).where(OperationalAlert.tenant_id == self.tenant_id)
        domain_value = self._enum_text(domain)
        category_value = self._enum_text(category)
        severity_value = self._enum_text(severity)
        priority_value = self._enum_text(priority)
        status_value = self._enum_text(status)
        if domain is not None:
            stmt = stmt.where(OperationalAlert.domain == domain_value)
        if category is not None:
            stmt = stmt.where(OperationalAlert.category == category_value)
        if severity is not None:
            stmt = stmt.where(OperationalAlert.severity == severity_value)
        if priority is not None:
            stmt = stmt.where(OperationalAlert.priority == priority_value)
        if status is not None:
            stmt = stmt.where(OperationalAlert.status == status_value)
        if source_type is not None:
            stmt = stmt.where(OperationalAlert.source_type == source_type)
        if source_id is not None:
            stmt = stmt.where(OperationalAlert.source_id == source_id)
        if date_from is not None:
            stmt = stmt.where(OperationalAlert.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(OperationalAlert.created_at <= date_to)
        return stmt

    def _apply_ordering(self, stmt):
        severity_rank = case(
            (OperationalAlert.severity == Severity.EMERGENCY.value, 4),
            (OperationalAlert.severity == Severity.CRITICAL.value, 3),
            (OperationalAlert.severity == Severity.WARNING.value, 2),
            (OperationalAlert.severity == Severity.INFO.value, 1),
            else_=0,
        )
        priority_rank = case(
            (OperationalAlert.priority == Priority.URGENT.value, 4),
            (OperationalAlert.priority == Priority.HIGH.value, 3),
            (OperationalAlert.priority == Priority.NORMAL.value, 2),
            (OperationalAlert.priority == Priority.LOW.value, 1),
            else_=0,
        )
        return stmt.order_by(desc(severity_rank), desc(priority_rank), desc(OperationalAlert.created_at))

    def _sort_alerts(self, alerts: list[OperationalAlert]) -> list[OperationalAlert]:
        return sorted(
            alerts,
            key=lambda alert: (
                self.SEVERITY_ORDER.get(alert.severity, 0),
                self.PRIORITY_ORDER.get(alert.priority, 0),
                alert.created_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

    def _empty_domain_summary(self) -> dict[str, AlertSummaryByDomain]:
        return {
            domain.value: AlertSummaryByDomain(open=0, critical=0, urgent=0)
            for domain in Domain
        }

    @staticmethod
    def _max_enum_value(values, ranking: dict[str, int]) -> str | None:
        best_value = None
        best_rank = 0
        for value in values:
            rank = ranking.get(value or "", 0)
            if rank > best_rank:
                best_rank = rank
                best_value = value
        return best_value

    @staticmethod
    def _most_critical_domain(by_domain: dict[str, AlertSummaryByDomain]) -> str | None:
        active = [(name, counts) for name, counts in by_domain.items() if counts.open > 0]
        if not active:
            return None
        winner_name, _ = max(
            active,
            key=lambda item: (
                item[1].critical,
                item[1].urgent,
                item[1].open,
                item[0],
            ),
        )
        return winner_name

    @staticmethod
    def _ensure_pagination(*, limit: int, offset: int) -> None:
        if limit < 1 or limit > AlertLifecycleService.DEFAULT_QUERY_LIMIT * 5:
            raise BusinessRuleError("limit out of allowed range.")
        if offset < 0:
            raise BusinessRuleError("offset must be zero or positive.")

    @staticmethod
    def _enum_text(value) -> str | None:
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)
