from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.planejamento_operacional.models import (
    PlanoOperacional,
    PlanoOperacionalTarefa,
    PlanoOperacionalTarefaInsumo,
)
from agricola.planejamento_operacional.service import PlanoOperacionalService
from agricola.tarefas.models import SafraTarefa
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


async def _criar_tarefa(session: AsyncSession, tenant_id: uuid.UUID, safra_id: uuid.UUID, talhao_id: uuid.UUID) -> SafraTarefa:
    tarefa = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        origem="MANUAL",
        tipo="ADUBACAO_NITROGENIO",
        descricao="Tarefa de teste",
        status="APROVADA",
    )
    session.add(tarefa)
    await session.flush()
    return tarefa


async def _criar_produto(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from core.cadastros.produtos.models import Produto

    produto = Produto(tenant_id=tenant_id, nome="Ureia Coberta", tipo="INSUMO", unidade_medida="KG")
    session.add(produto)
    await session.flush()
    return produto.id


@pytest.mark.asyncio
async def test_comparativo_orcamento_sinaliza_excedente_sem_bloquear(session: AsyncSession):
    """OPERATIONS-GAP-01 §21.9: plano operacional e orçamento de safra são fontes
    desconectadas — este teste garante que o comparativo detecta corretamente
    quando o plano excede o orçamento, sem impedir a aprovação."""
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, talhao_id)
    produto_id = await _criar_produto(session, tenant_id)

    session.add(ItemOrcamentoSafra(
        tenant_id=tenant_id,
        safra_id=safra.id,
        categoria="FERTILIZANTE",
        descricao="Ureia coberta (orçamento)",
        quantidade=100,
        unidade="kg",
        custo_unitario=10,
        custo_total=1000,
    ))

    plano = PlanoOperacional(
        tenant_id=tenant_id,
        safra_id=safra.id,
        nome="Plano de teste",
        data_inicio_prevista=date.today(),
    )
    session.add(plano)
    await session.flush()

    item = PlanoOperacionalTarefa(
        tenant_id=tenant_id,
        plano_operacional_id=plano.id,
        safra_tarefa_id=tarefa.id,
        status_planejamento="PRONTA",
    )
    session.add(item)
    await session.flush()

    session.add(PlanoOperacionalTarefaInsumo(
        tenant_id=tenant_id,
        plano_operacional_tarefa_id=item.id,
        produto_id=produto_id,
        unidade_dose="KG",
        quantidade_planejada=150,
        custo_total_estimado=1500,
        fonte_custo="MANUAL",
    ))
    await session.commit()

    svc = PlanoOperacionalService(session, tenant_id)
    comparativo = await svc.comparar_com_orcamento(plano.id)

    assert comparativo["custo_estimado_plano"] == pytest.approx(1500)
    assert comparativo["orcamento_previsto_safra"] == pytest.approx(1000)
    assert comparativo["excede_orcamento"] is True
    assert comparativo["percentual_excedente"] == pytest.approx(50.0)

    # Não bloqueia: avancar_status até APROVADO deve funcionar normalmente.
    await svc.avancar_status(plano.id, "EM_ANALISE")
    await svc.avancar_status(plano.id, "PARCIALMENTE_PRONTO")
    aprovado = await svc.avancar_status(plano.id, "APROVADO")
    assert aprovado.status == "APROVADO"
