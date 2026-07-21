"""
Testes para dashboard financeiro de safra.

Valida:
1. Agregação de custo (operações + despesas)
2. Agregação de receita (romaneios + receitas)
3. Cálculo de ROI
4. Rastreabilidade (origem_id linkados)
5. Tenant isolation
"""
import uuid
import pytest
from uuid import uuid4
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.exceptions import EntityNotFoundError
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.dashboard.service import DashboardAgricolaService
from agricola.cultivos.models import Cultivo, CultivoArea
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.romaneios.models import RomaneioColheita
from agricola.operacoes.schemas import OperacaoAgricolaCreate
from agricola.romaneios.schemas import RomaneioColheitaCreate
from financeiro.models.despesa import Despesa
from financeiro.models.receita import Receita
from financeiro.models.plano_conta import PlanoConta
from test_operational_workflow_governance_step02 import _garantir_unidade_ha
from test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_cultivo,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


def add_safra_com_area(
    session: AsyncSession,
    *,
    tenant_id,
    talhao_id,
    ano_safra: str,
    cultura: str,
    status: str,
    area_ha: float,
) -> Safra:
    safra = Safra(
        id=uuid4(),
        tenant_id=tenant_id,
        ano_safra=ano_safra,
        cultura=cultura,
        status=status,
    )
    cultivo = Cultivo(
        id=uuid4(),
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultura=cultura,
        status="ATIVO",
    )
    cultivo_area = CultivoArea(
        id=uuid4(),
        tenant_id=tenant_id,
        cultivo_id=cultivo.id,
        area_id=talhao_id,
        area_ha=area_ha,
    )
    session.add_all([safra, cultivo, cultivo_area])
    return safra


