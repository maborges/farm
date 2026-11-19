from __future__ import annotations

from contextlib import asynccontextmanager
from importlib import import_module
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from core import dependencies


def _request(method: str, path: str) -> Request:
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def scalar_one_or_none(self):
        if not self._rows:
            return None
        row = self._rows[0]
        return row[0] if isinstance(row, tuple) else row


class _FakeBind:
    def __init__(
        self,
        *,
        dialect_name: str = "postgresql",
        owners: dict[str, str | None] | None = None,
        dedicated_roles: list[str] | None = None,
    ):
        self.dialect = SimpleNamespace(name=dialect_name)
        self._owners = owners or {}
        self._dedicated_roles = dedicated_roles or []
        self.executed: list[tuple[str, dict[str, object] | None]] = []

    def execute(self, statement, params=None):
        sql_text = str(statement)
        self.executed.append((sql_text, params))
        if "pg_class" in sql_text:
            table_name = str((params or {}).get("table_name", ""))
            owner = self._owners.get(table_name)
            return _FakeResult([(owner,)] if owner is not None else [])
        if "pg_roles" in sql_text:
            return _FakeResult([(role,) for role in self._dedicated_roles])
        return _FakeResult([])


def test_migration_revision_chain_and_constants():
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    assert migration.revision == "20261119_rls_global_catalog_admin_write"
    assert migration.down_revision == "20261118_plano_acao_capex"


def test_resolve_global_catalog_admin_roles_includes_owner_and_dedicated_and_excludes_runtime():
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    bind = _FakeBind(
        owners={"modelos_fitossanitarios": "borgus"},
        dedicated_roles=["df_catalog_admin"],
    )

    roles = migration._resolve_global_catalog_admin_roles(bind, "modelos_fitossanitarios")
    assert roles == ["borgus", "df_catalog_admin"]

    filtered_bind = _FakeBind(
        owners={"modelos_fitossanitarios": "deepfarms_runtime"},
        dedicated_roles=[
            "public",
            "deepfarms_runtime",
            "deepfarms_auth",
            "deepfarms_dispatcher",
            "custom_runtime",
            "custom_auth",
            "custom_dispatcher",
            "df_catalog_admin",
            "deepfarms_catalog_admin",
        ],
    )
    filtered_roles = migration._resolve_global_catalog_admin_roles(
        filtered_bind, "modelos_fitossanitarios"
    )
    assert filtered_roles == ["df_catalog_admin", "deepfarms_catalog_admin"]


def test_resolve_global_catalog_admin_roles_fails_closed_when_empty():
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    bind = _FakeBind(
        owners={"modelos_fitossanitarios": "deepfarms_runtime"},
        dedicated_roles=["public", "deepfarms_auth", "deepfarms_dispatcher"],
    )

    with pytest.raises(RuntimeError, match="modelos_fitossanitarios"):
        migration._resolve_global_catalog_admin_roles(bind, "modelos_fitossanitarios")


def test_upgrade_creates_six_nominative_global_admin_policies(monkeypatch):
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    bind = _FakeBind(
        owners={
            "modelos_fitossanitarios": "borgus",
            "modelos_zoosanitarios": "borgus",
        },
        dedicated_roles=["df_catalog_admin"],
    )
    executed_sql: list[str] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "execute", lambda stmt: executed_sql.append(str(stmt)))

    migration.upgrade()

    drop_statements = [s for s in executed_sql if s.startswith("DROP POLICY IF EXISTS ")]
    create_statements = [s for s in executed_sql if s.startswith("CREATE POLICY ")]
    expected_policies = [
        f'"{table}_global_admin_{suffix}"'
        for table in ("modelos_fitossanitarios", "modelos_zoosanitarios")
        for suffix in ("insert", "update", "delete")
    ]
    assert len(drop_statements) == 6
    assert len(create_statements) == 6

    for policy_ident, stmt in zip(expected_policies, create_statements):
        assert policy_ident in stmt
        assert ' TO "borgus", "df_catalog_admin" ' in stmt
        assert "TO PUBLIC" not in stmt.upper()
        assert "tenant_id IS NULL" in stmt
        assert "NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text) IS NULL" in stmt

    for table in ("modelos_fitossanitarios", "modelos_zoosanitarios"):
        for legacy_suffix in ("select", "insert", "update", "delete"):
            assert not any(
                f'"{table}_{legacy_suffix}"' in s for s in executed_sql
            )


