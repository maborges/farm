from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.cadastros.produtos.models import (
    CategoriaProduto,
    Marca,
    ModeloProduto,
    Produto,
)
from scripts.initial_load import seed_produtos


def _load_product_catalog_constant(name):
    source = Path(__file__).resolve().parents[3] / "scripts/initial_load/seed_tabelas_produto.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


MARCAS = _load_product_catalog_constant("MARCAS")
MODELOS = _load_product_catalog_constant("MODELOS")
CATEGORIAS = _load_product_catalog_constant("CATEGORIAS")


class _Result:
    def __init__(self, values):
        self.values = values if isinstance(values, list) else [values]

    def scalars(self):
        return self

    def all(self):
        return self.values

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None


class _ProductLoadSession:
    def __init__(self, catalogs):
        self.catalogs = catalogs
        self.queries = []
        self.added = []
        self.pending_products = {}
        self.products = {}
        self.tenant_products = {
            "SEM-SOJA-P10T20": SimpleNamespace(
                codigo_interno="SEM-SOJA-P10T20", tenant_id=uuid4()
            )
        }
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, statement):
        if hasattr(self, "events"):
            self.events.append("query")
        entity = statement.column_descriptions[0]["entity"]
        compiled = statement.compile()
        sql = str(compiled)
        params = compiled.params
        self.queries.append((entity, sql, params))
        global_only = "tenant_id IS NULL" in sql

        if entity is Produto:
            code = params["codigo_interno_1"]
            existing = self.products.get(code)
            if existing is None and not global_only:
                existing = self.tenant_products.get(code)
            return _Result(existing)

        records = self.catalogs[entity]
        if not global_only:
            records = records + self.catalogs.get((entity, "tenant"), [])
        return _Result(records)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Produto):
            self.pending_products[obj.codigo_interno] = obj

    async def flush(self):
        for product in self.pending_products.values():
            if product.id is None:
                product.id = uuid4()

    async def commit(self):
        self.products.update(self.pending_products)
        self.pending_products.clear()
        self.commit_count += 1

    async def rollback(self):
        self.pending_products.clear()
        self.rollback_count += 1


def _fake_catalogs(*, missing=(), wrong_model_brand=False):
    missing = set(missing)
    brands = {
        item["nome"]: SimpleNamespace(
            id=uuid4(), nome=item["nome"], tenant_id=None, sistema=True
        )
        for item in MARCAS
    }
    global_brands = [brand for brand in brands.values() if brand.nome not in missing]
    tenant_brands = [
        SimpleNamespace(
            id=uuid4(), nome="Pioneer", tenant_id=uuid4(), sistema=False
        )
    ]

    global_models = []
    for item in MODELOS:
        if (item["marca"], item["nome"]) in missing:
            continue
        marca_id = brands[item["marca"]].id
        if wrong_model_brand and item["nome"] == "Rimula R4 X 15W-40":
            marca_id = brands["Mobil"].id
        global_models.append(
            SimpleNamespace(
                id=uuid4(),
                nome=item["nome"],
                marca_id=marca_id,
                tenant_id=None,
                sistema=True,
            )
        )
    tenant_models = [
        SimpleNamespace(
            id=uuid4(),
            nome="Rimula R4 X 15W-40",
            marca_id=brands["Shell"].id,
            tenant_id=uuid4(),
            sistema=False,
        )
    ]

    global_categories = {}
    for item in CATEGORIAS:
        if item["parent"] is None:
            global_categories[item["nome"]] = SimpleNamespace(
                id=uuid4(), nome=item["nome"], tenant_id=None, sistema=True
            )
        else:
            parent = global_categories[item["parent"]]
            global_categories[item["nome"]] = SimpleNamespace(
                id=uuid4(),
                nome=item["nome"],
                parent_id=parent.id,
                tenant_id=None,
                sistema=True,
            )
    global_categories = {
        name: category
        for name, category in global_categories.items()
        if name not in missing
    }
    tenant_categories = [
        SimpleNamespace(
            id=uuid4(), nome="Sementes", tenant_id=uuid4(), sistema=False
        )
    ]

    return {
        Marca: global_brands,
        (Marca, "tenant"): tenant_brands,
        ModeloProduto: global_models,
        (ModeloProduto, "tenant"): tenant_models,
        CategoriaProduto: list(global_categories.values()),
        (CategoriaProduto, "tenant"): tenant_categories,
        "brands_by_name": brands,
        "models": global_models,
        "categories_by_name": global_categories,
    }


def _bind_session(monkeypatch, session, events=None):
    class SessionContext:
        async def __aenter__(self):
            if events is not None:
                events.append("session_enter")
            return session

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(seed_produtos, "async_session_maker", SessionContext)


