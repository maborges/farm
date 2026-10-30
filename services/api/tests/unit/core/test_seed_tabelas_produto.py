from __future__ import annotations

from uuid import uuid4

import pytest

from core.cadastros.produtos.models import CategoriaProduto, Marca, ModeloProduto
from scripts.initial_load import seed_tabelas_produto


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _ProductSeedSession:
    def __init__(self, events):
        self.events = events
        self.entities_queried = []
        self.added = []
        self.existing = {}
        self.commit_count = 0

    async def execute(self, statement):
        self.events.append("query")
        entity = statement.column_descriptions[0]["entity"]
        self.entities_queried.append(entity)
        params = statement.compile().params
        if entity is Marca:
            key = params["nome_1"]
        elif entity is ModeloProduto:
            key = (params["marca_id_1"], params["nome_1"])
        else:
            return _Result(None)
        return _Result(self.existing.get((entity, key)))

    def add(self, obj):
        if isinstance(obj, Marca):
            obj.id = uuid4()
            key = obj.nome
        elif isinstance(obj, ModeloProduto):
            key = (obj.marca_id, obj.nome)
        else:
            key = None
        self.added.append(obj)
        if key is not None:
            self.existing[(type(obj), key)] = obj

    async def flush(self):
        pass

    async def commit(self):
        self.commit_count += 1


@pytest.mark.asyncio
async def test_execucao_seletiva_carrega_marcas_modelos_sem_tocar_categorias(
    monkeypatch, capsys
):
    from core import model_registry

    events = []
    session = _ProductSeedSession(events)

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(seed_tabelas_produto, "async_session_maker", SessionContext)
    monkeypatch.setattr(
        model_registry, "register_models", lambda: events.append("register_models")
    )
    monkeypatch.setattr(
        "sqlalchemy.orm.configure_mappers",
        lambda: events.append("configure_mappers"),
    )

    await seed_tabelas_produto.seed(only_marcas_modelos=True)
    added_count = len(session.added)
    first_run_query_count = len(session.entities_queried)
    await seed_tabelas_produto.seed(only_marcas_modelos=True)
    capsys.readouterr()

    assert set(session.entities_queried) == {Marca, ModeloProduto}
    assert CategoriaProduto not in session.entities_queried
    assert len(session.added) == added_count
    assert added_count > 0
    assert first_run_query_count == len(session.entities_queried) // 2
    assert all(obj.tenant_id is None and obj.sistema is True for obj in session.added)
    assert all(isinstance(obj, Marca | ModeloProduto) for obj in session.added)

    marcas = {obj.nome: obj for obj in session.added if isinstance(obj, Marca)}
    modelos = [obj for obj in session.added if isinstance(obj, ModeloProduto)]
    assert len(marcas) > 0
    assert modelos
    assert all(obj.marca_id in {marca.id for marca in marcas.values()} for obj in modelos)
    assert session.commit_count == 2
    assert events[:3] == ["register_models", "configure_mappers", "query"]
    second_run_start = first_run_query_count + 2
    assert events[second_run_start : second_run_start + 2] == [
        "register_models",
        "configure_mappers",
    ]


def test_registro_orm_do_projeto_configura_os_mappers_do_seed():
    from sqlalchemy.orm import configure_mappers

    from core.model_registry import register_models

    register_models()
    configure_mappers()
