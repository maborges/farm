"""
Testes — Frota & Equipamentos — Step 09

Cobre indicadores executivos consolidados, rentabilidade operacional,
rankings já existentes e isolamento multi-tenant.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.safras.models import Safra
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa
from operacional.models.abastecimento import Abastecimento
from operacional.models.apontamento import ApontamentoUso
from operacional.models.frota import JornadaEquipamento, RegistroManutencao
from operacional.services.frota_dashboard_service import FrotaDashboardService


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": nome, "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_up(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> uuid.UUID:
    up_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(up_id), "tenant_id": str(tenant_id), "nome": nome},
    )
    await session.commit()
    return up_id


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


async def _criar_pessoa(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> Pessoa:
    pessoa = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        ativo=True,
    )
    session.add(pessoa)
    await session.commit()
    await session.refresh(pessoa)
    return pessoa


async def _criar_equipamento(session: AsyncSession, tenant_id: uuid.UUID, up_id: uuid.UUID, nome: str) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=up_id,
        nome=nome,
        tipo="TRATOR",
        combustivel="DIESEL",
        status="ATIVO",
        horimetro_atual=100.0,
        km_atual=500.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_jornada_finalizada(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    up_id: uuid.UUID,
    operador_id: uuid.UUID,
    safra_id: uuid.UUID,
) -> JornadaEquipamento:
    jornada = JornadaEquipamento(
        tenant_id=tenant_id,
        equipamento_id=equipamento_id,
        operador_id=operador_id,
        unidade_produtiva_id=up_id,
        safra_id=safra_id,
        talhao_id=None,
        tipo_operacao="COLHEITA",
        data_inicio=datetime.now(timezone.utc) - timedelta(hours=4),
        data_fim=datetime.now(timezone.utc) - timedelta(hours=1),
        horimetro_inicial=100.0,
        horimetro_final=140.0,
        km_inicial=500.0,
        km_final=540.0,
        status="FINALIZADA",
        aberta_por_id=operador_id,
        encerrada_por_id=operador_id,
    )
    session.add(jornada)
    await session.commit()
    await session.refresh(jornada)
    return jornada


async def _criar_abastecimento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    operador_id: uuid.UUID,
    safra_id: uuid.UUID,
    litros: float,
    custo_total: float,
) -> None:
    session.add(
        Abastecimento(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            data=datetime.now(timezone.utc) - timedelta(days=1),
            operador_id=operador_id,
            safra_id=safra_id,
            talhao_id=None,
            horimetro_na_data=140.0,
            km_na_data=540.0,
            tipo_combustivel="DIESEL",
            litros=litros,
            preco_litro=10.0,
            custo_total=custo_total,
            tanque_cheio=True,
            local="INTERNO",
            observacoes="Teste Step09",
        )
    )
    await session.commit()


async def _criar_manutencao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    safra_id: uuid.UUID,
    tipo: str,
    custo_total: float,
) -> None:
    session.add(
        RegistroManutencao(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            os_id=None,
            safra_id=safra_id,
            talhao_id=None,
            data_realizacao=datetime.now(timezone.utc) - timedelta(days=2),
            tipo=tipo,
            descricao=f"{tipo} Step09",
            custo_total=custo_total,
            executado_por_id=None,
            horimetro_na_data=140.0,
            km_na_data=540.0,
            tecnico_responsavel=None,
        )
    )
    await session.commit()


async def _criar_apontamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    jornada_id: uuid.UUID,
    operador_id: uuid.UUID,
    up_id: uuid.UUID,
    safra_id: uuid.UUID,
    area_ha: float,
    custo_total: float,
) -> None:
    session.add(
        ApontamentoUso(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            jornada_id=jornada_id,
            operador_id=operador_id,
            data=datetime.now(timezone.utc) - timedelta(hours=3),
            turno="INTEGRAL",
            horimetro_inicio=100.0,
            horimetro_fim=140.0,
            km_inicio=500.0,
            km_fim=540.0,
            unidade_produtiva_id=up_id,
            safra_id=safra_id,
            production_unit_id=None,
            talhao_id=None,
            operacao_id=None,
            area_ha_trabalhada=area_ha,
            quantidade_produzida=None,
            quantidade_aplicada=None,
            custo_total=custo_total,
            custo_por_ha=round(custo_total / area_ha, 2) if area_ha > 0 else None,
            implementos_ids=[],
            combustivel_consumido_l=None,
            observacoes="Apontamento Step09",
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_dashboard_exec_consolida_rentabilidade_e_ranking(session: AsyncSession):
    tenant_principal = uuid.uuid4()
    tenant_outro = uuid.uuid4()
    await _garantir_tenant(session, tenant_principal, "Tenant Step09")
    await _garantir_tenant(session, tenant_outro, "Tenant Ignorado")

    up_principal = await _criar_up(session, tenant_principal, "UP Principal")
    up_outro = await _criar_up(session, tenant_outro, "UP Externa")
    safra_principal = await _criar_safra(session, tenant_principal)
    await _criar_safra(session, tenant_outro)

    operador = await _criar_pessoa(session, tenant_principal, "Operador Step09")
    equipamento_prod = await _criar_equipamento(session, tenant_principal, up_principal, "Trator Produtivo")
    equipamento_ocioso = await _criar_equipamento(session, tenant_principal, up_principal, "Trator Ocioso")
    equipamento_terceiro = await _criar_equipamento(session, tenant_outro, up_outro, "Trator Outro Tenant")

    jornada = await _criar_jornada_finalizada(
        session,
        tenant_principal,
        equipamento_prod.id,
        up_principal,
        operador.id,
        safra_principal.id,
    )
    await _criar_abastecimento(session, tenant_principal, equipamento_prod.id, operador.id, safra_principal.id, litros=20.0, custo_total=200.0)
    await _criar_manutencao(session, tenant_principal, equipamento_prod.id, safra_principal.id, "PREVENTIVA", 300.0)
    await _criar_manutencao(session, tenant_principal, equipamento_prod.id, safra_principal.id, "CORRETIVA", 400.0)
    await _criar_apontamento(
        session,
        tenant_principal,
        equipamento_prod.id,
        jornada.id,
        operador.id,
        up_principal,
        safra_principal.id,
        area_ha=10.0,
        custo_total=1000.0,
    )

    # Dados do outro tenant não devem contaminar a consolidação do tenant principal.
    await _criar_abastecimento(session, tenant_outro, equipamento_terceiro.id, operador.id, safra_principal.id, litros=50.0, custo_total=5000.0)

    dashboard = await FrotaDashboardService(session, tenant_principal).obter_dashboard(unidade_produtiva_id=up_principal)

    assert dashboard.resumo.total_equipamentos == 2
    assert dashboard.resumo.custo_operacional_total == 900.0
    assert dashboard.resumo.custo_preventivo_total == 300.0
    assert dashboard.resumo.custo_corretivo_total == 400.0
    assert dashboard.resumo.hectares_totais_apontados == 10.0
    assert dashboard.resumo.custo_por_hectare == 100.0
    assert dashboard.resumo.indice_rentabilidade_operacional == 11.11
    assert dashboard.resumo.equipamentos_ociosos == 1
    assert dashboard.ranking_maior_custo[0].equipamento_id == equipamento_prod.id
    assert dashboard.maquinas_ociosas and dashboard.maquinas_ociosas[0].equipamento_id == equipamento_ocioso.id
    assert dashboard.operadores_produtividade and dashboard.operadores_produtividade[0].operador_id == operador.id


@pytest.mark.asyncio
async def test_dashboard_exec_isola_tenant(session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _garantir_tenant(session, tenant_a, "Tenant A")
    await _garantir_tenant(session, tenant_b, "Tenant B")

    up_a = await _criar_up(session, tenant_a, "UP A")
    up_b = await _criar_up(session, tenant_b, "UP B")
    safra_a = await _criar_safra(session, tenant_a)
    operador = await _criar_pessoa(session, tenant_a, "Operador A")

    equipamento_a = await _criar_equipamento(session, tenant_a, up_a, "Equipamento A")
    equipamento_b = await _criar_equipamento(session, tenant_b, up_b, "Equipamento B")
    jornada_a = await _criar_jornada_finalizada(session, tenant_a, equipamento_a.id, up_a, operador.id, safra_a.id)
    await _criar_apontamento(
        session,
        tenant_a,
        equipamento_a.id,
        jornada_a.id,
        operador.id,
        up_a,
        safra_a.id,
        area_ha=5.0,
        custo_total=250.0,
    )

    # Registro de outro tenant com custo muito maior não pode alterar o dashboard do tenant A.
    await _criar_abastecimento(session, tenant_b, equipamento_b.id, operador.id, safra_a.id, litros=90.0, custo_total=9000.0)

    dashboard = await FrotaDashboardService(session, tenant_a).obter_dashboard(unidade_produtiva_id=up_a)

    ids = {item.equipamento_id for item in dashboard.equipamentos}
    assert equipamento_a.id in ids
    assert equipamento_b.id not in ids
    assert dashboard.resumo.custo_operacional_total == 0.0
    assert dashboard.resumo.hectares_totais_apontados == 5.0