@pytest.mark.asyncio
async def test_seed_produtos_registra_orm_filtra_global_e_eh_idempotente(
    monkeypatch, capsys
):
    from sqlalchemy.orm import configure_mappers

    from core import model_registry

    catalogs = _fake_catalogs()
    session = _ProductLoadSession(catalogs)
    events = []
    session.events = events
    _bind_session(monkeypatch, session, events)
    register_models = model_registry.register_models

    def register_and_record():
        events.append("register_models")
        register_models()

    configure = configure_mappers

    def configure_and_record():
        events.append("configure_mappers")
        configure()

    monkeypatch.setattr(model_registry, "register_models", register_and_record)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", configure_and_record)

    await seed_produtos.seed()
    first_count = len(session.products)
    await seed_produtos.seed()
    capsys.readouterr()

    assert len(seed_produtos.PRODUTOS_ELEGIVEIS) == 23
    assert len(session.products) == first_count == 23
    assert session.commit_count == 2
    assert session.rollback_count == 0
    session_enter = events.index("session_enter")
    first_query = events.index("query")
    assert events.index("register_models") < events.index("configure_mappers")
    assert events.index("configure_mappers") < session_enter < first_query

    assert all(
        "tenant_id IS NULL" in sql
        for entity, sql, _params in session.queries
        if entity in {Marca, ModeloProduto, CategoriaProduto, Produto}
    )
    assert not any(isinstance(obj, CategoriaProduto) for obj in session.added)
    assert all(
        product.tenant_id is None and product.ativo
        for product in session.products.values()
    )

    brands_by_name = catalogs["brands_by_name"]
    models = catalogs["models"]
    categories_by_name = catalogs["categories_by_name"]
    entries_by_code = {
        item["codigo_interno"]: item for item in seed_produtos.PRODUTOS_ELEGIVEIS
    }
    for code, product in session.products.items():
        source = entries_by_code[code]
        if source.get("marca"):
            assert product.marca_id == brands_by_name[source["marca"]].id
        if source.get("modelo"):
            source_brand = brands_by_name[source["marca"]]
            model = next(
                model
                for model in models
                if model.nome == source["modelo"]
                and model.marca_id == source_brand.id
            )
            assert product.modelo_id == model.id
            assert model.tenant_id is None
        if source.get("categoria"):
            assert product.categoria_id == categories_by_name[source["categoria"]].id

    assert "SEM-SOJA-P10T20" in session.products
    assert all(
        code not in session.products for code in seed_produtos.PENDENCIAS_PRODUTOS
    )
    assert all(product.tipo != "DEFENSIVO" for product in session.products.values())
    regulatory_fields = {
        "registro_mapa",
        "classe_toxicologica",
        "periodo_carencia_dias",
        "intervalo_reentrada_horas",
        "epi_obrigatorio",
    }
    for item in seed_produtos.PRODUTOS_ELEGIVEIS:
        details = item.get("detalhe_agricola", {})
        assert not regulatory_fields.intersection(details)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("missing", "wrong_model_brand", "expected_message"),
    [
        ({"Pioneer"}, False, "Marca global 'Pioneer' não encontrada"),
        ({("Shell", "Rimula R4 X 15W-40")}, False, "Modelo global"),
        (set(), True, "Modelo global"),
        ({"Minerais e Sal"}, False, "Categoria global 'Minerais e Sal' não encontrada"),
    ],
)
async def test_seed_produtos_falha_e_faz_rollback_para_dependencia_invalida(
    monkeypatch, capsys, missing, wrong_model_brand, expected_message
):
    catalogs = _fake_catalogs(missing=missing, wrong_model_brand=wrong_model_brand)
    session = _ProductLoadSession(catalogs)
    _bind_session(monkeypatch, session)

    with pytest.raises(ValueError, match=expected_message):
        await seed_produtos.seed()
    capsys.readouterr()

    assert session.commit_count == 0
    assert session.rollback_count == 1
    assert session.pending_products == {}
    assert session.products == {}
    if missing == {"Pioneer"}:
        assert not any(isinstance(obj, Produto) for obj in session.added)
    else:
        assert any(isinstance(obj, Produto) for obj in session.added)


def test_produtos_pendentes_nao_fazem_parte_da_carga_global():
    elegiveis = {item["codigo_interno"] for item in seed_produtos.PRODUTOS_ELEGIVEIS}

    assert len(seed_produtos.PRODUTOS) == 31
    assert len(elegiveis) == 23
    assert len(seed_produtos.PENDENCIAS_PRODUTOS) == 8
    assert set(seed_produtos.PENDENCIAS_PRODUTOS).isdisjoint(elegiveis)
    assert {
        item["codigo_interno"] for item in seed_produtos.PRODUTOS
    } - elegiveis == set(seed_produtos.PENDENCIAS_PRODUTOS)
    assert "SEM-MILHO-NK7059" in seed_produtos.PENDENCIAS_PRODUTOS
    assert "DEF-PAR-GRX-1L" in seed_produtos.PENDENCIAS_PRODUTOS
