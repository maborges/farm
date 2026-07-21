"""
SOIL-PLAN-EXEC-04I — Prova de que operações agrícolas novas não vazam para o
módulo financeiro genérico (dashboard financeiro e Livro Caixa/Carnê-Leão).

Antes de 04I, Despesa(origem_tipo="OPERACAO_AGRICOLA") nascia com status="PAGO" e era
lida sem filtro de origem por `DashboardService` (total_pago_mes) e `RelatorioService`
(Livro Caixa RFB). A partir de 04I, a criação dessa despesa foi removida — este teste
prova a ausência de vazamento diretamente nesses dois serviços, não apenas na ausência
do registro em si.
"""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from test_operational_workflow_governance_step03 import (
    _criar_cultivo,
    _criar_production_unit,
)

from agricola.operacoes.schemas import OperacaoAgricolaCreate
from agricola.operacoes.service import OperacaoService
from agricola.safras.models import Safra
from financeiro.services.dashboard_service import DashboardService
from financeiro.services.relatorio_service import RelatorioService


@pytest.mark.asyncio
async def test_operacao_nova_nao_aumenta_total_pago_mes_do_dashboard_financeiro(
    session: AsyncSession,
    tenant_id: str,
    unidade_produtiva_id: str,
    talhao_id: str,
):
    dashboard_svc = DashboardService(session, tenant_id)
    resumo_antes = await dashboard_svc.resumo(unidade_produtiva_id=unidade_produtiva_id)

    safra = Safra(
        id=uuid4(),
        tenant_id=tenant_id,
        ano_safra="2025/26",
        cultura="MILHO",
        status="COLHEITA",
    )
    session.add(safra)
    await session.commit()

    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, talhao_id)

    service = OperacaoService(session, tenant_id)
    await service.criar(
        OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita — sem vazamento financeiro",
            data_realizada=date.today(),
            area_aplicada_ha=50.0,
            custo_total=7500.0,
            insumos=[],
        )
    )

    resumo_depois = await dashboard_svc.resumo(unidade_produtiva_id=unidade_produtiva_id)
    assert resumo_depois.total_pago_mes == resumo_antes.total_pago_mes
    assert resumo_depois.total_a_pagar == resumo_antes.total_a_pagar


@pytest.mark.asyncio
async def test_operacao_nova_nao_aparece_no_livro_caixa(
    session: AsyncSession,
    tenant_id: str,
    unidade_produtiva_id: str,
    talhao_id: str,
):
    hoje = date.today()
    relatorio_svc = RelatorioService(session, tenant_id)
    livro_antes = await relatorio_svc.livro_caixa(
        competencia_inicio=hoje.replace(day=1),
        competencia_fim=hoje,
        unidade_produtiva_id=unidade_produtiva_id,
    )

    safra = Safra(
        id=uuid4(),
        tenant_id=tenant_id,
        ano_safra="2025/26",
        cultura="MILHO",
        status="COLHEITA",
    )
    session.add(safra)
    await session.commit()

    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, talhao_id)

    service = OperacaoService(session, tenant_id)
    await service.criar(
        OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita — sem linha no livro caixa",
            data_realizada=hoje,
            area_aplicada_ha=50.0,
            custo_total=3300.0,
            insumos=[],
        )
    )

    livro_depois = await relatorio_svc.livro_caixa(
        competencia_inicio=hoje.replace(day=1),
        competencia_fim=hoje,
        unidade_produtiva_id=unidade_produtiva_id,
    )

    # Nenhuma nova linha/valor de despesa deve surgir no Livro Caixa por causa da operação.
    assert livro_depois.total_despesas == livro_antes.total_despesas
    assert len(livro_depois.grupos) == len(livro_antes.grupos)
