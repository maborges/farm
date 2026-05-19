"""
Testes — Frota & Equipamentos — Step 08

Cobre apontamentos operacionais agrícolas, integração econômica,
produtividade, rastreabilidade e hardening multi-tenant/multi-UP.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa, PessoaRelacionamento, TipoRelacionamento
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.apontamento import ApontamentoUso
from operacional.schemas.apontamento import ApontamentoUsoCreate
from operacional.services.frota_apontamento_service import FrotaApontamentoService
from operacional.services.frota_agricultura_service import FrotaAgriculturaService


@pytest.fixture(autouse=True)
async def setup_step08_schema(session: AsyncSession):
    for ddl in (
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS jornada_id uuid",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS safra_id uuid",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS production_unit_id uuid",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS area_ha_trabalhada numeric(12,4)",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS quantidade_produzida numeric(18,6)",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS quantidade_aplicada numeric(18,6)",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS custo_total numeric(15,2)",
        "ALTER TABLE frota_apontamentos_uso ADD COLUMN IF NOT EXISTS custo_por_ha numeric(15,4)",
    ):
        await session.execute(text(ddl))
    await session.commit()


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


async def _criar_area(session: AsyncSession, tenant_id: uuid.UUID, up_id: uuid.UUID, nome: str) -> uuid.UUID:
    area_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :up_id, 'TALHAO', :nome, 100.0, true, now(), now())"
        ),
        {"id": str(area_id), "tenant_id": str(tenant_id), "up_id": str(up_id), "nome": nome},
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
        area_ha=100.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _criar_operador(session: AsyncSession, tenant_id: uuid.UUID, up_id: uuid.UUID, nome: str) -> Pessoa:
    pessoa = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        ativo=True,
    )
    session.add(pessoa)
    await session.flush()

    tipo_rel = TipoRelacionamento(
        tenant_id=tenant_id,
        codigo="FUNCIONARIO",
        nome="Funcionário",
        sistema=False,
        ativo=True,
    )
    session.add(tipo_rel)
    await session.flush()

    session.add(
        PessoaRelacionamento(
            pessoa_id=pessoa.id,
            tipo_id=tipo_rel.id,
            unidade_produtiva_id=up_id,
            ativo_desde=date.today(),
        )
    )
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


async def _criar_jornada_raw(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    up_id: uuid.UUID,
    operador_id: uuid.UUID,
    safra_id: uuid.UUID,
    talhao_id: uuid.UUID,
) -> uuid.UUID:
    jornada_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_jornadas_equipamento "
            "(id, tenant_id, equipamento_id, operador_id, unidade_produtiva_id, safra_id, talhao_id, tipo_operacao, data_inicio, status, horimetro_inicial, km_inicial, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :eq_id, :op_id, :up_id, :safra_id, :talhao_id, 'COLHEITA', :data_inicio, 'ABERTA', 100.0, 500.0, now(), now())"
        ),
        {
            "id": str(jornada_id),
            "tenant_id": str(tenant_id),
            "eq_id": str(equipamento_id),
            "op_id": str(operador_id),
            "up_id": str(up_id),
            "safra_id": str(safra_id),
            "talhao_id": str(talhao_id),
            "data_inicio": datetime.now(timezone.utc) - timedelta(hours=2),
        },
    )
    await session.commit()
    return jornada_id


async def _criar_operacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    talhao_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    operador_id: uuid.UUID,
    equipamento_id: uuid.UUID,
) -> OperacaoAgricola:
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        talhao_id=talhao_id,
        tipo="PULVERIZACAO",
        descricao="Pulverização de teste",
        data_realizada=date.today(),
        area_aplicada_ha=12.5,
        maquina_id=equipamento_id,
        operador_id=operador_id,
        custo_total=250.0,
        custo_por_ha=20.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.commit()
    await session.refresh(operacao)
    return operacao


@pytest.mark.asyncio
async def test_apontamento_valido_cria_allocacao_e_rastreabilidade(session: AsyncSession, tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Step08")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Step08")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador = await _criar_operador(session, tenant_id, up_id, "Operador Step08")
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator Step08")
    jornada_id = await _criar_jornada_raw(session, tenant_id, equipamento.id, up_id, operador.id, safra.id, area_id)
    operacao = await _criar_operacao(session, tenant_id, safra.id, area_id, pu.id, operador.id, equipamento.id)

    svc = FrotaApontamentoService(session, tenant_id)
    apontamento = await svc.criar(
        ApontamentoUsoCreate(
            equipamento_id=equipamento.id,
            operador_id=operador.id,
            jornada_id=jornada_id,
            data=datetime.now(timezone.utc),
            turno="INTEGRAL",
            horimetro_inicio=100.0,
            horimetro_fim=108.0,
            km_inicio=500.0,
            km_fim=516.0,
            unidade_produtiva_id=up_id,
            safra_id=safra.id,
            production_unit_id=pu.id,
            talhao_id=area_id,
            operacao_id=operacao.id,
            area_ha_trabalhada=12.5,
            quantidade_aplicada=250.0,
            custo_total=350.0,
            custo_por_ha=28.0,
            observacoes="Apontamento de validação",
        )
    )
    await session.commit()

    await session.refresh(apontamento)
    assert apontamento.jornada_id == jornada_id
    assert apontamento.safra_id == safra.id
    assert apontamento.production_unit_id == pu.id
    assert float(apontamento.area_ha_trabalhada or 0.0) == 12.5
    assert float(apontamento.custo_total or 0.0) == 350.0

    equipamento_db = await session.get(Equipamento, equipamento.id)
    assert float(equipamento_db.horimetro_atual) == 108.0

    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "MANUAL",
                CostAllocation.source_id == apontamento.id,
            )
        )
    ).scalar_one()
    assert allocation.production_unit_id == pu.id
    assert float(allocation.amount) == 350.0

    resumo = await FrotaAgriculturaService(session, tenant_id).obter_resumo(unidade_produtiva_id=up_id)
    assert resumo.resumo.apontamentos_total == 1
    assert resumo.resumo.hectares_totais == 12.5
    assert resumo.resumo.produtividade_media_ha_hora == 1.56
    assert resumo.resumo.custo_medio_por_ha == 28.0
    assert resumo.apontamentos_por_operacao[0].tipo_operacao == "PULVERIZACAO"
    assert resumo.apontamentos_por_operador[0].operador_nome == "Operador Step08"
    assert resumo.equipamentos_por_apontamento[0].equipamento_nome == "Trator Step08"


@pytest.mark.asyncio
async def test_apontamento_rejeita_tenant_mismatch_e_operador_sem_acesso(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    await _garantir_tenant(session, outro_tenant_id)
    up_a = await _criar_up(session, tenant_id, "UP Step08-A")
    up_b = await _criar_up(session, tenant_id, "UP Step08-B")
    up_outro = await _criar_up(session, outro_tenant_id, "UP Step08-X")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_a, "Talhão Step08-B")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador_outro = await _criar_operador(session, outro_tenant_id, up_outro, "Operador Outro Tenant")
    equipamento = await _criar_equipamento(session, tenant_id, up_a, "Trator Step08-B")
    jornada_id = await _criar_jornada_raw(session, tenant_id, equipamento.id, up_a, operador_outro.id, safra.id, area_id)

    with pytest.raises(BusinessRuleError, match="Pessoa não localizada"):
        await FrotaApontamentoService(session, tenant_id).criar(
            ApontamentoUsoCreate(
                equipamento_id=equipamento.id,
                operador_id=operador_outro.id,
                jornada_id=jornada_id,
                data=datetime.now(timezone.utc),
                horimetro_inicio=100.0,
                horimetro_fim=101.0,
                km_inicio=500.0,
                km_fim=502.0,
                unidade_produtiva_id=up_a,
                safra_id=safra.id,
                production_unit_id=pu.id,
                talhao_id=area_id,
                area_ha_trabalhada=2.0,
                custo_total=40.0,
            )
        )

    equipamento_outro = await _criar_equipamento(session, outro_tenant_id, up_outro, "Trator Outro Tenant")
    with pytest.raises(EntityNotFoundError, match="Equipamento não encontrado"):
        await FrotaApontamentoService(session, tenant_id).criar(
            ApontamentoUsoCreate(
                equipamento_id=equipamento_outro.id,
                data=datetime.now(timezone.utc),
                horimetro_inicio=100.0,
                horimetro_fim=101.0,
                km_inicio=500.0,
                km_fim=502.0,
            )
        )


@pytest.mark.asyncio
async def test_produtividade_operacional_consistente_por_talhao(session: AsyncSession, tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id, "UP Step08-C")
    safra = await _criar_safra(session, tenant_id)
    area_id = await _criar_area(session, tenant_id, up_id, "Talhão Step08-C")
    cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
    pu = await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, area_id)
    operador = await _criar_operador(session, tenant_id, up_id, "Operador Talhão")
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator Step08-C")
    jornada_id = await _criar_jornada_raw(session, tenant_id, equipamento.id, up_id, operador.id, safra.id, area_id)
    operacao = await _criar_operacao(session, tenant_id, safra.id, area_id, pu.id, operador.id, equipamento.id)

    svc = FrotaApontamentoService(session, tenant_id)
    await svc.criar(
        ApontamentoUsoCreate(
            equipamento_id=equipamento.id,
            operador_id=operador.id,
            jornada_id=jornada_id,
            data=datetime.now(timezone.utc),
            horimetro_inicio=100.0,
            horimetro_fim=106.0,
            km_inicio=500.0,
            km_fim=512.0,
            unidade_produtiva_id=up_id,
            safra_id=safra.id,
            production_unit_id=pu.id,
            talhao_id=area_id,
            operacao_id=operacao.id,
            area_ha_trabalhada=6.0,
            quantidade_produzida=18.0,
            custo_total=180.0,
        )
    )
    await session.commit()

    resumo = await FrotaAgriculturaService(session, tenant_id).obter_resumo(unidade_produtiva_id=up_id)
    assert resumo.resumo.apontamentos_total == 1
    assert resumo.resumo.hectares_totais == 6.0
    assert resumo.resumo.produtividade_media_ha_hora == 1.0
    assert resumo.apontamentos_por_talhao[0].talhao_nome == "Talhão Step08-C"
    assert resumo.apontamentos_por_talhao[0].produtividade_ha_hora == 1.0
