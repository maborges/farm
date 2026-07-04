from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import fmean

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import RecommendationDomain, RecommendationLifecycleActionType, RecommendationStatus
from .models import RecommendationLifecycleEvent, RecommendationResult
from .schemas import (
    RecommendationDomainMetricsListResponse,
    RecommendationDomainMetricsResponse,
    RecommendationMetricsFilterResponse,
    RecommendationLifecycleMetricsResponse,
    RecommendationMetricsSummaryResponse,
    RecommendationMetricsTimelinePointResponse,
    RecommendationRuleMetricsItem,
    RecommendationRuleMetricsResponse,
)

UTC = timezone.utc


class RecommendationMetricsService:
    """Read-only operational metrics for the canonical recommendation engine."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def summary(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        domain: RecommendationDomain | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> RecommendationMetricsSummaryResponse:
        """Return tenant-level recommendation metrics.

        Args:
            start_date: Optional inclusive start date for the metrics window.
            end_date: Optional inclusive end date for the metrics window.
            domain: Optional recommendation domain filter.
            unidade_produtiva_id: Optional production unit filter.

        Returns:
            Tenant-level summary metrics.

        Raises:
            None.
        """
        await self._set_rls_context()
        results = await self._load_results(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        events = await self._load_events(results, start_date=start_date, end_date=end_date)
        timeline = self._build_timeline(results)
        return RecommendationMetricsSummaryResponse(
            filters=self._filters(start_date, end_date, domain, unidade_produtiva_id),
            generated_at=datetime.now(UTC),
            tenant_id=self.tenant_id,
            total_recommendations=len(results),
            by_domain=self._count_by(results, "domain"),
            by_status=self._count_by(results, "status"),
            by_priority=self._count_by(results, "priority"),
            viewed_total=self._count_timestamp(results, "viewed_at"),
            accepted_total=self._count_timestamp(results, "accepted_at"),
            dismissed_total=self._count_timestamp(results, "dismissed_at"),
            executed_total=self._count_timestamp(results, "executed_at"),
            expired_total=self._count_status(results, {RecommendationStatus.EXPIRED.value, RecommendationStatus.AUTO_EXPIRED.value}),
            superseded_total=self._count_status(results, {RecommendationStatus.SUPERSEDED.value}),
            reopened_total=self._count_status(results, {RecommendationStatus.REOPENED.value}),
            view_rate=self._rate(self._count_timestamp(results, "viewed_at"), len(results)),
            accept_rate=self._rate(self._count_timestamp(results, "accepted_at"), len(results)),
            dismiss_rate=self._rate(self._count_timestamp(results, "dismissed_at"), len(results)),
            execute_rate=self._rate(self._count_timestamp(results, "executed_at"), len(results)),
            avg_time_to_view_seconds=self._average_duration(results, "viewed_at"),
            avg_time_to_accept_seconds=self._average_duration(results, "accepted_at"),
            avg_time_to_execute_seconds=self._average_duration(results, "executed_at"),
            lifecycle_events_total=len(events),
            timeline=timeline,
        )

    async def by_domain(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        domain: RecommendationDomain | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> RecommendationDomainMetricsListResponse:
        """Return domain-level recommendation metrics.

        Args:
            start_date: Optional inclusive start date for the metrics window.
            end_date: Optional inclusive end date for the metrics window.
            domain: Optional recommendation domain filter.
            unidade_produtiva_id: Optional production unit filter.

        Returns:
            Domain breakdown metrics.

        Raises:
            None.
        """
        await self._set_rls_context()
        results = await self._load_results(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        return RecommendationDomainMetricsListResponse(
            filters=self._filters(start_date, end_date, domain, unidade_produtiva_id),
            generated_at=datetime.now(UTC),
            items=self._build_domain_items(results),
        )

    async def by_rule(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        domain: RecommendationDomain | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> RecommendationRuleMetricsResponse:
        """Return leaderboards grouped by recommendation rule.

        Args:
            start_date: Optional inclusive start date for the metrics window.
            end_date: Optional inclusive end date for the metrics window.
            domain: Optional recommendation domain filter.
            unidade_produtiva_id: Optional production unit filter.

        Returns:
            Rule leaderboards ranked by volume, acceptance and dismissal.

        Raises:
            None.
        """
        await self._set_rls_context()
        results = await self._load_results(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        items = self._build_rule_items(results)
        return RecommendationRuleMetricsResponse(
            filters=self._filters(start_date, end_date, domain, unidade_produtiva_id),
            generated_at=datetime.now(UTC),
            top_by_volume=self._top(items, key="total"),
            top_by_acceptance=self._top(items, key="accepted_total"),
            top_by_dismissal=self._top(items, key="dismissed_total"),
        )

    async def lifecycle(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        domain: RecommendationDomain | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> RecommendationLifecycleMetricsResponse:
        """Return lifecycle event metrics for governance monitoring.

        Args:
            start_date: Optional inclusive start date for the metrics window.
            end_date: Optional inclusive end date for the metrics window.
            domain: Optional recommendation domain filter.
            unidade_produtiva_id: Optional production unit filter.

        Returns:
            Lifecycle totals and transition counts.

        Raises:
            None.
        """
        await self._set_rls_context()
        results = await self._load_results(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        events = await self._load_events(results, start_date=start_date, end_date=end_date)
        timeline = self._build_event_timeline(events)
        by_action = Counter(event.action_type for event in events)
        by_transition = Counter(f"{event.previous_status}->{event.new_status}" for event in events)
        by_new_status = Counter(event.new_status for event in events)
        return RecommendationLifecycleMetricsResponse(
            filters=self._filters(start_date, end_date, domain, unidade_produtiva_id),
            generated_at=datetime.now(UTC),
            tenant_id=self.tenant_id,
            total_events=len(events),
            by_action=dict(sorted(by_action.items())),
            by_transition=dict(sorted(by_transition.items())),
            created_total=by_action.get(RecommendationLifecycleActionType.CREATE.value, 0),
            viewed_total=by_new_status.get(RecommendationStatus.VIEWED.value, 0),
            accepted_total=by_new_status.get(RecommendationStatus.ACCEPTED.value, 0),
            dismissed_total=by_new_status.get(RecommendationStatus.DISMISSED.value, 0),
            executed_total=by_new_status.get(RecommendationStatus.EXECUTED.value, 0),
            expired_total=by_new_status.get(RecommendationStatus.EXPIRED.value, 0)
            + by_new_status.get(RecommendationStatus.AUTO_EXPIRED.value, 0),
            superseded_total=by_new_status.get(RecommendationStatus.SUPERSEDED.value, 0),
            reopened_total=by_new_status.get(RecommendationStatus.REOPENED.value, 0),
            timeline=timeline,
        )

    async def _load_results(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        domain: str | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> list[RecommendationResult]:
        stmt = select(RecommendationResult).where(*self._result_filters(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        ))
        return list((await self.session.execute(stmt)).scalars().all())

    async def _load_events(
        self,
        results: list[RecommendationResult],
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[RecommendationLifecycleEvent]:
        recommendation_ids = [result.id for result in results]
        if not recommendation_ids:
            return []
        stmt = select(RecommendationLifecycleEvent).where(
            RecommendationLifecycleEvent.tenant_id == self.tenant_id,
            RecommendationLifecycleEvent.recommendation_id.in_(recommendation_ids),
            *self._event_date_filters(start_date, end_date),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _build_domain_items(self, results: list[RecommendationResult]) -> list[RecommendationDomainMetricsResponse]:
        grouped: dict[str, list[RecommendationResult]] = defaultdict(list)
        for result in results:
            grouped[result.domain].append(result)
        items = [self._domain_item(domain, domain_results) for domain, domain_results in grouped.items()]
        return sorted(items, key=lambda item: (-item.total, item.domain.value))

    def _build_rule_items(self, results: list[RecommendationResult]) -> list[RecommendationRuleMetricsItem]:
        grouped: dict[str, list[RecommendationResult]] = defaultdict(list)
        for result in results:
            grouped[result.rule_code].append(result)
        items = [self._rule_item(rule_code, rule_results) for rule_code, rule_results in grouped.items()]
        return sorted(items, key=lambda item: (-item.total, item.rule_code))

    def _domain_item(self, domain: str, results: list[RecommendationResult]) -> RecommendationDomainMetricsResponse:
        total = len(results)
        viewed_total = self._count_timestamp(results, "viewed_at")
        accepted_total = self._count_timestamp(results, "accepted_at")
        dismissed_total = self._count_timestamp(results, "dismissed_at")
        executed_total = self._count_timestamp(results, "executed_at")
        return RecommendationDomainMetricsResponse(
            domain=domain,
            total=total,
            by_status=self._count_by(results, "status"),
            by_priority=self._count_by(results, "priority"),
            viewed_total=viewed_total,
            accepted_total=accepted_total,
            dismissed_total=dismissed_total,
            executed_total=executed_total,
            view_rate=self._rate(viewed_total, total),
            accept_rate=self._rate(accepted_total, total),
            dismiss_rate=self._rate(dismissed_total, total),
            execute_rate=self._rate(executed_total, total),
            avg_time_to_view_seconds=self._average_duration(results, "viewed_at"),
            avg_time_to_accept_seconds=self._average_duration(results, "accepted_at"),
            avg_time_to_execute_seconds=self._average_duration(results, "executed_at"),
        )

    def _rule_item(self, rule_code: str, results: list[RecommendationResult]) -> RecommendationRuleMetricsItem:
        sample = results[0]
        total = len(results)
        accepted_total = self._count_timestamp(results, "accepted_at")
        dismissed_total = self._count_timestamp(results, "dismissed_at")
        executed_total = self._count_timestamp(results, "executed_at")
        viewed_total = self._count_timestamp(results, "viewed_at")
        return RecommendationRuleMetricsItem(
            rule_code=rule_code,
            provider_name=sample.provider_name,
            domain=sample.domain,
            total=total,
            accepted_total=accepted_total,
            dismissed_total=dismissed_total,
            executed_total=executed_total,
            view_rate=self._rate(viewed_total, total),
            accept_rate=self._rate(accepted_total, total),
            dismiss_rate=self._rate(dismissed_total, total),
            execute_rate=self._rate(executed_total, total),
        )

    def _top(self, items: list[RecommendationRuleMetricsItem], *, key: str) -> list[RecommendationRuleMetricsItem]:
        return sorted(items, key=lambda item: (-int(getattr(item, key)), item.rule_code))[:10]

    def _build_timeline(self, results: list[RecommendationResult]) -> list[RecommendationMetricsTimelinePointResponse]:
        buckets: dict[date, dict[str, int]] = defaultdict(lambda: {
            "total_recommendations": 0,
            "viewed_total": 0,
            "accepted_total": 0,
            "dismissed_total": 0,
            "executed_total": 0,
        })
        for result in results:
            period = result.created_at.date()
            bucket = buckets[period]
            bucket["total_recommendations"] += 1
            bucket["viewed_total"] += int(result.viewed_at is not None)
            bucket["accepted_total"] += int(result.accepted_at is not None)
            bucket["dismissed_total"] += int(result.dismissed_at is not None)
            bucket["executed_total"] += int(result.executed_at is not None)
        return [
            RecommendationMetricsTimelinePointResponse(
                period=period,
                total_recommendations=payload["total_recommendations"],
                viewed_total=payload["viewed_total"],
                accepted_total=payload["accepted_total"],
                dismissed_total=payload["dismissed_total"],
                executed_total=payload["executed_total"],
                accept_rate=self._rate(payload["accepted_total"], payload["total_recommendations"]),
                dismissed_rate=self._rate(payload["dismissed_total"], payload["total_recommendations"]),
                executed_rate=self._rate(payload["executed_total"], payload["total_recommendations"]),
            )
            for period, payload in sorted(buckets.items())
        ]

    def _build_event_timeline(self, events: list[RecommendationLifecycleEvent]) -> list[RecommendationMetricsTimelinePointResponse]:
        buckets: dict[date, dict[str, int]] = defaultdict(lambda: {
            "total_recommendations": 0,
            "viewed_total": 0,
            "accepted_total": 0,
            "dismissed_total": 0,
            "executed_total": 0,
        })
        for event in events:
            period = event.created_at.date()
            bucket = buckets[period]
            bucket["total_recommendations"] += 1
            bucket["viewed_total"] += int(event.new_status == RecommendationStatus.VIEWED.value)
            bucket["accepted_total"] += int(event.new_status == RecommendationStatus.ACCEPTED.value)
            bucket["dismissed_total"] += int(event.new_status == RecommendationStatus.DISMISSED.value)
            bucket["executed_total"] += int(event.new_status == RecommendationStatus.EXECUTED.value)
        return [
            RecommendationMetricsTimelinePointResponse(
                period=period,
                total_recommendations=payload["total_recommendations"],
                viewed_total=payload["viewed_total"],
                accepted_total=payload["accepted_total"],
                dismissed_total=payload["dismissed_total"],
                executed_total=payload["executed_total"],
                accept_rate=self._rate(payload["accepted_total"], payload["total_recommendations"]),
                dismissed_rate=self._rate(payload["dismissed_total"], payload["total_recommendations"]),
                executed_rate=self._rate(payload["executed_total"], payload["total_recommendations"]),
            )
            for period, payload in sorted(buckets.items())
        ]

    @staticmethod
    def _count_by(results: list[RecommendationResult], attribute: str) -> dict[str, int]:
        counter = Counter(str(getattr(result, attribute)) for result in results)
        return dict(sorted(counter.items()))

    @staticmethod
    def _count_timestamp(results: list[RecommendationResult], attribute: str) -> int:
        return sum(1 for result in results if getattr(result, attribute) is not None)

    @staticmethod
    def _count_status(results: list[RecommendationResult], statuses: set[str]) -> int:
        return sum(1 for result in results if result.status in statuses)

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return round((numerator / denominator) if denominator else 0.0, 4)

    @staticmethod
    def _average_duration(results: list[RecommendationResult], attribute: str) -> float | None:
        durations = [
            (getattr(result, attribute) - result.created_at).total_seconds()
            for result in results
            if getattr(result, attribute) is not None and result.created_at is not None
        ]
        return round(fmean(durations), 2) if durations else None

    async def _set_rls_context(self) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )

    def _result_filters(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        domain: RecommendationDomain | None,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[object]:
        filters: list[object] = [RecommendationResult.tenant_id == self.tenant_id]
        if start_date is not None:
            filters.append(RecommendationResult.created_at >= self._start_of_day(start_date))
        if end_date is not None:
            filters.append(RecommendationResult.created_at < self._end_of_day(end_date))
        if domain is not None:
            filters.append(RecommendationResult.domain == domain.value)
        if unidade_produtiva_id is not None:
            filters.append(RecommendationResult.unidade_produtiva_id == unidade_produtiva_id)
        return filters

    def _event_date_filters(self, start_date: date | None, end_date: date | None) -> list[object]:
        filters: list[object] = []
        if start_date is not None:
            filters.append(RecommendationLifecycleEvent.created_at >= self._start_of_day(start_date))
        if end_date is not None:
            filters.append(RecommendationLifecycleEvent.created_at < self._end_of_day(end_date))
        return filters

    @staticmethod
    def _start_of_day(value: date) -> datetime:
        return datetime(value.year, value.month, value.day, tzinfo=UTC)

    @staticmethod
    def _end_of_day(value: date) -> datetime:
        return datetime(value.year, value.month, value.day, tzinfo=UTC) + timedelta(days=1)

    @staticmethod
    def _filters(
        start_date: date | None,
        end_date: date | None,
        domain: RecommendationDomain | None,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> RecommendationMetricsFilterResponse:
        return RecommendationMetricsFilterResponse(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            unidade_produtiva_id=unidade_produtiva_id,
        )
