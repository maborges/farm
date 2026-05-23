from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.alertas.service import AlertasAgricolasService
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.operacoes.schemas import OperacaoAgricolaUpdate
from agricola.operacoes.service import OperacaoService
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.service import TarefaService
from agricola.custos.models import CostAllocation
from core.models.tenant_audit_log import TenantAuditLog
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.despesa_schema import DespesaCreate, RateioCreate
from financeiro.services.despesa_service import DespesaService
from notificacoes.models import Notificacao


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_unidade_produtiva(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'UP Step03', true, now(), now())"
        ),
        {"id": str(unidade_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()
    return unidade_id


async def _criar_area(session: AsyncSession, tenant_id: uuid.UUID, unidade_id: uuid.UUID) -> uuid.UUID:
    area_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', 'Talhão Step03', 30.0, true, now(), now())"
        ),
        {"id": str(area_id), "tenant_id": str(tenant_id), "unidade_id": str(unidade_id)},
    )
    await session.commit()
    return area_id


async def _criar_safra(session: AsyncSession, tenant_id: uuid.UUID) -> Safra:
    safra = Safra(
        tenant_id=tenant_id,
        ano_safra=f"{date.today().year}/{date.today().year + 1}",
        cultura="SOJA",
        status="PLANEJADA",
    )
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    return safra


async def _criar_cultivo(session: AsyncSession, tenant_id: uuid.UUID, safra_id: uuid.UUID) -> uuid.UUID:
    cultivo_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cultivos (id, tenant_id, safra_id, cultura, status, consorciado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :safra_id, 'SOJA', 'PLANEJADO', false, now(), now())"
        ),
        {"id": str(cultivo_id), "tenant_id": str(tenant_id), "safra_id": str(safra_id)},
    )
    await session.commit()
    return cultivo_id


async def _criar_production_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    area_id: uuid.UUID,
) -> ProductionUnit:
    pu = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=100,
        area_ha=30.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _garantir_unidade_ha(session: AsyncSession) -> uuid.UUID:
    existente = (
        await session.execute(
            text("SELECT id FROM unidades_medida WHERE ativo = true AND codigo = 'HA' AND tenant_id IS NULL LIMIT 1")
        )
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_medida "
            "(id, tenant_id, codigo, nome, dimensao, codigo_canonico, fator_canonico, sistema, ativo, casas_decimais, eh_canonica, created_at, updated_at) "
            "VALUES (:id, NULL, 'HA', 'Hectare', 'AREA', 'HA', 1, true, true, 4, true, now(), now())"
        ),
        {"id": str(unidade_id)},
    )
    await session.commit()
    return unidade_id


async def _criar_tarefa(session: AsyncSession, tenant_id: uuid.UUID, safra_id: uuid.UUID, *, tipo: str, obs: str | None = None) -> SafraTarefa:
    tarefa = SafraTarefa(
        tenant_id=tenant_id,
        safra_id=safra_id,
        origem="MANUAL",
        tipo=tipo,
        descricao=f"Tarefa {tipo}",
        criticidade="NORMAL",
        prioridade="MEDIA",
        status="EM_EXECUCAO",
        obs=obs,
    )
    session.add(tarefa)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


async def _criar_operacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    area_id: uuid.UUID,
    *,
    production_unit_id: uuid.UUID | None,
) -> uuid.UUID:
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        production_unit_id=production_unit_id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Operação Step03",
        data_realizada=date.today(),
        area_aplicada_ha=10,
        custo_total=500,
        custo_por_ha=50,
        status="PLANEJADA",
        fotos=[],
    )
    session.add(operacao)
    await session.commit()
    await session.refresh(operacao)
    return operacao.id


