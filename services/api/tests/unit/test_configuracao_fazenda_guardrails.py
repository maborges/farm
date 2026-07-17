from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from core.exceptions import BusinessRuleError
from core.routers import configuration as configuration_router
from core.schemas.config_schemas import ConfiguracaoFazendaUpdate
from core.services.configuracoes_service import ConfiguracoesService


def test_configuracao_fazenda_update_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ConfiguracaoFazendaUpdate(overrides={}, tenant_id=str(uuid4()))


def test_configuracao_fazenda_service_frozen_allowlist_e_sem_commit_interno() -> None:
    assert ConfiguracoesService.CONFIG_FAZENDA_OVERRIDE_ALLOWLIST == frozenset()
    source = inspect.getsource(ConfiguracoesService.set_override_fazenda)
    assert "commit(" not in source

    service = ConfiguracoesService(SimpleNamespace(), uuid4())
    with pytest.raises(BusinessRuleError):
        service._validar_overrides_fazenda({"fuso_horario": "America/Cuiaba"})


def test_configuracao_fazenda_routes_are_deprecated() -> None:
    app = FastAPI()
    app.include_router(configuration_router.router, prefix="/api/v1")

    deprecated_paths = {
        route.path
        for route in app.routes
        if getattr(route, "deprecated", False)
    }

    assert "/api/v1/config/fazenda/{unidade_produtiva_id}" in deprecated_paths
