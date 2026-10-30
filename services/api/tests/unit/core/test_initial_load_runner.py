import pytest

from scripts.initial_load import run


@pytest.mark.asyncio
async def test_initial_load_runs_required_seeds_in_order(monkeypatch):
    from initial_load import (
        seed_admin,
        seed_catalogos,
        seed_crm_estagios,
        seed_culturas,
        seed_kb,
        seed_parametros_solo,
        seed_perfis,
        seed_plans,
    )

    from core import model_registry

    calls = []
    register_models = model_registry.register_models

    def record_model_registration():
        calls.append("orm_models")
        register_models()

    monkeypatch.setattr(model_registry, "register_models", record_model_registration)

    async def record(name):
        calls.append(name)

    monkeypatch.setattr(seed_catalogos, "seed_catalogos", lambda: record("catalogos"))
    monkeypatch.setattr(seed_perfis, "seed_perfis", lambda: record("perfis"))
    monkeypatch.setattr(seed_plans, "seed_plans", lambda: record("plans"))
    monkeypatch.setattr(seed_culturas, "run_seed", lambda: record("culturas"))
    monkeypatch.setattr(seed_parametros_solo, "run_seed", lambda: record("solo"))
    monkeypatch.setattr(seed_crm_estagios, "seed_estagios_crm", lambda session: record("crm"))
    monkeypatch.setattr(seed_kb, "seed_kb", lambda: record("kb"))
    monkeypatch.setattr(seed_admin, "seed_admin_user", lambda: record("admin"))
    monkeypatch.setattr(seed_admin, "seed_email_templates", lambda: record("email"))

    class SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_):
            return None

    from core import database

    monkeypatch.setattr(database, "async_session_maker", SessionContext)

    await run.run_initial_load()

    assert calls == [
        "orm_models",
        "catalogos",
        "perfis",
        "plans",
        "culturas",
        "solo",
        "crm",
        "kb",
        "admin",
        "email",
    ]