async def _criar_plano_custeio(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    plano_id = uuid.uuid4()
    session.add(
        PlanoConta(
            id=plano_id,
            tenant_id=tenant_id,
            codigo=f"5.1.{plano_id.hex[:6]}",
            nome="Custeio Step03",
            tipo="DESPESA",
            natureza="ANALITICA",
            categoria_rfb="CUSTEIO",
            ativo=True,
        )
    )
    await session.commit()
    return plano_id


@pytest.mark.asyncio
async def test_tarefa_administrativa_fecha_sem_warning_step03(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="ADMINISTRATIVA")

    await TarefaService(session, tenant_id).concluir(tarefa.id)
    await session.commit()

    total = (
        await session.execute(
            select(func.count(Notificacao.id)).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalar_one()
    assert total == 0


@pytest.mark.asyncio
async def test_inspecao_sem_evidencia_gera_warning_leve(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="INSPECAO")

    await TarefaService(session, tenant_id).concluir(tarefa.id)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.origem_id == f"tarefa:{tarefa.id}:inspection_without_evidence",
            )
        )
    ).scalars().first()

    assert notif is not None
    assert notif.nivel == "INFO"


@pytest.mark.asyncio
async def test_manutencao_frota_sem_evidencia_gera_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    tarefa = await _criar_tarefa(session, tenant_id, safra.id, tipo="MANUTENCAO_FROTA")

    await TarefaService(session, tenant_id).concluir(tarefa.id)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.origem_id == f"tarefa:{tarefa.id}:maintenance_without_evidence",
            )
        )
    ).scalars().first()

    assert notif is not None
    assert notif.nivel == "WARNING"


@pytest.mark.asyncio
async def test_operacao_agricola_com_custo_tenta_garantir_execucao_e_allocation_step03(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await _garantir_unidade_ha(session)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operacao_id = await _criar_operacao(session, tenant_id, safra.id, cultivo_id, area_id, production_unit_id=pu.id)

    await OperacaoService(session, tenant_id).atualizar(operacao_id, OperacaoAgricolaUpdate(status="REALIZADA"))
    await session.commit()

    execucao = (
        await session.execute(select(OperacaoExecucao).where(OperacaoExecucao.operacao_id == operacao_id))
    ).scalars().first()
    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.operation_execution_id == execucao.id,
            )
        )
    ).scalars().first()

    assert execucao is not None
    assert allocation is not None


@pytest.mark.asyncio
async def test_despesa_automatica_sem_origem_gera_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    plano_id = await _criar_plano_custeio(session, tenant_id)

    despesa = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_id,
        descricao="Despesa automática sem origem",
        valor_total=100.0,
        data_emissao=date.today(),
        data_vencimento=date.today(),
        data_pagamento=date.today(),
        status="PAGO",
        origem_tipo="OPERACAO_AGRICOLA",
        origem_id=None,
    )
    session.add(despesa)
    await session.flush()

    await AlertasAgricolasService(session, tenant_id).validar_despesa_origem_leve(despesa)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.origem_id == f"despesa:{despesa.id}:missing_origin",
            )
        )
    ).scalars().first()
    audit = (
        await session.execute(
            select(TenantAuditLog).where(
                TenantAuditLog.tenant_id == tenant_id,
                TenantAuditLog.action == "auto_exp_origin",
            )
        )
    ).scalars().first()

    assert notif is not None
    assert audit is not None


@pytest.mark.asyncio
async def test_rateio_financeiro_legitimo_nao_gera_falso_positivo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)
    plano_id = await _criar_plano_custeio(session, tenant_id)

    service = DespesaService(session, tenant_id)
    payload = DespesaCreate(
        unidade_produtiva_id=unidade_id,
        plano_conta_id=plano_id,
        descricao="Despesa manual com rateio legítimo",
        valor_total=1000.0,
        data_emissao=date.today(),
        data_vencimento=date.today() + timedelta(days=10),
        rateios=[RateioCreate(safra_id=safra.id, valor_rateado=1000.0, percentual=100.0)],
    )
    await service.create_with_rateio(payload)
    await session.commit()

    total_workflow_notifs = (
        await session.execute(
            select(func.count(Notificacao.id)).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalar_one()

    assert total_workflow_notifs == 0
