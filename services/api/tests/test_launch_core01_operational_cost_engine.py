from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.custos.operational_cost_service import OperationalCostAllocationService, OperationalCostInput
from agricola.dre.service import DREAgricolaV1Service
from core.cadastros.produtos.models import Produto
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from operacional.models.estoque import Deposito
from operacional.models.compras import Fornecedor
from core.cadastros.pessoas.models import Pessoa
from operacional.schemas.abastecimento import AbastecimentoCreate
from operacional.schemas.estoque import EntradaEstoqueRequest
from operacional.schemas.frota import ItemOrdemServicoCreate, OrdemServicoCreate, OrdemServicoUpdate
from operacional.services.abastecimento_service import AbastecimentoService
from operacional.services.estoque_service import EstoqueService
from operacional.services.frota_service import FrotaService
from rh.models import ColaboradorRH, Empreitada, LancamentoDiaria
from rh.service import DiariaService, EmpreitadaService
from test_frota_apontamentos_step08 import (
    _criar_area,
    _criar_cultivo,
    _criar_equipamento,
    _criar_jornada_raw,
    _criar_operador,
    _criar_production_unit,
    _criar_safra,
    _criar_up,
    _garantir_tenant,
)


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> PlanoConta:
    plano = PlanoConta(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo=f"9.{uuid.uuid4().hex[:6]}",
        nome=nome,
        tipo="DESPESA",
        natureza="ANALITICA",
        categoria_rfb="CUSTEIO",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    await session.refresh(plano)
    return plano


async def _criar_produto(session: AsyncSession, tenant_id: uuid.UUID, preco_medio: float = 15.0) -> Produto:
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=f"Produto Core01 {uuid.uuid4().hex[:6]}",
        tipo="INSUMO",
        unidade_medida="L",
        preco_medio=preco_medio,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_deposito(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> Deposito:
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Depósito Core01",
        tipo="GERAL",
        ativo=True,
    )
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito


async def _criar_fornecedor(session: AsyncSession, tenant_id: uuid.UUID) -> Fornecedor:
    pessoa = Pessoa(id=uuid.uuid4(), tenant_id=tenant_id, tipo="PJ", nome_exibicao="Fornecedor Core01", base_legal="CONTRATO", ativo=True)
    session.add(pessoa)
    await session.flush()
    fornecedor = Fornecedor(id=uuid.uuid4(), tenant_id=tenant_id, pessoa_id=pessoa.id)
    session.add(fornecedor)
    await session.commit()
    await session.refresh(fornecedor)
    return fornecedor


async def _criar_colaborador(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    tipo_contrato: str = "DIARISTA",
) -> ColaboradorRH:
    colaborador = ColaboradorRH(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Colaborador {uuid.uuid4().hex[:6]}",
        tipo_contrato=tipo_contrato,
        valor_diaria=180.0,
        valor_hora=22.5,
        ativo=True,
    )
    session.add(colaborador)
    await session.commit()
    await session.refresh(colaborador)
    return colaborador


@pytest.mark.asyncio
async def test_operational_cost_service_reprocessa_sem_duplicar(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Core01-A")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Core01-A")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperationalCostAllocationService(session, tenant_id)
    origem_id = uuid.uuid4()
    payload = OperationalCostInput(
        tenant_id=tenant_id,
        unidade_produtiva_id=up_id,
        safra_id=safra.id,
        talhao_id=area_id,
        production_unit_id=pu.id,
        origem_tipo="ABASTECIMENTO",
        origem_id=origem_id,
        categoria="COMBUSTIVEL",
        valor=120.0,
        data_competencia=date.today(),
        descricao="Abastecimento idempotente",
    )

    await service.process(payload)
    await service.process(payload)
    await session.commit()

    total = (
        await session.execute(
            select(func.count(CostAllocation.id)).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "FROTA_COMBUSTIVEL",
                CostAllocation.source_id == origem_id,
            )
        )
    ).scalar_one()
    assert total == 1


@pytest.mark.asyncio
async def test_abastecimento_externo_gera_allocacao_canonica_e_despesa(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Core01-B")
    await _criar_plano_conta(session, tenant_id, "Combustível Operacional")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Core01-B")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador = await _criar_operador(session, tenant_id, up_id, "Operador Core01")
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator Core01")
    await _criar_jornada_raw(session, tenant_id, equipamento.id, up_id, operador.id, safra.id, area_id)

    abastecimento = await AbastecimentoService(session, tenant_id).registrar(
        AbastecimentoCreate(
            equipamento_id=equipamento.id,
            data=datetime.now(timezone.utc),
            operador_id=operador.id,
            horimetro_na_data=110.0,
            tipo_combustivel="DIESEL",
            litros=40.0,
            preco_litro=6.5,
            local="EXTERNO",
        )
    )

    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "FROTA_COMBUSTIVEL",
                CostAllocation.source_id == abastecimento.id,
            )
        )
    ).scalar_one()
    despesa = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "ABASTECIMENTO",
                Despesa.origem_id == abastecimento.id,
            )
        )
    ).scalar_one()

    assert allocation.production_unit_id == pu.id
    assert allocation.cost_category == "INSUMO"
    assert float(allocation.amount) == 260.0
    assert float(despesa.valor_total) == 260.0


