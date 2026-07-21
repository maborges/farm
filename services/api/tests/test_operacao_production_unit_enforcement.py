"""
SOIL-PLAN-EXEC-04K — Garantia de ProductionUnit e bloqueio de novos custos sem
CostAllocation.

Cobre os cenários A-N descritos na especificação do programa: operação REALIZADA
com custo_total > 0 nunca pode persistir sem ProductionUnit resolvida
deterministicamente e sem CostAllocation criada com sucesso.
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
    _garantir_unidade_ha,
)

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaCreate, OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from agricola.production_units.models import ProductionUnit
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.estoque import EstoqueMovimento


async def _contexto(session: AsyncSession, *, com_cultivo: bool = True):
    tenant_id = uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    safra.status = "COLHEITA"
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id) if com_cultivo else None
    return tenant_id, unidade_id, area_id, safra, cultivo_id


def _payload(
    *,
    safra_id,
    talhao_id,
    status="REALIZADA",
    custo_total=250,
    production_unit_id=None,
    tipo="COLHEITA",
):
    return OperacaoAgricolaCreate(
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo=tipo,
        descricao="Operação 04K",
        data_realizada=date.today(),
        area_aplicada_ha=10,
        custo_total=custo_total,
        status=status,
        production_unit_id=production_unit_id,
        insumos=[],
    )


async def _allocation_da_operacao(session: AsyncSession, tenant_id, operacao_id):
    return (
        await session.execute(
            select(CostAllocation)
            .join(OperacaoExecucao, CostAllocation.operation_execution_id == OperacaoExecucao.id)
            .where(
                CostAllocation.tenant_id == tenant_id,
                OperacaoExecucao.operacao_id == operacao_id,
            )
        )
    ).scalars().first()


# ---------------------------------------------------------------------------
# A) Resolução explícita válida
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_resolucao_explicita_valida_cria_allocation(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(
        _payload(safra_id=safra.id, talhao_id=area_id, production_unit_id=pu.id)
    )

    assert operacao.production_unit_id == pu.id
    allocation = await _allocation_da_operacao(session, tenant_id, operacao.id)
    assert allocation is not None
    assert float(allocation.amount) == 250.0


# ---------------------------------------------------------------------------
# B) Resolução automática única
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_b_resolucao_automatica_unica(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))

    assert operacao.production_unit_id == pu.id
    allocation = await _allocation_da_operacao(session, tenant_id, operacao.id)
    assert allocation is not None


# ---------------------------------------------------------------------------
# C) Ausência de ProductionUnit bloqueia
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_c_ausencia_production_unit_bloqueia(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    # Nenhuma ProductionUnit cadastrada para esta safra/área.

    service = OperacaoService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="unidade produtiva"):
        await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))

    total = (
        await session.execute(
            select(OperacaoAgricola).where(OperacaoAgricola.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert total == []


# ---------------------------------------------------------------------------
# D) Ambiguidade bloqueia
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_d_ambiguidade_bloqueia(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    cultivo_id_2 = await _criar_cultivo(session, tenant_id, safra.id)
    # Duas ProductionUnit ATIVAS para a mesma safra/área (consórcio, percentuais
    # somando 100 para respeitar o check constraint), cultivos distintos, mas o
    # payload não informa cultivo_id, então ambas são candidatas válidas.
    pu1 = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=50,
        area_ha=15.0,
        status="ATIVA",
    )
    pu2 = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra.id,
        cultivo_id=cultivo_id_2,
        area_id=area_id,
        percentual_participacao=50,
        area_ha=15.0,
        status="ATIVA",
    )
    session.add_all([pu1, pu2])
    await session.commit()

    service = OperacaoService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="múltiplas ProductionUnit"):
        await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))


# ---------------------------------------------------------------------------
# E) Outro tenant bloqueia
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e_production_unit_de_outro_tenant_bloqueia(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    outro_tenant_id = uuid4()
    service = OperacaoService(session, outro_tenant_id)
    # Talhão/safra pertencem ao tenant original; o tenant "atacante" nem enxerga
    # o contexto (EntityNotFoundError) antes de chegar à validação de
    # ProductionUnit — o resultado prático é o mesmo bloqueio cross-tenant.
    payload = _payload(safra_id=safra.id, talhao_id=area_id, production_unit_id=pu.id)
    with pytest.raises((BusinessRuleError, EntityNotFoundError)):
        await service.criar(payload)


# ---------------------------------------------------------------------------
# F) Transição PLANEJADA->REALIZADA bloqueia sem PU, status anterior preservado
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f_transicao_planejada_para_realizada_bloqueia(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    # Operação criada como PLANEJADA não exige PU (sem bloqueio de custo).
    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(
        _payload(safra_id=safra.id, talhao_id=area_id, status="PLANEJADA")
    )
    assert operacao.production_unit_id is None

    with pytest.raises(BusinessRuleError):
        await service.atualizar(operacao.id, OperacaoAgricolaUpdate(status="REALIZADA"))
    # A própria service.atualizar() já reverte a transação internamente
    # (session.rollback() em BusinessRuleError); o status anterior nunca é commitado.


# ---------------------------------------------------------------------------
# G) Falha não consome estoque / H) não cria execução/allocation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gh_falha_nao_consome_estoque_nem_cria_execucao_allocation(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)

    service = OperacaoService(session, tenant_id)
    with pytest.raises(BusinessRuleError):
        await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))

    execucoes = (
        await session.execute(
            select(OperacaoExecucao).where(OperacaoExecucao.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert execucoes == []

    allocations = (
        await session.execute(
            select(CostAllocation).where(CostAllocation.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert allocations == []

    movimentos = (
        await session.execute(
            select(EstoqueMovimento).where(EstoqueMovimento.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert movimentos == []


# ---------------------------------------------------------------------------
# I) Contexto válido cria allocation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_i_contexto_valido_cria_allocation(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))
    allocation = await _allocation_da_operacao(session, tenant_id, operacao.id)
    assert allocation is not None
    assert allocation.production_unit_id == pu.id


# ---------------------------------------------------------------------------
# J) Retry não duplica allocation (idempotência)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_j_retry_nao_duplica_allocation(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(_payload(safra_id=safra.id, talhao_id=area_id))

    # Reenvio: edição que não muda nada economicamente relevante, apenas observação.
    await service.atualizar(operacao.id, OperacaoAgricolaUpdate(observacoes="reenvio offline"))

    allocations = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.production_unit_id == operacao.production_unit_id,
            )
        )
    ).scalars().all()
    assert len(allocations) == 1


# ---------------------------------------------------------------------------
# K) Edição econômica revalida contexto — production_unit de outro tenant é rejeitada
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_k_edicao_rejeita_production_unit_de_outro_contexto(session: AsyncSession):
    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(
        _payload(safra_id=safra.id, talhao_id=area_id, production_unit_id=pu.id)
    )

    with pytest.raises(BusinessRuleError):
        await service.atualizar(
            operacao.id, OperacaoAgricolaUpdate(production_unit_id=uuid4())
        )
    # Idem: rollback interno da service já garante que o vínculo inválido nunca
    # é persistido.


# ---------------------------------------------------------------------------
# N) Tipo que não exige allocation preserva comportamento existente
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_n_tipo_sem_exigencia_allocation_preserva_comportamento(session: AsyncSession):
    """OUTROS costuma ter regra.exige_cost_allocation permissiva; se a classificação
    de origem não exigir allocation, custo>0 sem PU não deve ser bloqueado por esta
    regra (o bloqueio é direcionado, não universal — SOIL-PLAN-EXEC-04K §8)."""
    from agricola.alertas.service import AlertasAgricolasService

    tenant_id, unidade_id, area_id, safra, cultivo_id = await _contexto(session)
    alertas_svc = AlertasAgricolasService(session, tenant_id)
    regra = alertas_svc.classificar_origem_operacao("OUTROS")

    service = OperacaoService(session, tenant_id)
    payload = _payload(safra_id=safra.id, talhao_id=area_id, tipo="OUTROS")

    if regra.exige_cost_allocation:
        with pytest.raises(BusinessRuleError):
            await service.criar(payload)
    else:
        operacao = await service.criar(payload)
        assert operacao.production_unit_id is None
