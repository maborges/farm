import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.a1_planejamento.schemas import ItemOrcamentoCreate, ItemOrcamentoUpdate
from agricola.a1_planejamento.service import PlanejamentoService


def _result(*, scalars_first=None, scalars_all=None):
    scalars = MagicMock()
    scalars.first.return_value = scalars_first
    scalars.all.return_value = scalars_all or []
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _safra(tenant_id, safra_id):
    return SimpleNamespace(id=safra_id, tenant_id=tenant_id)


# ── custo_unitario_efetivo (property do model, sem DB) ─────────────────────

def test_custo_unitario_efetivo_prioriza_ajustado_sobre_snapshot_e_legado():
    item = ItemOrcamentoSafra(
        custo_unitario=10.0,
        custo_unitario_snapshot=8.0,
        custo_unitario_ajustado=6.0,
    )
    assert item.custo_unitario_efetivo == 6.0


def test_custo_unitario_efetivo_usa_snapshot_se_nao_houver_ajuste():
    item = ItemOrcamentoSafra(custo_unitario=10.0, custo_unitario_snapshot=8.0)
    assert item.custo_unitario_efetivo == 8.0


def test_custo_unitario_efetivo_cai_para_legado_manual():
    item = ItemOrcamentoSafra(custo_unitario=10.0)
    assert item.custo_unitario_efetivo == 10.0


# ── criar_item ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_criar_item_manual_preserva_comportamento_atual():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(scalars_first=_safra(tenant_id, safra_id)))
    session.refresh = AsyncMock(side_effect=lambda item: None)

    service = PlanejamentoService(session, tenant_id)
    data = ItemOrcamentoCreate(
        categoria="SEMENTE",
        descricao="Semente soja",
        quantidade=10,
        unidade="sc",
        origem_tipo="MANUAL",
        custo_unitario=150.0,
    )
    item = await service.criar_item(safra_id, data)

    assert item.origem_tipo == "MANUAL"
    assert item.custo_unitario_snapshot is None
    assert item.custo_total == 1500.0


@pytest.mark.asyncio
async def test_criar_item_com_origem_produto_grava_snapshot_imutavel():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    produto_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(scalars_first=_safra(tenant_id, safra_id)))
    session.refresh = AsyncMock(side_effect=lambda item: None)

    with patch("agricola.a1_planejamento.service.SnapshotCustoService") as MockSnapshot:
        MockSnapshot.return_value.capturar = AsyncMock(
            return_value=(Decimal("42.50"), {"produto_id": str(produto_id), "preco_medio": "42.50"})
        )
        service = PlanejamentoService(session, tenant_id)
        data = ItemOrcamentoCreate(
            categoria="FERTILIZANTE",
            descricao="Ureia",
            quantidade=5,
            unidade="sc",
            origem_tipo="PRODUTO",
            origem_id=produto_id,
        )
        item = await service.criar_item(safra_id, data)

    assert item.origem_tipo == "PRODUTO"
    assert item.origem_id == produto_id
    assert float(item.custo_unitario_snapshot) == 42.5
    assert item.custo_total == 212.5  # 5 * 42.5, não depende de custo_unitario do payload
    assert item.snapshot_data["preco_medio"] == "42.50"
    assert item.capturado_em is not None