@pytest.mark.asyncio
async def test_fechamento_os_gera_pecas_manutencao_e_despesa_unica(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Core01-C")
    await _criar_plano_conta(session, tenant_id, "Manutenção Custeio")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Core01-C")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador = await _criar_operador(session, tenant_id, up_id, "Operador Oficina")
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator Oficina")
    await _criar_jornada_raw(session, tenant_id, equipamento.id, up_id, operador.id, safra.id, area_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=30.0)
    deposito = await _criar_deposito(session, tenant_id, up_id)
    fornecedor = await _criar_fornecedor(session, tenant_id)
    await EstoqueService(session, tenant_id).registrar_entrada(
        EntradaEstoqueRequest(
            deposito_id=deposito.id,
            produto_id=produto.id,
            fornecedor_id=fornecedor.id,
            quantidade=10.0,
            custo_unitario=30.0,
            motivo="Carga inicial OS",
        )
    )
    await session.commit()

    service = FrotaService(session, tenant_id)
    os = await service.abrir_os(
        OrdemServicoCreate(
            maquinario_id=equipamento.id,
            tipo="CORRETIVA",
            descricao_problema="Troca de correia",
            horimetro_na_abertura=110.0,
            tecnico_responsavel="Oficina Core01",
        )
    )
    await service.adicionar_item_os(
        os.id,
        ItemOrdemServicoCreate(
            produto_id=produto.id,
            quantidade=2.0,
            deposito_id=deposito.id,
            baixar_estoque=True,
        ),
    )
    await service.fechar_os(os.id, OrdemServicoUpdate(custo_mao_obra=90.0))

    pecas = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "FROTA_PECAS",
                CostAllocation.source_id == os.id,
            )
        )
    ).scalar_one()
    manutencao = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "FROTA_MANUTENCAO",
                CostAllocation.source_id == os.id,
            )
        )
    ).scalar_one()
    despesas = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "ORDEM_SERVICO",
                Despesa.origem_id == os.id,
            )
        )
    ).scalars().all()

    assert pecas.production_unit_id == pu.id
    assert float(pecas.amount) == 60.0
    assert float(manutencao.amount) == 90.0
    assert len(despesas) == 1
    assert float(despesas[0].valor_total) == 150.0


@pytest.mark.asyncio
async def test_rh_sem_contexto_agricola_nao_forca_rateio_invalido(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Core01-D")
    await _criar_plano_conta(session, tenant_id, "RH Custeio")
    colaborador = await _criar_colaborador(session, tenant_id, up_id)
    diaria = LancamentoDiaria(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        colaborador_id=colaborador.id,
        unidade_produtiva_id=up_id,
        data=date.today(),
        horas_trabalhadas=8.0,
        atividade="GERAL",
        valor_diaria=180.0,
        status="PENDENTE",
    )
    session.add(diaria)
    await session.commit()

    pagos = await DiariaService(session, tenant_id).pagar_lote([diaria.id], date.today())
    assert pagos == 1

    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "RH_DIARIA",
                CostAllocation.source_id == diaria.id,
            )
        )
    ).scalars().first()
    despesa = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "RH_DIARIA",
                Despesa.origem_id == diaria.id,
            )
        )
    ).scalar_one()

    assert allocation is None
    assert float(despesa.valor_total) == 180.0


@pytest.mark.asyncio
async def test_dre_reflete_maquinas_e_mao_de_obra_sem_duplicidade(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Core01-E")
    await _criar_plano_conta(session, tenant_id, "Combustível Operacional")
    await _criar_plano_conta(session, tenant_id, "RH Custeio")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Core01-E")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador = await _criar_operador(session, tenant_id, up_id, "Operador DRE")
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator DRE")
    await _criar_jornada_raw(session, tenant_id, equipamento.id, up_id, operador.id, safra.id, area_id)
    await AbastecimentoService(session, tenant_id).registrar(
        AbastecimentoCreate(
            equipamento_id=equipamento.id,
            data=datetime.now(timezone.utc),
            operador_id=operador.id,
            horimetro_na_data=115.0,
            tipo_combustivel="DIESEL",
            litros=20.0,
            preco_litro=6.0,
            local="EXTERNO",
        )
    )

    colaborador = await _criar_colaborador(session, tenant_id, up_id, tipo_contrato="EMPREITEIRO")
    empreitada = Empreitada(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        colaborador_id=colaborador.id,
        unidade_produtiva_id=up_id,
        safra_id=safra.id,
        descricao="Capina operacional",
        unidade="HECTARE",
        quantidade=10.0,
        valor_unitario=25.0,
        valor_total=250.0,
        data_inicio=date.today(),
        status="CONCLUIDA",
    )
    session.add(empreitada)
    await session.commit()
    await EmpreitadaService(session, tenant_id).pagar(empreitada.id, date.today())

    dre = await DREAgricolaV1Service(session, tenant_id).gerar(safra_id=safra.id)

    assert dre.custos_operacionais == 370.0
    assert dre.despesas_operacionais == 0.0
    assert any(item.origem_tipo == "FROTA_COMBUSTIVEL" for item in dre.custos_operacionais_detalhe.itens)
    assert any(item.origem_tipo == "RH_EMPREITADA" for item in dre.custos_operacionais_detalhe.itens)
    assert not dre.despesas_operacionais_detalhe.itens
    assert pu.id in dre.production_unit_ids
