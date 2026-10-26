"""Regressões de segurança da identidade global e rollback BYOK."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import context
from fastapi import HTTPException, Request


MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20261022_agro_admin_01b1_session_nullable.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("agro_admin_identity_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _Connection:
    def __init__(self, values: list[int]) -> None:
        self.values = iter(values)

    def execute(self, _statement):
        return _ScalarResult(next(self.values))


@pytest.mark.parametrize(
    ("counts", "expected_message"),
    [
        ([3], "credenciais BYOK persistidas"),
        ([0, 2], "sessões globais sem tenant"),
    ],
)
def test_downgrade_bloqueia_dados_antes_de_qualquer_ddl(
    monkeypatch, counts: list[int], expected_message: str
) -> None:
    migration = _load_migration()
    calls: list[tuple] = []
    connection = _Connection(counts)
    migration.op = SimpleNamespace(
        get_bind=lambda: connection,
        drop_table=lambda *args, **kwargs: calls.append(("drop", args, kwargs)),
        alter_column=lambda *args, **kwargs: calls.append(("alter", args, kwargs)),
    )
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.sa, "inspect", lambda _connection: SimpleNamespace(has_table=lambda *_args, **_kwargs: True))

    with pytest.raises(RuntimeError, match=expected_message):
        migration.downgrade()

    assert calls == []


def test_downgrade_offline_recusa_gerar_ddl_sem_inspecao(monkeypatch) -> None:
    migration = _load_migration()
    monkeypatch.setattr(context, "is_offline_mode", lambda: True)
    migration.op = SimpleNamespace(get_bind=lambda: pytest.fail("não deve abrir conexão"))

    with pytest.raises(RuntimeError, match="modo offline"):
        migration.downgrade()


def test_rotas_legadas_de_identidade_agro_nao_sao_montadas_por_padrao() -> None:
    from core.config import settings
    from main import app

    if settings.enable_legacy_agro_db:
        pytest.skip("Ambiente optou explicitamente por habilitar o repositório legado")

    paths = {route.path for route in app.routes}
    assert "/api/v1/agro/auth/register" not in paths
    assert "/api/v1/agro/auth/login" not in paths
    assert "/api/v1/agro/auth/logout" not in paths
    assert "/api/v1/agro/byok/credentials" in paths


def test_logout_central_valida_cookie_e_bloqueia_csrf_cross_site() -> None:
    from core.dependencies import get_token
    from core.routers.auth import router as auth_router

    logout_route = next(route for route in auth_router.routes if route.path == "/auth/logout")
    assert any(dependency.call is get_token for dependency in logout_route.dependant.dependencies)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/auth/logout",
            "raw_path": b"/api/v1/auth/logout",
            "query_string": b"",
            "headers": [
                (b"cookie", b"deepfarms_session=session-token"),
                (b"sec-fetch-site", b"cross-site"),
            ],
            "server": ("deepfarms.com.br", 443),
            "client": ("198.51.100.8", 1234),
            "http_version": "1.1",
        }
    )
    with pytest.raises(HTTPException) as error:
        get_token(request)
    assert error.value.status_code == 403
