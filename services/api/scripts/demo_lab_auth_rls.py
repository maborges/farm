"""Allow a demo user to discover only tenants they are actively linked to."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.demo_lab_bootstrap import lab_url
from scripts.demo_lab_guard import DemoLabTargetError


async def prepare() -> None:
    engine = create_async_engine(lab_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET ROLE deepfarms_demo_owner"))
            identity = (await connection.execute(text(
                "SELECT current_database(), current_user, session_user"
            ))).one()
            if tuple(identity) != ("deepfarms_demo_lab", "deepfarms_demo_owner", "borgus"):
                raise DemoLabTargetError("Unexpected authentication policy identity")

            state = (await connection.execute(text("""
                SELECT c.relrowsecurity, c.relforcerowsecurity,
                       (SELECT count(*) FROM pg_policies p
                        WHERE p.schemaname='farms' AND p.tablename='tenants'
                          AND p.policyname='demo_user_membership_read')
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='farms' AND c.relname='tenants'
            """))).one_or_none()
            if state == (True, True, 1):
                return
            if state != (True, True, 0):
                raise DemoLabTargetError(f"Unexpected tenant RLS state: {state}")

            await connection.execute(text("""
                CREATE POLICY demo_user_membership_read ON farms.tenants
                FOR SELECT TO deepfarms_demo_runtime
                USING (EXISTS (
                    SELECT 1 FROM farms.tenant_usuarios tu
                    WHERE tu.tenant_id = tenants.id
                      AND tu.usuario_id = NULLIF(
                          current_setting('app.current_user_id', true), ''
                      )::uuid
                      AND tu.status = 'ATIVO'
                ))
            """))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(prepare())
    print("Demo login tenant discovery policy installed")
