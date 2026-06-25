from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import ACTIVE_ALERT_STATUSES, OperationalAlert


async def set_rls_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Bind the current tenant in the database session for RLS-aware queries."""

    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))


async def has_active_alert(session: AsyncSession, tenant_id: UUID, dedupe_key: str) -> bool:
    """Check whether an active alert already exists for the provided dedupe key."""

    stmt = select(OperationalAlert.id).where(
        OperationalAlert.tenant_id == tenant_id,
        OperationalAlert.dedupe_key == dedupe_key,
        OperationalAlert.status.in_(ACTIVE_ALERT_STATUSES),
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None
