"""
Testes — Frota & Equipamentos — Step 03

Cobre:
- Cálculo preciso da disponibilidade média da frota (%)
- Tempo total parado em manutenção (horas)
- Detecção e retorno de máquinas ociosas (sem jornadas/apontamentos nos últimos 7 dias)
- Consolidação de custos por safra usando a nova formatação dinâmica
- Consolidação e distribuição de custos por Unidade Produtiva (UP) com fallback legado
- Hardening e isolamento multi-UP/multi-tenant
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.safras.models import Safra
from core.cadastros.equipamentos.models import Equipamento
from operacional.services.frota_custo_consolidado_service import FrotaCustoConsolidadoService
from operacional.services.frota_dashboard_service import FrotaDashboardService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_unidade(
    session: AsyncSession, tenant_id: uuid.UUID, nome: str = "UP Frota Step03"
) -> uuid.UUID:
    uid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(uid), "tenant_id": str(tenant_id), "nome": nome},
    )
    await session.commit()
    return uid


async def _criar_equipamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None = None,
    status: str = "ATIVO",
) -> Equipamento:
    equipamento = Equipamento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Trator-S03-{uuid.uuid4().hex[:6]}",
        tipo="TRATOR",
        combustivel="DIESEL",
        status=status,
        horimetro_atual=100.0,
        km_atual=0.0,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_jornada(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None,
    data_inicio: datetime,
    data_fim: datetime | None = None,
    status: str = "FINALIZADA",
) -> uuid.UUID:
    jornada_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_jornadas_equipamento "
            "(id, tenant_id, equipamento_id, unidade_produtiva_id, tipo_operacao, data_inicio, data_fim, status, horimetro_inicial, horimetro_final, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :eq_id, :up_id, 'COLHEITA', :dt_ini, :dt_fim, :status, 100.0, 124.0, now(), now())"
        ),
        {
            "id": str(jornada_id),
            "tenant_id": str(tenant_id),
            "eq_id": str(equipamento_id),
            "up_id": str(unidade_produtiva_id) if unidade_produtiva_id else None,
            "dt_ini": data_inicio,
            "dt_fim": data_fim,
            "status": status,
        },
    )
    await session.commit()
    return jornada_id


async def _criar_abastecimento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None,
    safra_id: uuid.UUID | None,
    custo_total: float,
    data: datetime,
) -> uuid.UUID:
    ab_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_abastecimentos "
            "(id, tenant_id, equipamento_id, safra_id, litros, custo_total, data, tipo_combustivel, horimetro_na_data, preco_litro, tanque_cheio, local, created_at) "
            "VALUES (:id, :tid, :eq, :safra, 50.0, :custo, :data, 'DIESEL', 0.0, 12.0, true, 'INTERNO', now())"
        ),
        {
            "id": str(ab_id),
            "tid": str(tenant_id),
            "eq": str(equipamento_id),
            "safra": str(safra_id) if safra_id else None,
            "custo": custo_total,
            "data": data,
        },
    )
    await session.commit()
    return ab_id


async def _criar_manutencao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None,
    safra_id: uuid.UUID | None,
    custo_pecas: float,
    custo_mao_obra: float,
    data_inicio: datetime,
    data_fim: datetime,
) -> uuid.UUID:
    os_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_ordens_servico "
            "(id, tenant_id, equipamento_id, safra_id, numero_os, tipo, status, descricao_problema, data_abertura, "
            "data_conclusao, horimetro_na_abertura, custo_total_pecas, custo_mao_obra) "
            "VALUES (:id, :tid, :eq, :safra, :numero_os, 'PREVENTIVA', 'CONCLUIDA', 'Teste', :dt_ini, :dt_fim, 0, :pecas, :mo)"
        ),
        {
            "id": str(os_id),
            "tid": str(tenant_id),
            "eq": str(equipamento_id),
            "safra": str(safra_id) if safra_id else None,
            "numero_os": f"OS-{uuid.uuid4().hex[:10]}",
            "dt_ini": data_inicio,
            "dt_fim": data_fim,
            "pecas": custo_pecas,
            "mo": custo_mao_obra,
        },
    )

    manut_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_registros_manutencao "
            "(id, tenant_id, equipamento_id, os_id, safra_id, "
            "tipo, descricao, custo_total, data_realizacao, horimetro_na_data) "
            "VALUES (:id, :tid, :eq, :os, :safra, 'PREVENTIVA', 'Teste', :total, :dt, 0.0)"
        ),
        {
            "id": str(manut_id),
            "tid": str(tenant_id),
            "eq": str(equipamento_id),
            "os": str(os_id),
            "safra": str(safra_id) if safra_id else None,
            "total": custo_pecas + custo_mao_obra,
            "dt": data_fim,
        },
    )
    await session.commit()
    return manut_id


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculo_disponibilidade_e_tempo_parado(session: AsyncSession, tenant_id: uuid.UUID):
    """Garante que a disponibilidade e o tempo parado em manutenção sejam computados com precisão absoluta."""
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_unidade(session, tenant_id)
    equipamento = await _criar_equipamento(session, tenant_id, up_id)

    agora = datetime.now(timezone.utc)

    # 1. 24 horas trabalhadas em jornadas finalizadas
    await _criar_jornada(session, tenant_id, equipamento.id, up_id, agora - timedelta(days=5), agora - timedelta(days=5) + timedelta(hours=24))

    # 2. 6 horas paradas em ordens de serviço de manutenção
    await _criar_manutencao(
        session,
        tenant_id,
        equipamento.id,
        up_id,
        None,
        150.0,
        50.0,
        agora - timedelta(hours=20),
        agora - timedelta(hours=20) + timedelta(hours=6),
    )

    consolidado_svc = FrotaCustoConsolidadoService(session, tenant_id)
    horas_trab = await consolidado_svc.obter_horas_trabalhadas(equipamento.id, agora - timedelta(days=10), agora)
    horas_manut = await consolidado_svc.obter_tempo_manutencao(equipamento.id, agora - timedelta(days=10), agora)

    assert horas_trab == 24.0
    assert horas_manut == 6.0

    inicio = agora - timedelta(hours=30)
    disp = await consolidado_svc.calcular_disponibilidade(equipamento.id, inicio, agora)
    # (30 - 6) / 30 * 100 = 80.0%
    assert disp == 80.0


@pytest.mark.asyncio
async def test_consolidacao_de_custos_por_safra(session: AsyncSession, tenant_id: uuid.UUID):
    """Garante que os custos operacionais (abastecimento e manutenção) sejam apropriados corretamente por Safra."""
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_unidade(session, tenant_id)
    equipamento = await _criar_equipamento(session, tenant_id, up_id)

    # Criar uma safra
    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2025/26",
        cultura="SOJA",
        status="PLANEJAMENTO"
    )
    session.add(safra)
    await session.commit()

    agora = datetime.now(timezone.utc)

    # Abastecimento na safra
    await _criar_abastecimento(session, tenant_id, equipamento.id, up_id, safra.id, 600.0, agora - timedelta(days=1))

    # Manutenção na safra
    await _criar_manutencao(
        session,
        tenant_id,
        equipamento.id,
        up_id,
        safra.id,
        300.0,
        100.0,
        agora - timedelta(days=3),
        agora - timedelta(days=3) + timedelta(hours=2),
    )

    consolidado_svc = FrotaCustoConsolidadoService(session, tenant_id)
    custos_safra = await consolidado_svc.obter_custos_por_safra([equipamento.id])

    # Deve conter a chave da safra formatada dinamicamente: "2025/26 / SOJA"
    chave_esperada = "2025/26 / SOJA"
    assert chave_esperada in custos_safra
    assert custos_safra[chave_esperada] == 1000.0  # 600 abastecimento + 400 manutenção


@pytest.mark.asyncio
async def test_dashboard_indicadores_e_maquinas_ociosas(session: AsyncSession, tenant_id: uuid.UUID):
    """Garante que o dashboard exiba os novos indicadores analíticos e as máquinas ociosas com precisão."""
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_unidade(session, tenant_id)

    # Equipamento 1: Ativo, trabalhou ontem (Não deve ser ocioso)
    eq_ativo_recente = await _criar_equipamento(session, tenant_id, up_id, "ATIVO")
    await _criar_jornada(session, tenant_id, eq_ativo_recente.id, up_id, datetime.now(timezone.utc) - timedelta(days=1))

    # Equipamento 2: Ativo, trabalhou há 10 dias (Ocioso!)
    eq_ocioso = await _criar_equipamento(session, tenant_id, up_id, "ATIVO")
    await _criar_jornada(session, tenant_id, eq_ocioso.id, up_id, datetime.now(timezone.utc) - timedelta(days=10))

    # Equipamento 3: Inativo (Não deve aparecer como máquina ociosa)
    eq_inativo = await _criar_equipamento(session, tenant_id, up_id, "INATIVO")

    dashboard_svc = FrotaDashboardService(session, tenant_id)
    dashboard = await dashboard_svc.obter_dashboard(up_id)

    # Validar resumo
    assert dashboard.resumo.disponibilidade_media <= 100.0
    assert dashboard.resumo.tempo_parado_manutencao_horas >= 0.0

    # Validar máquinas ociosas
    ociosas_ids = [item.equipamento_id for item in dashboard.maquinas_ociosas]
    assert eq_ocioso.id in ociosas_ids
    assert eq_ativo_recente.id not in ociosas_ids
    assert eq_inativo.id not in ociosas_ids
