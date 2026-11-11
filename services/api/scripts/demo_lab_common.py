"""Shared, lab-only session and synthetic tenant for demo data loaders."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from scripts.demo_lab_bootstrap import lab_url
from scripts.demo_lab_guard import DemoLabTargetError, validate_demo_lab_identity

NAMESPACE = UUID("ee22ca17-811c-40a5-b670-0fc3891bc7e9")
TENANT_ID = uuid5(NAMESPACE, "tenant")


def demo_id(name: str) -> UUID:
    """Return a stable identifier for one synthetic record."""
    return uuid5(NAMESPACE, name)


@asynccontextmanager
async def demo_session():
    """Open a lab-only session using the RLS-bound runtime role."""
    url = lab_url()
    os.environ["DATABASE_URL"] = url
    os.environ["RLS_DEV_ROUTE_SESSIONS_ENABLED"] = "false"
    os.environ["RLS_DEV_ALL_ROUTES_ENABLED"] = "false"
    os.environ["RUN_EMBEDDED_JOBS"] = "false"
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET ROLE deepfarms_demo_runtime"))
            await connection.execute(text("SET search_path TO farms, pg_catalog"))
            row = (await connection.execute(text("""
                SELECT current_database(), current_user, r.rolsuper, r.rolbypassrls,
                       has_schema_privilege(current_user, 'farms', 'USAGE')
                FROM pg_roles r WHERE r.rolname = current_user
            """))).one()
            validate_demo_lab_identity(*row)
            await connection.commit()
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                @event.listens_for(session.sync_session, "after_begin")
                def set_tenant(_session, _transaction, sync_connection):
                    sync_connection.execute(text(
                        "SELECT set_config('app.current_tenant_id', :tid, true)"
                    ), {"tid": str(TENANT_ID)})

                yield session
    finally:
        await engine.dispose()


async def ensure_model(session: AsyncSession, model, identifier: UUID, values: dict):
    """Insert a deterministic tenant-scoped object or reject drift on re-run."""
    row = (await session.execute(select(model).where(model.id == identifier))).scalar_one_or_none()
    if row is not None:
        for key, expected in values.items():
            actual = getattr(row, key)
            if isinstance(actual, Decimal):
                expected = Decimal(str(expected)) if expected is not None else None
            if actual != expected:
                raise DemoLabTargetError(f"Synthetic record drift in {model.__name__}.{key}")
        return row
    if "tenant_id" in values and values["tenant_id"] != TENANT_ID:
        raise DemoLabTargetError("Foreign tenant rejected")
    row = model(id=identifier, **values)
    session.add(row)
    await session.flush()
    return row


async def ensure_base(session: AsyncSession, scenario: str):
    """Create the demo tenant and the requested property without other tenants."""
    from core.models.tenant import Tenant
    from core.models.unidade_produtiva import UnidadeProdutiva

    names = {"cafe": "Fazenda Modelo 1", "pecuaria": "Fazenda Modelo 2"}
    if scenario not in names:
        raise DemoLabTargetError("Unknown demonstration scenario")
    await ensure_model(session, Tenant, TENANT_ID, {
        "nome": "demonstracao", "email_responsavel": "demonstracao@deepfarms.com.br",
        "slug": "deepfarms-demo-lab", "ativo": True,
    })
    return await ensure_model(session, UnidadeProdutiva, demo_id(scenario + "/fazenda"), {
        "tenant_id": TENANT_ID, "nome": names[scenario], "ativo": True,
        "tipo_propriedade": "fazenda", "area_total_ha": 1000,
    })


async def ensure_area(session: AsyncSession, name: str, values: dict):
    """Use the official area service to enforce the territorial hierarchy."""
    from core.cadastros.propriedades.models import AreaRural
    from core.cadastros.propriedades.service import AreaRuralService

    identifier = demo_id(name)
    row = (await session.execute(select(AreaRural).where(
        AreaRural.id == identifier, AreaRural.tenant_id == TENANT_ID
    ))).scalar_one_or_none()
    if row is not None:
        for key, expected in values.items():
            if getattr(row, key) != expected:
                raise DemoLabTargetError(f"Synthetic area drift in {key}")
        return row
    service = AreaRuralService(AreaRural, session, TENANT_ID)
    return await service.criar_area({"id": identifier, **values})
