"""
Testes para SOIL-PLAN-EXEC-04G/04I — Reversão econômica transacional da operação agrícola.

Valida que o cancelamento de uma OperacaoAgricola (hard_delete) reverte, na mesma
transação e de forma idempotente:
1. Estoque (movimentos SAIDA revertidos via DEVOLUCAO já existente)
2. CostAllocation vinculado às execuções da operação (removido)
3. Despesa(origem_tipo="OPERACAO_AGRICOLA") histórica, se existir (neutralizada:
   ativo=False, status=CANCELADO) — a partir de 04I, operações novas não criam mais
   essa despesa, então a ausência dela é o cenário normal; a neutralização permanece
   apenas para compatibilidade com dados antigos.

E que dashboard/DRE deixam de considerar o custo da operação cancelada.
"""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_production_unit,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)

from agricola.custos.models import CostAllocation
from agricola.dashboard.service import DashboardAgricolaService
from agricola.dre.service import DREAgricolaV1Service
from agricola.operacoes.models import OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaCreate, OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from core.exceptions import EntityNotFoundError
from core.services.analytics_request_cache import clear_analytics_request_cache
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta


async def _contexto(session: AsyncSession):
    tenant_id = uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    safra.status = "COLHEITA"
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    plano = PlanoConta(
        tenant_id=tenant_id,
        codigo=f"3.{str(uuid4())[:6]}",
        nome="Custeio",
        tipo="DESPESA",
        categoria_rfb="CUSTEIO",
        natureza="ANALITICA",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    return tenant_id, unidade_id, area_id, safra, cultivo_id, pu


async def _criar_operacao_realizada(
    session: AsyncSession, *, tenant_id, safra_id, talhao_id, custo_total: float, descricao: str
):
    service = OperacaoService(session, tenant_id)
    operacao_create = OperacaoAgricolaCreate(
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo="COLHEITA",
        descricao=descricao,
        data_realizada=date.today(),
        area_aplicada_ha=10.0,
        custo_total=custo_total,
        insumos=[],
    )
    return await service.criar(operacao_create)


async def _despesa_da_operacao(session: AsyncSession, operacao_id) -> Despesa | None:
    stmt = select(Despesa).where(
        Despesa.origem_id == operacao_id, Despesa.origem_tipo == "OPERACAO_AGRICOLA"
    )
    return (await session.execute(stmt)).scalars().first()


async def _criar_despesa_legada(
    session: AsyncSession, *, tenant_id, unidade_id, operacao_id, valor_total: float
) -> Despesa:
    """Simula uma Despesa(OPERACAO_AGRICOLA) criada antes de 04I (dado histórico)."""
    plano = PlanoConta(
        tenant_id=tenant_id,
        codigo=f"3.{str(uuid4())[:6]}",
        nome="Custeio legado",
        tipo="DESPESA",
        categoria_rfb="CUSTEIO",
        natureza="ANALITICA",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    despesa = Despesa(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano.id,
        descricao="Despesa histórica pré-04I",
        valor_total=valor_total,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        data_pagamento=date.today(),
        status="PAGO",
        origem_id=operacao_id,
        origem_tipo="OPERACAO_AGRICOLA",
        ativo=True,
    )
    session.add(despesa)
    await session.commit()
    await session.refresh(despesa)
    return despesa


async def _allocations_da_operacao(
    session: AsyncSession, tenant_id, operacao_id
) -> list[CostAllocation]:
    exec_ids = (
        await session.execute(
            select(OperacaoExecucao.id).where(OperacaoExecucao.operacao_id == operacao_id)
        )
    ).scalars().all()
    if not exec_ids:
        return []
    return list(
        (
            await session.execute(
                select(CostAllocation).where(
                    CostAllocation.tenant_id == tenant_id,
                    CostAllocation.operation_execution_id.in_(exec_ids),
                )
            )
        )
        .scalars()
        .all()
    )


class TestOperacaoReversaoEconomica:
    """SOIL-PLAN-EXEC-04G: cancelamento reverte estoque + CostAllocation + Despesa."""

    @pytest.mark.asyncio
    async def test_cenario_a_h_cancelamento_operacao_nova_sem_despesa(
        self, session: AsyncSession
    ):
        """Operação nova (pós-04I) não cria despesa; cancelamento reverte apenas allocation."""
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=1000.0, descricao="Op cancelamento simples",
        )

        allocations_antes = await _allocations_da_operacao(session, tenant_id, operacao.id)
        assert len(allocations_antes) == 1
        assert await _despesa_da_operacao(session, operacao.id) is None

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao.id)
        await session.commit()

        # Sem insumos nesta operação, não há SAIDA de estoque a reverter (coberto no FIFO).
        allocations_depois = await _allocations_da_operacao(session, tenant_id, operacao.id)
        assert allocations_depois == []
        assert await _despesa_da_operacao(session, operacao.id) is None

        with pytest.raises(EntityNotFoundError):
            await service.get_or_fail(operacao.id)

    @pytest.mark.asyncio
    async def test_cenario_i_reversao_operacao_historica_neutraliza_despesa_legada(
        self, session: AsyncSession
    ):
        """Despesa(OPERACAO_AGRICOLA) legada (dado pré-04I) segue sendo neutralizada."""
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=1000.0, descricao="Op com despesa legada",
        )
        despesa_legada = await _criar_despesa_legada(
            session, tenant_id=tenant_id, unidade_id=unidade_id,
            operacao_id=operacao.id, valor_total=1000.0,
        )
        assert despesa_legada.ativo is True

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao.id)
        await session.commit()

        assert await _allocations_da_operacao(session, tenant_id, operacao.id) == []
        await session.refresh(despesa_legada)
        assert despesa_legada.ativo is False
        assert despesa_legada.status == "CANCELADO"

    @pytest.mark.asyncio
    async def test_cenario_b_idempotencia_segunda_chamada_nao_gera_efeito_duplicado(
        self, session: AsyncSession
    ):
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=500.0, descricao="Op idempotencia",
        )

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao.id)
        await session.commit()

        with pytest.raises(EntityNotFoundError):
            await service.hard_delete(operacao.id)
        await session.rollback()

        allocations_depois = await _allocations_da_operacao(session, tenant_id, operacao.id)
        assert allocations_depois == []

    @pytest.mark.asyncio
    async def test_cenario_c_multiplas_allocations_reverte_apenas_a_operacao_cancelada(
        self, session: AsyncSession
    ):
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao_1 = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=300.0, descricao="Op C1",
        )
        operacao_2 = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=700.0, descricao="Op C2",
        )

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao_1.id)
        await session.commit()

        assert await _allocations_da_operacao(session, tenant_id, operacao_1.id) == []
        allocations_2 = await _allocations_da_operacao(session, tenant_id, operacao_2.id)
        assert len(allocations_2) == 1
        assert float(allocations_2[0].amount) == 700.0

    @pytest.mark.asyncio
    async def test_cenario_d_isolamento_multitenant(self, session: AsyncSession):
        tenant_a, _, area_a, safra_a, _, _ = await _contexto(session)
        tenant_b, _, area_b, safra_b, _, _ = await _contexto(session)

        operacao_a = await _criar_operacao_realizada(
            session, tenant_id=tenant_a, safra_id=safra_a.id, talhao_id=area_a,
            custo_total=400.0, descricao="Op tenant A",
        )
        operacao_b = await _criar_operacao_realizada(
            session, tenant_id=tenant_b, safra_id=safra_b.id, talhao_id=area_b,
            custo_total=900.0, descricao="Op tenant B",
        )

        service_a = OperacaoService(session, tenant_a)
        await service_a.hard_delete(operacao_a.id)
        await session.commit()

        assert await _allocations_da_operacao(session, tenant_a, operacao_a.id) == []
        allocations_b = await _allocations_da_operacao(session, tenant_b, operacao_b.id)
        assert len(allocations_b) == 1
        assert await _despesa_da_operacao(session, operacao_a.id) is None
        assert await _despesa_da_operacao(session, operacao_b.id) is None

    @pytest.mark.asyncio
    async def test_cenario_e_dashboard_reflete_cancelamento(self, session: AsyncSession):
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=600.0, descricao="Op E ativa",
        )
        operacao_cancelada = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=400.0, descricao="Op E cancelada",
        )

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo_antes = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo_antes.financeiro.custo_operacoes_total == 1000.0

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao_cancelada.id)
        await session.commit()

        resumo_depois = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo_depois.financeiro.total_operacoes == 1
        assert resumo_depois.financeiro.custo_operacoes_total == 600.0

    @pytest.mark.asyncio
    async def test_cenario_f_dre_reflete_cancelamento(self, session: AsyncSession):
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=1200.0, descricao="Op F",
        )

        dre_service = DREAgricolaV1Service(session, tenant_id)
        dre_antes = await dre_service.gerar(safra_id=safra.id, production_unit_id=pu.id)
        assert dre_antes.custos_diretos == 1200.0

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao.id)
        await session.commit()
        clear_analytics_request_cache()

        dre_depois = await dre_service.gerar(safra_id=safra.id, production_unit_id=pu.id)
        assert dre_depois.custos_diretos == 0.0
        despesa_itens = dre_depois.despesas_operacionais_detalhe.itens
        assert not any(item.origem_id == operacao.id for item in despesa_itens)

    @pytest.mark.asyncio
    async def test_cenario_g_reexecucao_apos_cancelamento(self, session: AsyncSession):
        """Cancelar uma operação e criar uma nova para a mesma safra/talhão não gera duplicidade."""
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao_1 = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=1000.0, descricao="Op G original",
        )

        service = OperacaoService(session, tenant_id)
        await service.hard_delete(operacao_1.id)
        await session.commit()

        operacao_2 = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=850.0, descricao="Op G reexecutada",
        )

        allocations_2 = await _allocations_da_operacao(session, tenant_id, operacao_2.id)
        assert len(allocations_2) == 1
        assert float(allocations_2[0].amount) == 850.0

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.total_operacoes == 1
        assert resumo.financeiro.custo_operacoes_total == 850.0

    @pytest.mark.asyncio
    async def test_atualizar_status_sai_de_realizada_reverte_efeitos(self, session: AsyncSession):
        """Mudar o status de REALIZADA para outro valor via atualizar() também reverte."""
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu = await _contexto(session)
        operacao = await _criar_operacao_realizada(
            session, tenant_id=tenant_id, safra_id=safra.id, talhao_id=area_id,
            custo_total=650.0, descricao="Op status revertido",
        )
        assert len(await _allocations_da_operacao(session, tenant_id, operacao.id)) == 1

        service = OperacaoService(session, tenant_id)
        operacao_atualizada = await service.atualizar(
            operacao.id, OperacaoAgricolaUpdate(status="PLANEJADA")
        )
        await session.commit()

        assert operacao_atualizada.status == "PLANEJADA"
        assert await _allocations_da_operacao(session, tenant_id, operacao.id) == []
        assert await _despesa_da_operacao(session, operacao.id) is None
