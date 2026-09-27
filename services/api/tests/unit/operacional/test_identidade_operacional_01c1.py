from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.cadastros.pessoas.models import PessoaUsuario
from core.exceptions import EntityNotFoundError
from operacional.services.identidade_operacional_service import (
    IdentidadeOperacionalService,
)


class _Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, *values):
        self.values = list(values)

    async def execute(self, _statement):
        return _Result(self.values.pop(0))


def test_identity_is_contextual_and_has_active_cardinality_constraints() -> None:
    table = PessoaUsuario.__table__
    assert {"tenant_id", "pessoa_id", "usuario_id", "status"}.issubset(table.c.keys())
    constraints = {constraint.name for constraint in table.constraints}
    assert "fk_pessoa_usuario_tenant_pessoa" in constraints
    assert "fk_pessoa_usuario_tenant_usuario" in constraints
    assert "uq_pessoa_usuario_tenant_id" in constraints
    indexes = {index.name for index in table.indexes}
    assert "uq_pessoa_usuario_tenant_pessoa_ativo" in indexes
    assert "uq_pessoa_usuario_tenant_usuario_ativo" in indexes


@pytest.mark.asyncio
async def test_resolver_requires_active_identity_and_membership_result() -> None:
    identity = SimpleNamespace(id=uuid4(), pessoa_id=uuid4())
    session = _Session(identity)

    resolved = await IdentidadeOperacionalService.resolver_pessoa_usuario(
        session, uuid4(), uuid4()
    )

    assert resolved is identity


@pytest.mark.asyncio
async def test_resolver_rejects_missing_identity() -> None:
    with pytest.raises(EntityNotFoundError, match="identidade operacional"):
        await IdentidadeOperacionalService.resolver_pessoa_usuario(
            _Session(None), uuid4(), uuid4()
        )


def test_future_authorization_uses_canonical_identity_not_heuristics() -> None:
    source = Path(
        "services/api/operacional/services/identidade_operacional_service.py"
    ).read_text(encoding="utf-8")
    assert "pessoa_usuario_id" in source
    assert "RequisicaoResponsabilidadeHistorico.pessoa_usuario_id" in source
    assert "func.lower" not in source
    assert ".cpf" not in source
    assert ".nome" not in source
