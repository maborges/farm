"""Install explicit tenant policies only in the disposable demonstration lab.

These laboratory policies are not migrations and do not prove production RLS.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.demo_lab_bootstrap import lab_url
from scripts.demo_lab_guard import DemoLabTargetError

# This is deliberately limited to the domain rows needed by the demo scripts.
TABLES = (
    "tenants", "unidades_produtivas", "cadastros_areas_rurais", "safras",
    "cultivos", "cultivo_areas", "production_units", "cadastros_produtos",
    "estoque_depositos", "estoque_movimentos", "operacoes_agricolas",
    "operacoes_execucoes", "insumos_operacao", "cost_allocations",
    "romaneios_colheita", "agricola_produtos_colhidos", "pec_lotes",
    "pec_animais", "pec_eventos_animal", "pec_manejos_lote",
)


async def prepare_policies() -> None:
    """Apply missing policies on explicitly listed lab tables in one transaction."""
    engine = create_async_engine(lab_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET ROLE deepfarms_demo_owner"))
            identity = (await connection.execute(text(
                "SELECT current_database(), current_user, session_user"
            ))).one()
            if tuple(identity) != ("deepfarms_demo_lab", "deepfarms_demo_owner", "borgus"):
                raise DemoLabTargetError("Unexpected policy installation identity")
            for table in TABLES:
                exists = (await connection.execute(text(
                    "SELECT to_regclass(:name) IS NOT NULL"
                ), {"name": f"farms.{table}"})).scalar_one()
                if not exists:
                    raise DemoLabTargetError(f"Missing demonstration table: {table}")
                enabled = (await connection.execute(text(
                    "SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:name)"
                ), {"name": f"farms.{table}"})).scalar_one()
                if enabled:
                    raise DemoLabTargetError(f"Existing RLS requires manual review: {table}")
                key = "id" if table == "tenants" else "tenant_id"
                expression = f"{key} = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
                await connection.execute(text(f'ALTER TABLE farms."{table}" ENABLE ROW LEVEL SECURITY'))
                await connection.execute(text(f'ALTER TABLE farms."{table}" FORCE ROW LEVEL SECURITY'))
                await connection.execute(text(
                    f'CREATE POLICY demo_tenant_scope ON farms."{table}" '
                    f'FOR ALL TO deepfarms_demo_runtime USING ({expression}) WITH CHECK ({expression})'
                ))
    finally:
        await engine.dispose()
    print(f"Laboratory-only RLS installed for {len(TABLES)} tables")


if __name__ == "__main__":
    asyncio.run(prepare_policies())
