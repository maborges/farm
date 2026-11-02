from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.dependencies import _activate_session_tenant
from core.models.tenant import Tenant
from recommendations import scheduler as scheduler_module
from recommendations.providers.wizard_provider import WizardRecommendationProvider
from recommendations.registry import RecommendationProviderRegistry
from wizard.models import (
    ImplantacaoChecklistItem,
    ImplantacaoOperacional,
    ImplantacaoPendencia,
)


TENANT_A = UUID("11111111-1111-4111-8111-111111111111")
TENANT_B = UUID("22222222-2222-4222-8222-222222222222")
TENANT_INACTIVE = UUID("33333333-3333-4333-8333-333333333333")


@pytest.mark.asyncio
async def test_wizard_scheduler_dispatcher_and_runtime_rls_lab(monkeypatch) -> None:
    runtime_url = os.getenv("DEEPFARMS_RLS_01J1_RUNTIME_URL")
    dispatcher_url = os.getenv("DEEPFARMS_RLS_01J1_DISPATCHER_URL")
    if not runtime_url or not dispatcher_url:
        pytest.skip("01J1 lab runtime/dispatcher URLs must be supplied by the test runner")

    runtime_engine = create_async_engine(
        runtime_url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {
                "search_path": "farms",
                "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
            }
        },
    )
    dispatcher_engine = create_async_engine(
        dispatcher_url,
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {
                "search_path": "farms",
                "options": "-c idle_in_transaction_session_timeout=30000 -c statement_timeout=60000",
            }
        },
    )
    runtime_sessions = async_sessionmaker(runtime_engine, expire_on_commit=False, autoflush=False)
    results = {}
    provider_rows: dict[UUID, tuple[UUID, ...]] = {}
    provider_context: dict[UUID, tuple[str, str, str, int]] = {}

    async def snapshot_tenant_rows(tenant_id: UUID) -> tuple[int, int, int]:
        async with runtime_sessions() as session:
            await _activate_session_tenant(session, tenant_id)
            counts = (
                await session.execute(
                    select(
                        select(func.count(ImplantacaoOperacional.id)).scalar_subquery(),
                        select(func.count(ImplantacaoChecklistItem.id)).scalar_subquery(),
                        select(func.count(ImplantacaoPendencia.id)).scalar_subquery(),
                    )
                )
            ).one()
            await session.rollback()
            return tuple(counts)

    try:
        async with runtime_sessions() as session:
            identity = (
                await session.execute(
                    text(
                        """SELECT current_database(), current_user, session_user,
                                  rolsuper, rolbypassrls
                           FROM pg_roles WHERE rolname = current_user"""
                    )
                )
            ).one()
            assert identity[0] == "deepfarms_rls_lab"
            assert identity[1] == identity[2] == "deepfarms_rls_lab_runtime"
            assert identity[3] is False and identity[4] is False

            memberships = (
                await session.execute(
                    text(
                        """SELECT count(*) FROM pg_auth_members am
                           JOIN pg_roles member ON member.oid = am.member
                           JOIN pg_roles granted ON granted.oid = am.roleid
                           WHERE member.rolname = current_user
                             AND granted.rolname IN
                                 ('deepfarms_rls_lab_owner', 'deepfarms_rls_lab_deploy',
                                  'deepfarms_rls_lab_dispatcher')"""
                    )
                )
            ).scalar_one()
            assert memberships == 0

        async with dispatcher_engine.connect() as dispatcher:
            dispatcher_identity = (
                await dispatcher.execute(
                    text("SELECT current_database(), current_user, session_user")
                )
            ).one()
            assert dispatcher_identity == (
                "deepfarms_rls_lab",
                "deepfarms_rls_lab_dispatcher",
                "deepfarms_rls_lab_dispatcher",
            )
            tenant_ids = await scheduler_module._list_active_tenant_ids(dispatcher)
            assert set(tenant_ids) == {TENANT_A, TENANT_B}

            with pytest.raises(DBAPIError):
                await dispatcher.execute(select(ImplantacaoOperacional.id))
            await dispatcher.rollback()

        async with runtime_sessions() as session:
            with pytest.raises(DBAPIError):
                await session.execute(select(Tenant.id))
            await session.rollback()

            no_context_count = await session.scalar(
                select(func.count(ImplantacaoOperacional.id))
            )
            assert no_context_count == 0
            await session.rollback()

        # The wizard provider instrumentation observes the effective database
        # identity and returned model rows, then delegates to its real method.
        original_list = WizardRecommendationProvider._listar_implantacoes

        async def capture_wizard_rows(provider, tenant_id, unidade_produtiva_id):
            identity = (
                await provider.session.execute(
                    text(
                        """SELECT current_user, session_user,
                                  current_setting('app.current_tenant_id', true),
                                  pg_backend_pid()"""
                    )
                )
            ).one()
            rows = await original_list(provider, tenant_id, unidade_produtiva_id)
            provider_rows[tenant_id] = tuple(row.tenant_id for row in rows)
            provider_context[tenant_id] = tuple(identity)
            return rows

        monkeypatch.setattr(
            WizardRecommendationProvider,
            "_listar_implantacoes",
            capture_wizard_rows,
        )
        registry = RecommendationProviderRegistry()
        registry.register(WizardRecommendationProvider)
        monkeypatch.setattr(
            scheduler_module,
            "recommendation_provider_registry",
            registry,
        )
        monkeypatch.setattr(scheduler_module, "async_session_maker", runtime_sessions)
        monkeypatch.setattr(
            scheduler_module,
            "dispatcher_engine",
            dispatcher_engine,
        )

        before = {
            tenant_id: await snapshot_tenant_rows(tenant_id)
            for tenant_id in (TENANT_A, TENANT_B)
        }

        original_run_tenant_cycle = scheduler_module._run_tenant_cycle

        async def capture_tenant_result(tenant_id, **kwargs):
            result = await original_run_tenant_cycle(tenant_id, **kwargs)
            results[tenant_id] = result
            return result

        monkeypatch.setattr(
            scheduler_module,
            "_run_tenant_cycle",
            capture_tenant_result,
        )

        completed = await scheduler_module.run_scheduled_recommendation_cycle(
            dry_run=True,
            batch_size=1,
        )
        assert completed == 2
        assert set(results) == {TENANT_A, TENANT_B}
        for tenant_id in (TENANT_A, TENANT_B):
            result = results[tenant_id]
            assert result is not None
            assert result.providers_requested == 1
            assert result.providers_executed == 1
            assert result.errors == 0
            assert result.candidates_total >= 1
            assert [item.provider_name for item in result.executions] == ["wizard"]
            assert provider_rows[tenant_id] == (tenant_id,)
            effective_user, session_user, effective_tenant, _pid = provider_context[tenant_id]
            assert effective_user == session_user == "deepfarms_rls_lab_runtime"
            assert effective_tenant == str(tenant_id)

        # A and B were processed by one runtime pool connection (pool_size=1),
        # proving local GUC state did not cross the checkout boundary.
        assert provider_context[TENANT_A][3] == provider_context[TENANT_B][3]

        after = {
            tenant_id: await snapshot_tenant_rows(tenant_id)
            for tenant_id in (TENANT_A, TENANT_B)
        }
        assert after == before

        # Context is rearmed by the shared 01G hook after COMMIT, ROLLBACK, and
        # a failed transaction; the same session continues to see its Tenant.
        async with runtime_sessions() as session:
            await _activate_session_tenant(session, TENANT_A)

            async def tenant_snapshot():
                row = (
                    await session.execute(
                        text(
                            """SELECT current_setting('app.current_tenant_id', true),
                                      (SELECT count(*) FROM wizard_implantacoes_operacionais)"""
                        )
                    )
                ).one()
                return row[0], row[1]

            assert await tenant_snapshot() == (str(TENANT_A), 1)
            await session.commit()
            assert await tenant_snapshot() == (str(TENANT_A), 1)
            await session.rollback()
            assert await tenant_snapshot() == (str(TENANT_A), 1)
            with pytest.raises(DBAPIError):
                await session.execute(text("SELECT 1 / 0"))
            await session.rollback()
            assert await tenant_snapshot() == (str(TENANT_A), 1)
            await session.rollback()

        # Verify dry-run left the operational fixtures untouched and created no
        # recommendation-result table/rows.
        async with runtime_sessions() as session:
            await _activate_session_tenant(session, TENANT_A)
            unchanged = await session.scalar(
                select(func.count(ImplantacaoOperacional.id))
            )
            assert unchanged == 1
            recommendation_table_absent = await session.scalar(
                text("SELECT to_regclass('farms.recommendation_results') IS NULL")
            )
            assert recommendation_table_absent is True
            await session.rollback()

        async with dispatcher_engine.connect() as first, dispatcher_engine.connect() as second:
            first_pid = await first.scalar(text("SELECT pg_backend_pid()"))
            second_pid = await second.scalar(text("SELECT pg_backend_pid()"))
            assert first_pid != second_pid
            assert await scheduler_module._acquire_scheduler_lock(first) is True
            await first.commit()  # Transaction boundary must not release the session lock.
            assert await first.scalar(text("SELECT pg_backend_pid()")) == first_pid
            assert await scheduler_module._acquire_scheduler_lock(second) is False
            await scheduler_module._release_scheduler_lock(first)
            assert await scheduler_module._acquire_scheduler_lock(second) is True
            await scheduler_module._release_scheduler_lock(second)

    finally:
        await dispatcher_engine.dispose()
        await runtime_engine.dispose()
