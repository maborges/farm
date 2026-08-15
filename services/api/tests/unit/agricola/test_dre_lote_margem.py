from __future__ import annotations

import uuid

import pytest

from agricola.dre.schemas import DREAgricolaSection, DRESourceItem
from agricola.dre.service import DREAgricolaV1Service


def _item(pu_id, produto_colhido_id, valor, quantidade, unidade="SACA_60KG") -> DRESourceItem:
    return DRESourceItem(
        natureza="RECEITA_OPERACIONAL",
        fonte_oficial="Receita",
        origem_tipo="COMERCIALIZACAO",
        production_unit_id=pu_id,
        valor=valor,
        meta={
            "produto_colhido_id": str(produto_colhido_id),
            "quantidade": quantidade,
            "unidade": unidade,
        },
    )


def _custo_item(pu_id, valor) -> DRESourceItem:
    return DRESourceItem(
        natureza="CUSTO_DIRETO",
        fonte_oficial="CostAllocation",
        production_unit_id=pu_id,
        valor=valor,
    )


def _scope_sem_pu() -> dict:
    return {"production_units": []}


@pytest.mark.asyncio
async def test_rateio_um_lote_absorve_todo_custo():
    service = DREAgricolaV1Service.__new__(DREAgricolaV1Service)
    service.session = None
    service.tenant_id = uuid.uuid4()

    pu_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    receitas = DREAgricolaSection(itens=[_item(pu_id, lote_id, valor=1000.0, quantidade=100.0)])
    custos_diretos = DREAgricolaSection(itens=[_custo_item(pu_id, 300.0)])
    custos_operacionais = DREAgricolaSection(itens=[_custo_item(pu_id, 100.0)])

    margens, sem_vinculo = await service._ratear_custos_por_lote(
        _scope_sem_pu(), receitas, custos_diretos, custos_operacionais
    )

    assert sem_vinculo == 0
    assert len(margens) == 1
    lote = margens[0]
    assert lote.custo_rateado == 400.0
    assert lote.margem == 600.0
    assert lote.margem_percentual == 60.0


@pytest.mark.asyncio
async def test_rateio_proporcional_entre_multiplos_lotes():
    service = DREAgricolaV1Service.__new__(DREAgricolaV1Service)
    service.session = None
    service.tenant_id = uuid.uuid4()

    pu_id = uuid.uuid4()
    lote_a = uuid.uuid4()
    lote_b = uuid.uuid4()
    receitas = DREAgricolaSection(
        itens=[
            _item(pu_id, lote_a, valor=600.0, quantidade=60.0),
            _item(pu_id, lote_b, valor=400.0, quantidade=40.0),
        ]
    )
    custos_diretos = DREAgricolaSection(itens=[_custo_item(pu_id, 500.0)])
    custos_operacionais = DREAgricolaSection(itens=[])

    margens, sem_vinculo = await service._ratear_custos_por_lote(
        _scope_sem_pu(), receitas, custos_diretos, custos_operacionais
    )

    margens_por_id = {m.produto_colhido_id: m for m in margens}
    assert sem_vinculo == 0
    # custo rateado deve somar exatamente ao custo total da PU, sem perda por arredondamento
    assert round(sum(m.custo_rateado for m in margens), 2) == 500.0
    assert margens_por_id[lote_a].custo_rateado == 300.0
    assert margens_por_id[lote_b].custo_rateado == 200.0
    assert margens_por_id[lote_a].margem == 300.0
    assert margens_por_id[lote_b].margem == 200.0


@pytest.mark.asyncio
async def test_rateio_lote_com_quantidade_zero_nao_quebra():
    service = DREAgricolaV1Service.__new__(DREAgricolaV1Service)
    service.session = None
    service.tenant_id = uuid.uuid4()

    pu_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    receitas = DREAgricolaSection(itens=[_item(pu_id, lote_id, valor=500.0, quantidade=0.0)])
    custos_diretos = DREAgricolaSection(itens=[_custo_item(pu_id, 200.0)])
    custos_operacionais = DREAgricolaSection(itens=[])

    margens, sem_vinculo = await service._ratear_custos_por_lote(
        _scope_sem_pu(), receitas, custos_diretos, custos_operacionais
    )

    assert sem_vinculo == 0
    assert len(margens) == 1
    # sem base de rateio (quantidade total da PU é zero), custo rateado fica zero em vez de dividir por zero
    assert margens[0].custo_rateado == 0.0
    assert margens[0].margem == 500.0
