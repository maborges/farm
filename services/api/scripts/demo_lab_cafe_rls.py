"""Add tenant policies for the coffee scenario in the isolated demo lab only."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.demo_lab_bootstrap import lab_url
from scripts.demo_lab_guard import DemoLabTargetError

TABLES = (
    "safra_fase_historico",
    "safra_talhoes",
    "safra_tarefas",
    "planos_operacionais",
    "planos_operacionais_tarefas",
    "agricola_orcamento_itens",
    "financeiro_lancamentos",
    "caderno_campo_entradas",
    "fin_planos_conta",
    "fin_receitas",
    "fin_despesas",
    "fin_rateios",
    "fin_contas_bancarias",
    "financeiro_comercializacoes",
    "cadastros_pessoas",
)


async def prepare():
    """Install only missing lab policies, rejecting unexpected existing policies."""
    engine = create_async_engine(lab_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET ROLE deepfarms_demo_owner"))
            identity = (
                await connection.execute(
                    text("SELECT current_database(), current_user, session_user")
                )
            ).one()
            if tuple(identity) != ("deepfarms_demo_lab", "deepfarms_demo_owner", "borgus"):
                raise DemoLabTargetError("Unexpected policy installation identity")
            for table in TABLES:
                state = (
                    await connection.execute(
                        text("""
                    SELECT c.relrowsecurity, c.relforcerowsecurity,
                           (SELECT count(*) FROM pg_policies p
                            WHERE p.schemaname='farms' AND p.tablename=c.relname
                              AND p.policyname='demo_tenant_scope')
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='farms' AND c.relname=:table
                """),
                        {"table": table},
                    )
                ).one_or_none()
                if state == (True, True, 1):
                    continue
                if state != (False, False, 0):
                    raise DemoLabTargetError(f"Unexpected RLS state: {table}")
                expression = (
                    "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
                )
                await connection.execute(
                    text(f'ALTER TABLE farms."{table}" ENABLE ROW LEVEL SECURITY')
                )
                await connection.execute(
                    text(f'ALTER TABLE farms."{table}" FORCE ROW LEVEL SECURITY')
                )
                await connection.execute(
                    text(
                        f'CREATE POLICY demo_tenant_scope ON farms."{table}" '
                        f"FOR ALL TO deepfarms_demo_runtime USING ({expression}) "
                        f"WITH CHECK ({expression})"
                    )
                )
            for table in ("estoque_saldos", "estoque_lotes"):
                state = (
                    await connection.execute(
                        text("""
                            SELECT c.relrowsecurity, c.relforcerowsecurity,
                                   (SELECT count(*) FROM pg_policies p
                                    WHERE p.schemaname='farms' AND p.tablename=c.relname
                                      AND p.policyname='demo_tenant_scope')
                            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                            WHERE n.nspname='farms' AND c.relname=:table
                        """),
                        {"table": table},
                    )
                ).one_or_none()
                if state == (True, True, 1):
                    continue
                if state != (False, False, 0):
                    raise DemoLabTargetError(f"Unexpected RLS state: {table}")
                expression = (
                    "EXISTS (SELECT 1 FROM farms.estoque_depositos d "  # noqa: S608
                    f'WHERE d.id = "{table}".deposito_id '
                    "AND d.tenant_id = "
                    "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
                )
                await connection.execute(
                    text(f'ALTER TABLE farms."{table}" ENABLE ROW LEVEL SECURITY')
                )
                await connection.execute(
                    text(f'ALTER TABLE farms."{table}" FORCE ROW LEVEL SECURITY')
                )
                await connection.execute(
                    text(
                        f'CREATE POLICY demo_tenant_scope ON farms."{table}" '
                        f"FOR ALL TO deepfarms_demo_runtime USING ({expression}) "
                        f"WITH CHECK ({expression})"
                    )
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(prepare())
    print("Additional laboratory tenant policies installed")
