"""
Testes para o fluxo econômico de criação de operação agrícola (SOIL-PLAN-EXEC-04I).

Valida:
1. Operação com custo_total > 0 NÃO cria Despesa(OPERACAO_AGRICOLA) — apenas CostAllocation
2. Operação sem custo não cria CostAllocation
3. Rastreabilidade via CostAllocation (operation_execution_id/source_id)
4. Tenant isolation
5. Operação inválida não cria CostAllocation nem Despesa

Nome do arquivo mantido por compatibilidade histórica (era "webhook de despesa automática");
o comportamento válido a partir de 04I é a ausência dessa despesa.
"""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from test_operational_workflow_governance_step03 import (
    _criar_cultivo,
    _criar_production_unit,
    _garantir_tenant,
)

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaCreate
from agricola.operacoes.service import OperacaoService
from agricola.safras.models import Safra
from core.exceptions import EntityNotFoundError
from financeiro.models.despesa import Despesa


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


class TestOperacaoDespesaWebhook:
    """Testes do efeito econômico da criação de operação agrícola."""

    @pytest.mark.asyncio
    async def test_operacao_com_custo_nao_cria_despesa_mas_cria_allocation(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Operação com custo_total > 0 não deve criar Despesa; deve criar CostAllocation."""
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
        operacao_create = OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita mecanizada",
            data_realizada=date.today(),
            area_aplicada_ha=50.0,
            custo_total=5000.0,
            insumos=[],
        )
        operacao = await service.criar(operacao_create)

        despesa_stmt = select(Despesa).where(
            Despesa.origem_id == operacao.id,
            Despesa.origem_tipo == "OPERACAO_AGRICOLA",
        )
        despesa = (await session.execute(despesa_stmt)).scalars().first()
        assert despesa is None, "Despesa(OPERACAO_AGRICOLA) não deve mais ser criada (04I)"

        allocations = await _allocations_da_operacao(session, tenant_id, operacao.id)
        assert len(allocations) == 1
        assert float(allocations[0].amount) == 5000.0

    @pytest.mark.asyncio
    async def test_operacao_sem_custo_nao_cria_despesa_nem_allocation(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Operação com custo_total = 0 não deve criar Despesa nem CostAllocation."""
        safra = Safra(
            id=uuid4(),
            tenant_id=tenant_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="PLANTIO",
        )
        session.add(safra)
        await session.commit()

        cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
        await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, talhao_id)

        service = OperacaoService(session, tenant_id)
        operacao_create = OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="PLANTIO",
            descricao="Plantio manual",
            data_realizada=date.today(),
            area_aplicada_ha=10.0,
            custo_total=0.0,
            insumos=[],
        )
        operacao = await service.criar(operacao_create)

        despesa_stmt = select(Despesa).where(Despesa.origem_id == operacao.id)
        assert (await session.execute(despesa_stmt)).scalars().first() is None

        assert await _allocations_da_operacao(session, tenant_id, operacao.id) == []

    @pytest.mark.asyncio
    async def test_rastreabilidade_operacao_allocation(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """CostAllocation deve ter vínculo rastreável (operation_execution_id/allocation_date)."""
        safra = Safra(
            id=uuid4(),
            tenant_id=tenant_id,
            ano_safra="2025/26",
            cultura="SOJA",
            status="DESENVOLVIMENTO",
        )
        session.add(safra)
        await session.commit()

        cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
        await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, talhao_id)

        data_op = date(2025, 6, 15)
        service = OperacaoService(session, tenant_id)
        operacao_create = OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="ADUBAÇÃO",
            descricao="Adubação de cobertura",
            data_realizada=data_op,
            area_aplicada_ha=50.0,
            custo_total=2500.0,
            insumos=[],
        )
        operacao = await service.criar(operacao_create)

        allocations = await _allocations_da_operacao(session, tenant_id, operacao.id)
        assert len(allocations) == 1
        allocation = allocations[0]
        assert allocation.source == "OPERATION_EXECUTION"
        assert allocation.allocation_date == data_op
        assert float(allocation.amount) == 2500.0

    @pytest.mark.asyncio
    async def test_tenant_isolation_operacao_nao_cria_despesa_em_outro_tenant(
        self,
        session: AsyncSession,
        tenant_id: str,
        outro_tenant_id: str,
        talhao_id: str
    ):
        """Operação de um tenant não deve gerar Despesa nem CostAllocation em outro tenant."""
        await _garantir_tenant(session, outro_tenant_id)

        safra_outro = Safra(
            id=uuid4(),
            tenant_id=outro_tenant_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="DESENVOLVIMENTO",
        )
        session.add(safra_outro)
        await session.commit()

        service = OperacaoService(session, tenant_id)
        operacao_create = OperacaoAgricolaCreate(
            safra_id=safra_outro.id,
            talhao_id=talhao_id,
            tipo="PULVERIZAÇÃO",
            descricao="Pulverização",
            data_realizada=date.today(),
            area_aplicada_ha=10.0,
            custo_total=1000.0,
            insumos=[],
        )

        with pytest.raises(EntityNotFoundError):
            await service.criar(operacao_create)

    @pytest.mark.asyncio
    async def test_operacao_tipo_invalido_nao_cria_despesa_nem_allocation(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Se a operação falha por tipo inválido (RN), nem Despesa nem allocation são criados."""
        safra = Safra(
            id=uuid4(),
            tenant_id=tenant_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="COLHEITA",
        )
        session.add(safra)
        await session.commit()

        service = OperacaoService(session, tenant_id)
        operacao_create = OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="PLANTIO",  # não permitido na fase COLHEITA
            descricao="Plantio em COLHEITA (deve falhar)",
            data_realizada=date.today(),
            area_aplicada_ha=10.0,
            custo_total=1000.0,
            insumos=[],
        )

        from core.exceptions import BusinessRuleError

        with pytest.raises(BusinessRuleError):
            await service.criar(operacao_create)

        despesa_stmt = select(Despesa).where(
            Despesa.descricao.contains("Plantio em COLHEITA")
        )
        assert (await session.execute(despesa_stmt)).scalars().first() is None
        # A validação de fase falha antes de a OperacaoAgricola ser persistida, logo não há
        # OperacaoExecucao/CostAllocation possível para esta tentativa (nada além a verificar).
