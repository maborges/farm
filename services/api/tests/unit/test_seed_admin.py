import asyncio
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select

from core.models.admin_user import AdminUser
from core.models.auth import Usuario

API_ROOT = Path(__file__).parents[2]


def test_seed_bootstrap_registers_mappers_and_compiles_admin_query() -> None:
    # Fresh interpreter reproduces the standalone script import, without the
    # model imports performed by tests/conftest.py.
    code = (
        "import sys; "
        "sys.path.insert(0, '.'); "
        "import scripts.initial_load.seed_admin; "
        "from sqlalchemy import select; "
        "from core.models.admin_user import AdminUser; "
        "from sqlalchemy.orm import configure_mappers; "
        "configure_mappers(); "
        "print(select(AdminUser))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=API_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "SELECT admin_users" in result.stdout


def test_admin_seed_is_idempotent(monkeypatch) -> None:
    from initial_load import seed_admin

    saved_admins = []
    saved_users = []

    class FakeSession:
        async def execute(self, statement):
            target = saved_admins if "admin_users" in str(statement) else saved_users
            return SimpleNamespace(
                scalar_one_or_none=lambda: target[0] if target else None
            )

        def add(self, record):
            if isinstance(record, AdminUser):
                saved_admins.append(record)
            else:
                saved_users.append(record)

        async def commit(self):
            return None

    @asynccontextmanager
    async def session_context():
        yield FakeSession()

    monkeypatch.setattr(seed_admin, "async_session_maker", session_context)
    monkeypatch.setattr(seed_admin, "hash_password", lambda _password: "test-hash")

    async def run_twice():
        # The production seed prints account details; keep test output free of
        # credential values while exercising the unchanged behavior.
        with patch("builtins.print"):
            await seed_admin.seed_admin_user()
            await seed_admin.seed_admin_user()

    asyncio.run(run_twice())
    assert len(saved_admins) == 1
    assert len(saved_users) == 1
    assert isinstance(saved_users[0], Usuario)
    assert saved_users[0].is_superuser is True
    assert saved_users[0].senha_hash == saved_admins[0].senha_hash


def test_seed_registers_models_without_breaking_safra_cultivo_relationship() -> None:
    from agricola.cultivos.models import Cultivo
    from agricola.safras.models import Safra

    configure = __import__("sqlalchemy.orm", fromlist=["configure_mappers"]).configure_mappers
    configure()
    assert Safra.cultivos.property.mapper.class_ is Cultivo
    assert Cultivo.safra.property.mapper.class_ is Safra
    # Admin query remains constructible after all relationship mappers configure.
    assert "admin_users" in str(select(AdminUser))