class TestDashboardFinanceiroSafra:
    """Testes de agregação financeira de safra."""

    @pytest.mark.asyncio
    async def test_resumo_financeiro_safra_valido(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Dashboard deve retornar agregação correta de custo + receita."""
        # Setup: Criar safra
        safra = add_safra_com_area(
            session,
            tenant_id=tenant_id,
            talhao_id=talhao_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="COLHEITA",
            area_ha=100.0,
        )

        # Criar planos de conta
        plano_despesa = PlanoConta(
            id=uuid4(),
            tenant_id=tenant_id,
            codigo="3.01",
            nome="Custeio",
            tipo="DESPESA",
            categoria_rfb="CUSTEIO",
            natureza="ANALITICA",
            ativo=True
        )
        plano_receita = PlanoConta(
            id=uuid4(),
            tenant_id=tenant_id,
            codigo="4.01",
            nome="Receita Venda",
            tipo="RECEITA",
            categoria_rfb="RECEITA_ATIVIDADE",
            natureza="ANALITICA",
            ativo=True
        )
        session.add_all([plano_despesa, plano_receita])
        await session.commit()

        # Criar operação com custo
        operacao = OperacaoAgricola(
            id=uuid4(),
            tenant_id=tenant_id,
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita",
            data_realizada=date.today(),
            area_aplicada_ha=100.0,
            custo_total=5000.0,  # R$ 5000
            fase_safra="COLHEITA"
        )
        session.add(operacao)
        await session.commit()

        # Criar despesa associada (webhook já a teria criado, simulamos)
        despesa = Despesa(
            id=uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_despesa.id,
            descricao="Colheita — MILHO 2025/26",
            valor_total=5000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            data_pagamento=date.today(),
            status="PAGO",
            origem_id=operacao.id,
            origem_tipo="OPERACAO_AGRICOLA"
        )
        session.add(despesa)
        await session.commit()

        # Criar romaneio com receita
        romaneio = RomaneioColheita(
            id=uuid4(),
            tenant_id=tenant_id,
            safra_id=safra.id,
            talhao_id=talhao_id,
            data_colheita=date.today(),
            peso_bruto_kg=60000.0,  # 60 toneladas
            tara_kg=0.0,
            umidade_pct=14.0,
            impureza_pct=1.0,
            preco_saca=100.0,  # R$ 100/saca
            peso_liquido_kg=60000.0,
            desconto_umidade_kg=0.0,
            desconto_impureza_kg=0.0,
            peso_liquido_padrao_kg=60000.0,
            sacas_60kg=1000.0,  # 1000 sacas
            receita_total=100000.0  # 1000 sacas × R$ 100
        )
        session.add(romaneio)
        await session.commit()

        # Criar receita associada (webhook já a teria criado, simulamos)
        receita = Receita(
            id=uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_receita.id,
            descricao="Venda de grãos — MILHO 2025/26",
            valor_total=100000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            data_recebimento=date.today(),
            status="RECEBIDO",
            origem_id=romaneio.id,
            origem_tipo="ROMANEIO_COLHEITA"
        )
        session.add(receita)
        await session.commit()

        # Act
        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)

        # Assert
        assert resumo.id == safra.id
        assert resumo.cultura == "MILHO"
        assert resumo.ano_safra == "2025/26"
        assert resumo.area_plantada_ha == 100.0

        # Operações
        assert resumo.financeiro.total_operacoes == 1
        assert resumo.financeiro.custo_operacoes_total == 5000.0
        assert resumo.financeiro.custo_por_ha == 50.0  # 5000 / 100

        # Romaneios
        assert resumo.financeiro.total_romaneios == 1
        assert resumo.financeiro.total_sacas == 1000.0
        assert resumo.financeiro.produtividade_sc_ha == 10.0  # 1000 / 100

        # Financeiro
        assert resumo.financeiro.despesa_total == 5000.0
        assert resumo.financeiro.receita_total == 100000.0
        assert resumo.financeiro.lucro_bruto == 95000.0
        assert resumo.financeiro.roi_pct == 1900.0  # (95000 / 5000) × 100

    @pytest.mark.asyncio
    async def test_resumo_financeiro_safra_sem_operacoes(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Dashboard com safra sem operações deve retornar zeros."""
        # Setup
        safra = add_safra_com_area(
            session,
            tenant_id=tenant_id,
            talhao_id=talhao_id,
            ano_safra="2025/26",
            cultura="SOJA",
            status="PLANTIO",
            area_ha=50.0,
        )
        await session.commit()

        # Act
        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)

        # Assert: Todos os valores zero/vazios
        assert resumo.financeiro.total_operacoes == 0
        assert resumo.financeiro.custo_operacoes_total == 0.0
        assert resumo.financeiro.total_romaneios == 0
        assert resumo.financeiro.total_sacas == 0.0
        assert resumo.financeiro.despesa_total == 0.0
        assert resumo.financeiro.receita_total == 0.0
        assert resumo.financeiro.lucro_bruto == 0.0
        assert resumo.financeiro.roi_pct is None  # Sem despesa = sem ROI

    @pytest.mark.asyncio
    async def test_resumo_financeiro_safra_nao_existe(
        self,
        session: AsyncSession,
        tenant_id: str
    ):
        """Dashboard deve falhar se safra não existe."""
        safra_id_fake = uuid4()

        dashboard = DashboardAgricolaService(session, tenant_id)

        with pytest.raises(EntityNotFoundError):
            await dashboard.resumo_financeiro_safra(safra_id_fake)

    @pytest.mark.asyncio
    async def test_tenant_isolation_dashboard(
        self,
        session: AsyncSession,
        tenant_id: str,
        outro_tenant_id: str,
        talhao_id: str
    ):
        """Dashboard de um tenant não deveria acessar safra de outro tenant."""
        # Setup: Safra de outro tenant
        safra_outro = add_safra_com_area(
            session,
            tenant_id=outro_tenant_id,
            talhao_id=talhao_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="COLHEITA",
            area_ha=50.0,
        )
        await session.commit()

        # Act: Tentar acessar com tenant_id diferente
        dashboard = DashboardAgricolaService(session, tenant_id)

        with pytest.raises(EntityNotFoundError):
            await dashboard.resumo_financeiro_safra(safra_outro.id)

    @pytest.mark.asyncio
    async def test_resumo_produtividade_calculada(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """Produtividade deve ser calculada corretamente (sacas/ha)."""
        # Setup: Safra com area 100 ha
        safra = add_safra_com_area(
            session,
            tenant_id=tenant_id,
            talhao_id=talhao_id,
            ano_safra="2025/26",
            cultura="SOJA",
            status="COLHEITA",
            area_ha=100.0,
        )

        plano = PlanoConta(
            id=uuid4(),
            tenant_id=tenant_id,
            codigo="4.01",
            nome="Receita",
            tipo="RECEITA",
            categoria_rfb="RECEITA_ATIVIDADE",
            natureza="ANALITICA",
            ativo=True
        )
        session.add(plano)
        await session.commit()

        # Criar romaneio: 2500 sacas em 100 ha = 25 sc/ha
        romaneio = RomaneioColheita(
            id=uuid4(),
            tenant_id=tenant_id,
            safra_id=safra.id,
            talhao_id=talhao_id,
            data_colheita=date.today(),
            peso_bruto_kg=150000.0,  # 150 toneladas
            tara_kg=0.0,
            umidade_pct=12.0,
            impureza_pct=1.0,
            preco_saca=100.0,
            peso_liquido_kg=150000.0,
            desconto_umidade_kg=0.0,
            desconto_impureza_kg=0.0,
            peso_liquido_padrao_kg=150000.0,
            sacas_60kg=2500.0,  # 2500 sacas
            receita_total=250000.0
        )
        session.add(romaneio)
        await session.commit()

        # Act
        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)

        # Assert
        assert resumo.financeiro.total_sacas == 2500.0
        assert resumo.financeiro.produtividade_sc_ha == 25.0  # 2500 / 100

    @pytest.mark.asyncio
    async def test_resumo_roi_calculado(
        self,
        session: AsyncSession,
        tenant_id: str,
        unidade_produtiva_id: str,
        talhao_id: str
    ):
        """ROI deve ser (receita - despesa) / despesa × 100."""
        # Setup
        safra = add_safra_com_area(
            session,
            tenant_id=tenant_id,
            talhao_id=talhao_id,
            ano_safra="2025/26",
            cultura="MILHO",
            status="COLHEITA",
            area_ha=100.0,
        )

        plano_despesa = PlanoConta(
            id=uuid4(),
            tenant_id=tenant_id,
            codigo="3.02",
            nome="Custeio",
            tipo="DESPESA",
            categoria_rfb="CUSTEIO",
            natureza="ANALITICA",
            ativo=True
        )
        plano_receita = PlanoConta(
            id=uuid4(),
            tenant_id=tenant_id,
            codigo="4.02",
            nome="Receita",
            tipo="RECEITA",
            categoria_rfb="RECEITA_ATIVIDADE",
            natureza="ANALITICA",
            ativo=True
        )
        session.add_all([plano_despesa, plano_receita])
        await session.commit()

        # Operação: custo = R$ 10.000
        operacao = OperacaoAgricola(
            id=uuid4(),
            tenant_id=tenant_id,
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita",
            data_realizada=date.today(),
            area_aplicada_ha=100.0,
            custo_total=10000.0,
            fase_safra="COLHEITA"
        )
        session.add(operacao)

        # Despesa
        despesa = Despesa(
            id=uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_despesa.id,
            descricao="Colheita",
            valor_total=10000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            data_pagamento=date.today(),
            status="PAGO",
            origem_id=operacao.id,
            origem_tipo="OPERACAO_AGRICOLA"
        )
        session.add(despesa)

        # Romaneio: receita = R$ 30.000
        romaneio = RomaneioColheita(
            id=uuid4(),
            tenant_id=tenant_id,
            safra_id=safra.id,
            talhao_id=talhao_id,
            data_colheita=date.today(),
            peso_bruto_kg=60000.0,
            tara_kg=0.0,
            umidade_pct=14.0,
            impureza_pct=1.0,
            preco_saca=300.0,  # Preço alto
            peso_liquido_kg=60000.0,
            desconto_umidade_kg=0.0,
            desconto_impureza_kg=0.0,
            peso_liquido_padrao_kg=60000.0,
            sacas_60kg=1000.0,
            receita_total=300000.0  # 1000 × 300
        )
        session.add(romaneio)

        # Receita
        receita = Receita(
            id=uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            plano_conta_id=plano_receita.id,
            descricao="Venda",
            valor_total=300000.0,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            data_recebimento=date.today(),
            status="RECEBIDO",
            origem_id=romaneio.id,
            origem_tipo="ROMANEIO_COLHEITA"
        )
        session.add(receita)
        await session.commit()

        # Act
        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)

        # Assert
        # ROI = (300000 - 10000) / 10000 × 100 = 2900%
        assert resumo.financeiro.despesa_total == 10000.0
        assert resumo.financeiro.receita_total == 300000.0
        assert resumo.financeiro.lucro_bruto == 290000.0
        assert resumo.financeiro.roi_pct == 2900.0