def test_upgrade_and_downgrade_are_noop_for_non_postgresql(monkeypatch):
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    sqlite_bind = _FakeBind(dialect_name="sqlite")
    executed_sql: list[str] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: sqlite_bind)
    monkeypatch.setattr(migration.op, "execute", lambda stmt: executed_sql.append(str(stmt)))

    migration.upgrade()
    migration.downgrade()

    assert executed_sql == []


def test_downgrade_drops_exactly_the_six_global_admin_policies(monkeypatch):
    migration = import_module("migrations.versions.20261119_rls_global_catalog_admin_write")
    pg_bind = _FakeBind(dialect_name="postgresql")
    executed_sql: list[str] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: pg_bind)
    monkeypatch.setattr(migration.op, "execute", lambda stmt: executed_sql.append(str(stmt)))

    migration.downgrade()

    expected = [
        f'DROP POLICY IF EXISTS "{table}_global_admin_{suffix}" ON "{table}"'
        for table in ("modelos_fitossanitarios", "modelos_zoosanitarios")
        for suffix in ("insert", "update", "delete")
    ]
    assert executed_sql == expected


@pytest.mark.asyncio
async def test_get_catalog_admin_session_routing_and_fail_closed(monkeypatch):
    observed: list[str] = []

    class FakeSession:
        def __init__(self, tag: str):
            self.tag = tag
            self.info = {}

    def make_factory(tag: str):
        @asynccontextmanager
        async def _ctx():
            observed.append(tag)
            yield FakeSession(tag)

        return _ctx

    # 1. Usa catalog_admin_async_session_maker quando configurado
    monkeypatch.setattr(dependencies, "catalog_admin_async_session_maker", make_factory("catalog_admin"))
    monkeypatch.setattr(dependencies, "async_session_maker", make_factory("legacy"))
    monkeypatch.setattr(dependencies.settings, "require_restricted_runtime_role", True)

    gen = dependencies.get_catalog_admin_session(_request("POST", "/api/v1/climatico/backoffice/modelos-fitossanitarios"))
    sess = await anext(gen)
    assert sess.tag == "catalog_admin"
    await gen.aclose()

    # 2. Fail-closed (HTTP 503) sob runtime restrito sem catalog_admin_async_session_maker
    monkeypatch.setattr(dependencies, "catalog_admin_async_session_maker", None)
    monkeypatch.setattr(dependencies.settings, "require_restricted_runtime_role", True)
    with pytest.raises(HTTPException) as exc_info:
        await anext(dependencies.get_catalog_admin_session(_request("POST", "/api/v1/climatico/backoffice/modelos-fitossanitarios")))
    assert exc_info.value.status_code == 503

    # 2b. Também fail-closed quando uses_restricted_route_session retorna True
    monkeypatch.setattr(dependencies.settings, "require_restricted_runtime_role", False)
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    monkeypatch.setattr(dependencies.settings, "rls_dev_all_routes_enabled", True)
    with pytest.raises(HTTPException) as exc_info_2:
        await anext(dependencies.get_catalog_admin_session(_request("POST", "/api/v1/climatico/backoffice/modelos-fitossanitarios")))
    assert exc_info_2.value.status_code == 503

    # 3. Fallback para async_session_maker apenas quando modo restrito está desligado
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", False)
    monkeypatch.setattr(dependencies.settings, "rls_dev_all_routes_enabled", False)
    gen_legacy = dependencies.get_catalog_admin_session(_request("POST", "/api/v1/climatico/backoffice/modelos-fitossanitarios"))
    sess_legacy = await anext(gen_legacy)
    assert sess_legacy.tag == "legacy"
    await gen_legacy.aclose()

    assert observed == ["catalog_admin", "legacy"]