@pytest.mark.asyncio
async def test_criar_item_snapshot_nao_muda_se_cadastro_mestre_mudar_depois():
    """Uma vez gravado, o snapshot é congelado — mudanças futuras no Produto
    não afetam o item já criado (o item nem referencia o objeto Produto)."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    produto_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(scalars_first=_safra(tenant_id, safra_id)))
    session.refresh = AsyncMock(side_effect=lambda item: None)

    with patch("agricola.a1_planejamento.service.SnapshotCustoService") as MockSnapshot:
        MockSnapshot.return_value.capturar = AsyncMock(
            return_value=(Decimal("100.00"), {"preco_medio": "100.00"})
        )
        service = PlanejamentoService(session, tenant_id)
        data = ItemOrcamentoCreate(
            categoria="FERTILIZANTE", descricao="NPK", quantidade=1, unidade="sc",
            origem_tipo="PRODUTO", origem_id=produto_id,
        )
        item = await service.criar_item(safra_id, data)

    custo_unitario_snapshot_original = item.custo_unitario_snapshot

    # Produto mudou de preço no cadastro mestre depois — não existe qualquer
    # referência viva ao objeto Produto no item, então nada aqui pode mudar.
    assert item.custo_unitario_snapshot == custo_unitario_snapshot_original


# ── atualizar_item ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_atualizar_item_ajuste_manual_nao_altera_origem_nem_snapshot():
    tenant_id = uuid.uuid4()
    item_id = uuid.uuid4()
    produto_id = uuid.uuid4()

    item = ItemOrcamentoSafra(
        id=item_id,
        tenant_id=tenant_id,
        safra_id=uuid.uuid4(),
        categoria="FERTILIZANTE",
        descricao="Ureia",
        quantidade=5,
        unidade="sc",
        origem_tipo="PRODUTO",
        origem_id=produto_id,
        custo_unitario=42.5,
        custo_unitario_snapshot=42.5,
        snapshot_data={"preco_medio": "42.50"},
        custo_total=212.5,
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(scalars_first=item))
    session.refresh = AsyncMock(side_effect=lambda i: None)

    service = PlanejamentoService(session, tenant_id)
    data = ItemOrcamentoUpdate(custo_unitario_ajustado=50.0)
    atualizado = await service.atualizar_item(item_id, data)

    assert atualizado.origem_tipo == "PRODUTO"
    assert atualizado.origem_id == produto_id
    assert float(atualizado.custo_unitario_snapshot) == 42.5  # snapshot preservado
    assert atualizado.custo_unitario_ajustado == 50.0
    assert atualizado.custo_total == 250.0  # 5 * 50.0 (efetivo = ajustado)


@pytest.mark.asyncio
async def test_atualizar_item_tenta_trocar_origem_e_e_ignorado():
    tenant_id = uuid.uuid4()
    item_id = uuid.uuid4()

    item = ItemOrcamentoSafra(
        id=item_id, tenant_id=tenant_id, safra_id=uuid.uuid4(),
        categoria="SEMENTE", descricao="Semente", quantidade=1, unidade="sc",
        origem_tipo="MANUAL", custo_unitario=10.0, custo_total=10.0,
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(scalars_first=item))
    session.refresh = AsyncMock(side_effect=lambda i: None)

    service = PlanejamentoService(session, tenant_id)
    data = ItemOrcamentoUpdate.model_construct(
        origem_tipo="PRODUTO", origem_id=uuid.uuid4()
    )
    atualizado = await service.atualizar_item(item_id, data)

    # origem_tipo/origem_id imutáveis pós-criação — update ignora esses campos
    assert atualizado.origem_tipo == "MANUAL"
    assert atualizado.origem_id is None


# ── Realizado via CostAllocation ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_realizado_soma_cost_allocation_por_categoria_e_fonte():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    pu_id = uuid.uuid4()

    allocations = [
        SimpleNamespace(amount=100.0, cost_category="INSUMO", source="APONTAMENTO_FROTA", fin_rateio_id=None),
        SimpleNamespace(amount=50.0, cost_category="MAO_OBRA", source="RH_DIARIA", fin_rateio_id=None),
        SimpleNamespace(amount=30.0, cost_category="OUTROS", source="FIN_RATEIO", fin_rateio_id=uuid.uuid4()),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalars_all=[pu_id]),
            _result(scalars_all=allocations),
        ]
    )

    service = PlanejamentoService(session, tenant_id)
    realizado = await service._get_realizado(safra_id, area_ha=10.0)

    assert realizado.custo_operacoes == 150.0
    assert realizado.custo_rateios == 30.0
    assert realizado.custo_total == 180.0
    assert realizado.custo_por_ha == 18.0
    categorias = {c.categoria: c.custo_total for c in realizado.por_categoria}
    assert categorias == {"INSUMO": 100.0, "MAO_OBRA": 50.0, "OUTROS": 30.0}


@pytest.mark.asyncio
async def test_get_realizado_sem_production_units_cai_no_fallback_legado():
    """Sem production_units (e portanto sem CostAllocation possível), cai no
    fallback OperacaoAgricola+Rateio em vez de reportar zero indevidamente."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalars_all=[]),  # production units
            _result(scalars_all=[]),  # operacoes_agricolas (fallback)
            _result(scalars_all=[]),  # rateios (fallback)
        ]
    )

    service = PlanejamentoService(session, tenant_id)
    realizado = await service._get_realizado(safra_id, area_ha=10.0)

    assert realizado.custo_total == 0.0
    assert realizado.por_categoria == []


@pytest.mark.asyncio
async def test_get_realizado_sem_cost_allocation_mas_com_production_units_usa_fallback():
    """Caso real encontrado em staging: production_units existem, mas
    CostAllocation está vazio para elas (operações realizadas antes da
    integração, ou dado inserido fora da service layer). Não deve reportar
    R$ 0,00 de realizado — cai para OperacaoAgricola+Rateio."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    pu_id = uuid.uuid4()

    operacoes = [SimpleNamespace(custo_total=6200.0, tipo="ADUBAÇÃO")]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalars_all=[pu_id]),   # production units
            _result(scalars_all=[]),        # CostAllocation (vazio)
            _result(scalars_all=operacoes), # fallback: operacoes_agricolas
            _result(scalars_all=[]),        # fallback: rateios
        ]
    )

    service = PlanejamentoService(session, tenant_id)
    realizado = await service._get_realizado(safra_id, area_ha=10.0)

    assert realizado.custo_total == 6200.0
    assert realizado.custo_operacoes == 6200.0