async def _criar_operacao(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    talhao_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    custo_total: float,
    descricao: str,
) -> OperacaoAgricola:
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        production_unit_id=production_unit_id,
        talhao_id=talhao_id,
        tipo="PLANTIO",
        descricao=descricao,
        data_realizada=date.today(),
        custo_total=custo_total,
    )
    session.add(operacao)
    await session.commit()
    await session.refresh(operacao)
    return operacao


async def _criar_execucao_com_allocation(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    operacao: OperacaoAgricola,
    production_unit_id: uuid.UUID,
    unidade_ha_id: uuid.UUID,
    amount: float,
) -> None:
    execucao = OperacaoExecucao(
        tenant_id=tenant_id,
        operacao_id=operacao.id,
        production_unit_id=production_unit_id,
        data_execucao=date.today(),
        quantidade_executada=1.0,
        quantidade_devolvida=0.0,
        unidade_medida_id=unidade_ha_id,
        custo_real=amount,
        area_ha_executada=1.0,
        status="REALIZADA",
    )
    session.add(execucao)
    await session.flush()
    await registrar_cost_allocation(
        session,
        tenant_id=tenant_id,
        production_unit_id=production_unit_id,
        source="OPERATION_EXECUTION",
        source_id=execucao.id,
        operation_execution_id=execucao.id,
        amount=amount,
        allocation_date=date.today(),
        cost_category="OUTROS",
        allocation_method="DIRECT",
        allocation_basis=1.0,
    )
    await session.commit()


