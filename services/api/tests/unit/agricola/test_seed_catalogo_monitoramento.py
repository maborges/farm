from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from agricola.monitoramento.service import MonitoramentoCatalogoService
from scripts.initial_load.seed_catalogo_monitoramento import ENTRADAS, _seed_catalogo


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _SeedSession:
    def __init__(self):
        self.entries = []
        self.added = []
        self.statements = []
        self.commit_count = 0

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result([
            (entry.tipo, entry.nome_popular, entry.cultura)
            for entry in self.entries
        ])

    def add(self, entry):
        self.added.append(entry)
        self.entries.append(entry)

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_seed_monitoramento_insere_registros_globais_e_eh_idempotente():
    session = _SeedSession()

    inseridos, existentes = await _seed_catalogo(session)

    assert inseridos == len(ENTRADAS)
    assert existentes == 0
    assert len(session.added) == len(ENTRADAS)
    assert all(entry.tenant_id is None for entry in session.added)
    assert all(entry.is_system is True for entry in session.added)
    assert all(entry.nde_padrao is None for entry in session.added)

    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "monitoramento_catalogo.tenant_id IS NULL" in sql
    assert "monitoramento_catalogo.is_system IS true" in sql

    inseridos, existentes = await _seed_catalogo(session)

    assert inseridos == 0
    assert existentes == len(ENTRADAS)
    assert len(session.added) == len(ENTRADAS)
    assert session.commit_count == 2


@pytest.mark.asyncio
async def test_catalogo_nao_expoe_registro_system_vinculado_a_outro_tenant():
    class _ListResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class _Session:
        def __init__(self):
            self.statement = None

        async def execute(self, statement):
            self.statement = statement
            return _ListResult()

    session = _Session()
    await MonitoramentoCatalogoService(session, uuid4()).listar()

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "monitoramento_catalogo.tenant_id =" in sql
    assert "monitoramento_catalogo.tenant_id IS NULL" in sql
    assert "monitoramento_catalogo.is_system IS true" in sql