class TestDashboardFinanceiroSafraCustoRealizado:
    """SOIL-PLAN-EXEC-04F: custo do dashboard vem de CostAllocation, não de Despesa."""

    async def _contexto(self, session: AsyncSession):
        tenant_id = uuid4()
        await _garantir_tenant(session, tenant_id)
        unidade_id = await _criar_unidade_produtiva(session, tenant_id)
        area_id = await _criar_area(session, tenant_id, unidade_id)
        safra = await _criar_safra(session, tenant_id)
        cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
        pu = ProductionUnit(
            tenant_id=tenant_id,
            safra_id=safra.id,
            cultivo_id=cultivo_id,
            area_id=area_id,
            percentual_participacao=100,
            area_ha=100.0,
            status="ATIVA",
        )
        session.add(pu)
        cultivo_area = CultivoArea(
            tenant_id=tenant_id,
            cultivo_id=cultivo_id,
            area_id=area_id,
            area_ha=100.0,
        )
        session.add(cultivo_area)
        await session.commit()
        await session.refresh(pu)
        unidade_ha_id = await _garantir_unidade_ha(session, tenant_id)
        return tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id

    def _plano_despesa(self, tenant_id: uuid.UUID, codigo: str) -> PlanoConta:
        return PlanoConta(
            tenant_id=tenant_id,
            codigo=codigo,
            nome="Custeio",
            tipo="DESPESA",
            categoria_rfb="CUSTEIO",
            natureza="ANALITICA",
            ativo=True,
        )

    def _despesa_operacao(
        self,
        *,
        tenant_id: uuid.UUID,
        unidade_id: uuid.UUID,
        plano_conta_id: uuid.UUID,
        descricao: str,
        valor_total: float,
        origem_id: uuid.UUID,
    ) -> Despesa:
        return Despesa(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_id,
            plano_conta_id=plano_conta_id,
            descricao=descricao,
            valor_total=valor_total,
            data_emissao=date.today(),
            data_vencimento=date.today(),
            status="PAGO",
            origem_id=origem_id,
            origem_tipo="OPERACAO_AGRICOLA",
        )

    @pytest.mark.asyncio
    async def test_cenario_a_operacao_com_allocation_ignora_despesa_divergente(
        self, session: AsyncSession
    ):
        """CostAllocation e custo_total concordam; a Despesa não deve somar por cima."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        plano_despesa = self._plano_despesa(tenant_id, "3.90")
        session.add(plano_despesa)
        await session.commit()

        operacao = await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=1000.0, descricao="Op A",
        )
        await _criar_execucao_com_allocation(
            session, tenant_id=tenant_id, operacao=operacao, production_unit_id=pu.id,
            unidade_ha_id=unidade_ha_id, amount=1000.0,
        )
        session.add(self._despesa_operacao(
            tenant_id=tenant_id, unidade_id=unidade_id, plano_conta_id=plano_despesa.id,
            descricao="Despesa vinculada", valor_total=1000.0, origem_id=operacao.id,
        ))
        await session.commit()

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.custo_operacoes_total == 1000.0
        assert resumo.financeiro.despesa_total == 1000.0

    @pytest.mark.asyncio
    async def test_cenario_b_allocation_diverge_da_despesa_prevalece_allocation(
        self, session: AsyncSession
    ):
        """CostAllocation = 1200, Despesa = 900: custo considerado deve ser 1200, sem usar min()."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        plano_despesa = self._plano_despesa(tenant_id, "3.91")
        session.add(plano_despesa)
        await session.commit()

        operacao = await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=1200.0, descricao="Op B",
        )
        await _criar_execucao_com_allocation(
            session, tenant_id=tenant_id, operacao=operacao, production_unit_id=pu.id,
            unidade_ha_id=unidade_ha_id, amount=1200.0,
        )
        session.add(self._despesa_operacao(
            tenant_id=tenant_id, unidade_id=unidade_id, plano_conta_id=plano_despesa.id,
            descricao="Despesa divergente", valor_total=900.0, origem_id=operacao.id,
        ))
        await session.commit()

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.custo_operacoes_total == 1200.0
        assert resumo.financeiro.despesa_total == 1200.0

    @pytest.mark.asyncio
    async def test_cenario_c_operacao_antiga_sem_allocation_usa_fallback_custo_total(
        self, session: AsyncSession
    ):
        """Operação sem CostAllocation cai no fallback de OperacaoAgricola.custo_total."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=800.0, descricao="Op C antiga",
        )

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.custo_operacoes_total == 800.0
        assert resumo.financeiro.despesa_total == 800.0

    @pytest.mark.asyncio
    async def test_cenario_d_operacao_sem_custo(self, session: AsyncSession):
        """Sem custo_total e sem allocation: custo considerado = 0 e ROI preservado como None."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=0.0,
            descricao="Op D sem custo",
        )

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.custo_operacoes_total == 0.0
        assert resumo.financeiro.despesa_total == 0.0
        assert resumo.financeiro.roi_pct is None

    @pytest.mark.asyncio
    async def test_cenario_e_multiplas_operacoes_sem_duplicidade(self, session: AsyncSession):
        """Operação 1 com allocation + Operação 2 sem allocation: soma sem duplicidade."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        operacao_1 = await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=500.0, descricao="Op E1",
        )
        await _criar_execucao_com_allocation(
            session, tenant_id=tenant_id, operacao=operacao_1, production_unit_id=pu.id,
            unidade_ha_id=unidade_ha_id, amount=500.0,
        )
        await _criar_operacao(
            session, tenant_id=tenant_id, safra_id=safra.id, cultivo_id=cultivo_id,
            talhao_id=area_id, production_unit_id=pu.id, custo_total=300.0,
            descricao="Op E2 sem allocation",
        )

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.total_operacoes == 2
        assert resumo.financeiro.custo_operacoes_total == 800.0
        assert resumo.financeiro.despesa_total == 800.0

    @pytest.mark.asyncio
    async def test_cenario_f_despesa_orfa_nao_entra(self, session: AsyncSession):
        """Despesa órfã, sem operação/custo/allocation correspondente, não entra no cálculo."""
        ctx = await self._contexto(session)
        tenant_id, unidade_id, area_id, safra, cultivo_id, pu, unidade_ha_id = ctx
        plano_despesa = self._plano_despesa(tenant_id, "3.92")
        session.add(plano_despesa)
        await session.commit()
        session.add(self._despesa_operacao(
            tenant_id=tenant_id, unidade_id=unidade_id, plano_conta_id=plano_despesa.id,
            descricao="Despesa órfã", valor_total=5000.0, origem_id=uuid4(),
        ))
        await session.commit()

        dashboard = DashboardAgricolaService(session, tenant_id)
        resumo = await dashboard.resumo_financeiro_safra(safra.id)
        assert resumo.financeiro.total_operacoes == 0
        assert resumo.financeiro.custo_operacoes_total == 0.0
        assert resumo.financeiro.despesa_total == 0.0
