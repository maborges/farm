from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.eficiencia.service import EficienciaOperacionalAgricolaV1Service
from agricola.operacoes.models import OperacaoAgricola
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse
from core.cadastros.equipamentos.models import Equipamento
from operacional.models.apontamento import ApontamentoUso
from operacional.models.frota import JornadaEquipamento
from test_dre_agricola_v1 import _base_contexto, _criar_production_unit_extra


def _warning(codigo: str, origem: str) -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade="INCONSISTENCIA_MODERADA" if codigo.endswith("RECONCILIACAO") else "RISCO_ECONOMICO",
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid.uuid4())],
        meta={"codigo": codigo},
    )


def _dre_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    production_unit_id: uuid.UUID | None,
    area_total_ha: float,
    receita_liquida: float,
    custos_diretos: float,
    custos_operacionais: float,
    despesas_operacionais: float,
    warnings: list[DREWarning] | None = None,
) -> DREAgricolaResponse:
    warnings = warnings or []
    margem_bruta = round(receita_liquida - custos_diretos, 2)
    resultado_operacional = round(margem_bruta - custos_operacionais - despesas_operacionais, 2)
    custo_operacional_total = round(custos_diretos + custos_operacionais + despesas_operacionais, 2)
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
        cultura="SOJA",
        receita_bruta=receita_liquida,
        deducoes=0.0,
        receita_liquida=receita_liquida,
        custos_diretos=custos_diretos,
        custos_operacionais=custos_operacionais,
        margem_bruta=margem_bruta,
        despesas_operacionais=despesas_operacionais,
        resultado_operacional=resultado_operacional,
        kpis=DREAgricolaKpis(
            area_total_ha=area_total_ha,
            receita_liquida=receita_liquida,
            custo_operacional_total=custo_operacional_total,
            margem_bruta=margem_bruta,
            resultado_operacional=resultado_operacional,
            margem_pct=round((resultado_operacional / receita_liquida) * 100, 2) if receita_liquida > 0 else None,
            custo_por_hectare=round(custo_operacional_total / area_total_ha, 2) if area_total_ha > 0 else None,
            receita_por_hectare=round(receita_liquida / area_total_ha, 2) if area_total_ha > 0 else None,
            resultado_por_hectare=round(resultado_operacional / area_total_ha, 2) if area_total_ha > 0 else None,
            sujeito_reconciliacao=bool(warnings),
            observacao_reconciliacao="rentabilidade sujeita à reconciliação." if warnings else None,
            warnings_relevantes=[warning.codigo for warning in warnings],
        ),
        receita=DREAgricolaSection(),
        custos_diretos_detalhe=DREAgricolaSection(),
        custos_operacionais_detalhe=DREAgricolaSection(),
        despesas_operacionais_detalhe=DREAgricolaSection(),
        warnings=warnings,
        reconciliacao=DREReconcilacaoMeta(),
    )


def _rentabilidade_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    pu_a: uuid.UUID,
    pu_b: uuid.UUID | None = None,
    item_a_area: float = 10.0,
    item_a_resultado: float = 7000.0,
    item_b_area: float = 20.0,
    item_b_resultado: float = 10000.0,
) -> RentabilidadeAgricolaResponse:
    item_a = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_a,
        label="PU A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=item_a_area,
        resultado_operacional=item_a_resultado,
        margem_pct=round((item_a_resultado / (item_a_area * 1000.0)) * 100, 2) if item_a_area > 0 else None,
        receita_liquida_por_hectare=1000.0,
        resultado_por_hectare=round(item_a_resultado / item_a_area, 2) if item_a_area > 0 else None,
        warnings_relevantes=[],
    )
    items = [item_a]
    ranking = [item_a]
    warnings = [_warning("RENTABILIDADE_SAFRA_RECONCILIACAO", "rentabilidade_v1")]

    if pu_b is not None:
        item_b = RentabilidadeAgricolaItem(
            scope="PRODUCTION_UNIT",
            id=pu_b,
            label="PU B",
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            area_total_ha=item_b_area,
            resultado_operacional=item_b_resultado,
            margem_pct=round((item_b_resultado / (item_b_area * 1000.0)) * 100, 2) if item_b_area > 0 else None,
            receita_liquida_por_hectare=1000.0,
            resultado_por_hectare=round(item_b_resultado / item_b_area, 2) if item_b_area > 0 else None,
            warnings_relevantes=["MOVIMENTO_COM_CUSTO_SEM_ALLOCATION"],
        )
        item_a.posicao = 1
        item_b.posicao = 2
        items = [item_a, item_b]
        ranking = [item_a, item_b]
        warnings.append(_warning("MOVIMENTO_COM_CUSTO_SEM_ALLOCATION", "estoque_movimentos"))
    else:
        item_a.posicao = 1

    safra = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=item_a_area + (item_b_area if pu_b is not None else 0.0),
        resultado_operacional=item_a_resultado + (item_b_resultado if pu_b is not None else 0.0),
        margem_pct=round(((item_a_resultado + (item_b_resultado if pu_b is not None else 0.0)) / ((item_a_area + (item_b_area if pu_b is not None else 0.0)) * 1000.0)) * 100, 2)
        if (item_a_area + (item_b_area if pu_b is not None else 0.0)) > 0
        else None,
        receita_liquida_por_hectare=1000.0,
        resultado_por_hectare=round((item_a_resultado + (item_b_resultado if pu_b is not None else 0.0)) / (item_a_area + (item_b_area if pu_b is not None else 0.0)), 2)
        if (item_a_area + (item_b_area if pu_b is not None else 0.0)) > 0
        else None,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="rentabilidade sujeita à reconciliação.",
        warnings_relevantes=["RENTABILIDADE_SAFRA_RECONCILIACAO"],
    )

    return RentabilidadeAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=items,
        ranking=ranking,
        warnings=warnings,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="rentabilidade sujeita à reconciliação.",
    )


async def _criar_equipamento(session: AsyncSession, tenant_id: uuid.UUID, nome: str, unidade_produtiva_id: uuid.UUID) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TRATOR",
        nome=nome,
        combustivel="DIESEL",
        status="ATIVO",
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_jornada(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    safra_id: uuid.UUID,
    inicio: datetime,
    fim: datetime,
    horimetro_inicial: float,
    horimetro_final: float,
) -> JornadaEquipamento:
    jornada = JornadaEquipamento(
        tenant_id=tenant_id,
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra_id=safra_id,
        tipo_operacao="CAMPO",
        data_inicio=inicio,
        data_fim=fim,
        horimetro_inicial=horimetro_inicial,
        horimetro_final=horimetro_final,
        status="FINALIZADA",
    )
    session.add(jornada)
    await session.commit()
    await session.refresh(jornada)
    return jornada


async def _criar_apontamento(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    safra_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    jornada_id: uuid.UUID,
    data: datetime,
    area_ha_trabalhada: float,
    horimetro_inicio: float,
    horimetro_fim: float,
    custo_total: float,
) -> ApontamentoUso:
    apontamento = ApontamentoUso(
        tenant_id=tenant_id,
        equipamento_id=equipamento_id,
        jornada_id=jornada_id,
        data=data,
        turno="INTEGRAL",
        horimetro_inicio=horimetro_inicio,
        horimetro_fim=horimetro_fim,
        unidade_produtiva_id=unidade_produtiva_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        area_ha_trabalhada=area_ha_trabalhada,
        custo_total=custo_total,
        custo_por_ha=round(custo_total / area_ha_trabalhada, 2) if area_ha_trabalhada > 0 else None,
    )
    session.add(apontamento)
    await session.commit()
    await session.refresh(apontamento)
    return apontamento


async def _criar_operacao(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    talhao_id: uuid.UUID,
    tipo: str,
    descricao: str,
    data_realizada: date,
    hora_inicio: time,
    hora_fim: time,
    area_aplicada_ha: float,
    custo_total: float,
) -> OperacaoAgricola:
    operacao = OperacaoAgricola(
        tenant_id=tenant_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        talhao_id=talhao_id,
        tipo=tipo,
        subtipo=None,
        descricao=descricao,
        data_realizada=data_realizada,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        area_aplicada_ha=area_aplicada_ha,
        custo_total=custo_total,
        custo_por_ha=round(custo_total / area_aplicada_ha, 2) if area_aplicada_ha > 0 else 0.0,
        status="REALIZADA",
    )
    session.add(operacao)
    await session.commit()
    await session.refresh(operacao)
    return operacao


async def _criar_area_extra(session: AsyncSession, tenant_id: uuid.UUID, unidade_id: uuid.UUID, nome: str) -> uuid.UUID:
    area_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', :nome, 15.0, true, now(), now())"
        ),
        {"id": str(area_id), "tenant_id": str(tenant_id), "unidade_id": str(unidade_id), "nome": nome},
    )
    await session.commit()
    return area_id


@pytest.mark.asyncio
async def test_eficiencia_calcula_metricas_ranking_e_warning(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu_a, _, _, _ = await _base_contexto(session, tenant_id)
    area_b_id = await _criar_area_extra(session, tenant_id, unidade_id, "Talhão B")
    pu_b = await _criar_production_unit_extra(session, tenant_id, safra.id, cultivo_id, area_b_id)

    eq_a = await _criar_equipamento(session, tenant_id, "Trator A", unidade_id)
    eq_b = await _criar_equipamento(session, tenant_id, "Trator B", unidade_id)

    jornada_a = await _criar_jornada(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_a.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        inicio=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
        fim=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        horimetro_inicial=100.0,
        horimetro_final=104.0,
    )
    jornada_b = await _criar_jornada(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_b.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        inicio=datetime(2026, 1, 11, 8, 0, tzinfo=timezone.utc),
        fim=datetime(2026, 1, 11, 13, 0, tzinfo=timezone.utc),
        horimetro_inicial=200.0,
        horimetro_final=205.0,
    )

    await _criar_apontamento(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_a.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        jornada_id=jornada_a.id,
        data=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        area_ha_trabalhada=5.0,
        horimetro_inicio=100.0,
        horimetro_fim=104.0,
        custo_total=1000.0,
    )
    await _criar_apontamento(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_b.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        production_unit_id=pu_b.id,
        jornada_id=jornada_b.id,
        data=datetime(2026, 1, 11, 10, 0, tzinfo=timezone.utc),
        area_ha_trabalhada=10.0,
        horimetro_inicio=200.0,
        horimetro_fim=205.0,
        custo_total=5000.0,
    )

    await _criar_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Pulverização A",
        data_realizada=date(2026, 1, 10),
        hora_inicio=time(8, 0),
        hora_fim=time(10, 0),
        area_aplicada_ha=5.0,
        custo_total=2000.0,
    )
    await _criar_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        production_unit_id=pu_b.id,
        talhao_id=area_b_id,
        tipo="PLANTIO",
        descricao="Plantio B",
        data_realizada=date(2026, 1, 11),
        hora_inicio=time(8, 0),
        hora_fim=time(12, 0),
        area_aplicada_ha=10.0,
        custo_total=6000.0,
    )

    dre_response = _dre_response(
        tenant_id=tenant_id,
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
        production_unit_id=None,
        area_total_ha=30.0,
        receita_liquida=30000.0,
        custos_diretos=6000.0,
        custos_operacionais=2000.0,
        despesas_operacionais=1000.0,
        warnings=[_warning("DRE_AGRUPAMENTO_RECONCILIACAO", "dre_agricola_v1")],
    )
    rentabilidade_response = _rentabilidade_response(
        tenant_id=tenant_id,
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
        pu_a=pu_a.id,
        pu_b=pu_b.id,
        item_a_area=15.0,
        item_a_resultado=14000.0,
        item_b_area=10.0,
        item_b_resultado=5000.0,
    )

    calls: list[dict] = []

    class FakeDreService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append({"service": "dre", "kwargs": kwargs})
            return dre_response

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append({"service": "rentabilidade", "kwargs": kwargs})
            return rentabilidade_response

    with (
        patch("agricola.eficiencia.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.eficiencia.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
    ):
        response = await EficienciaOperacionalAgricolaV1Service(session, tenant_id).gerar(
            safra_id=safra.id,
            unidade_produtiva_id=unidade_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert [call["service"] for call in calls] == ["rentabilidade", "dre"]
    assert response.safra.custo_operacional_total == 9000.0
    assert response.safra.custo_operacional_por_hectare == 300.0
    assert response.safra.custo_operacional_por_operacao == 4500.0
    assert response.safra.horas_por_hectare == 0.6
    assert response.safra.hectares_por_jornada == 7.5
    assert response.safra.resultado_por_hectare == 700.0
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "indicadores sujeitos à reconciliação."
    assert {warning.codigo for warning in response.warnings} >= {
        "DRE_AGRUPAMENTO_RECONCILIACAO",
        "RENTABILIDADE_SAFRA_RECONCILIACAO",
        "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
        "EFICIENCIA_OPERACIONAL_DESVIO_CUSTO",
    }
    assert [item.id for item in response.ranking] == [str(pu_a.id), str(pu_b.id)]
    assert response.ranking[0].posicao == 1
    assert response.ranking[0].custo_operacional_por_hectare == 66.67
    assert response.ranking[1].posicao == 2
    assert response.production_units[0].warnings_relevantes == []
    assert response.production_units[1].warnings_relevantes == ["MOVIMENTO_COM_CUSTO_SEM_ALLOCATION"]
    assert [item.id for item in response.equipamentos] == [str(eq_a.id), str(eq_b.id)]
    assert response.equipamentos[0].custo_operacional_por_hectare == 200.0
    assert response.equipamentos[1].custo_operacional_por_hectare == 500.0
    assert [item.label for item in response.operacoes] == ["PULVERIZACAO", "PLANTIO"]


@pytest.mark.asyncio
async def test_eficiencia_isola_tenant_e_respeita_filtros(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu_a, _, _, _ = await _base_contexto(session, tenant_id)
    area_b_id = await _criar_area_extra(session, tenant_id, unidade_id, "Talhão B")
    pu_b = await _criar_production_unit_extra(session, tenant_id, safra.id, cultivo_id, area_b_id)
    foreign_tenant_id = uuid.uuid4()
    await _base_contexto(session, foreign_tenant_id)

    eq_a = await _criar_equipamento(session, tenant_id, "Trator A", unidade_id)
    eq_foreign = await _criar_equipamento(session, foreign_tenant_id, "Trator Estrangeiro", unidade_id)

    jornada_a = await _criar_jornada(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_a.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        inicio=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
        fim=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        horimetro_inicial=100.0,
        horimetro_final=104.0,
    )
    await _criar_jornada(
        session,
        tenant_id=eq_foreign.tenant_id,
        equipamento_id=eq_foreign.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        inicio=datetime(2026, 1, 11, 8, 0, tzinfo=timezone.utc),
        fim=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
        horimetro_inicial=200.0,
        horimetro_final=204.0,
    )

    await _criar_apontamento(
        session,
        tenant_id=tenant_id,
        equipamento_id=eq_a.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        jornada_id=jornada_a.id,
        data=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        area_ha_trabalhada=5.0,
        horimetro_inicio=100.0,
        horimetro_fim=104.0,
        custo_total=1000.0,
    )
    await _criar_apontamento(
        session,
        tenant_id=eq_foreign.tenant_id,
        equipamento_id=eq_foreign.id,
        unidade_produtiva_id=unidade_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        jornada_id=jornada_a.id,
        data=datetime(2026, 1, 11, 10, 0, tzinfo=timezone.utc),
        area_ha_trabalhada=99.0,
        horimetro_inicio=200.0,
        horimetro_fim=204.0,
        custo_total=99999.0,
    )

    await _criar_operacao(
        session,
        tenant_id=tenant_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        talhao_id=area_id,
        tipo="PULVERIZACAO",
        descricao="Pulverização A",
        data_realizada=date(2026, 1, 10),
        hora_inicio=time(8, 0),
        hora_fim=time(10, 0),
        area_aplicada_ha=5.0,
        custo_total=2000.0,
    )
    await _criar_operacao(
        session,
        tenant_id=eq_foreign.tenant_id,
        safra_id=safra.id,
        production_unit_id=pu_a.id,
        talhao_id=area_id,
        tipo="PLANTIO",
        descricao="Operação Estrangeira",
        data_realizada=date(2026, 1, 11),
        hora_inicio=time(8, 0),
        hora_fim=time(12, 0),
        area_aplicada_ha=50.0,
        custo_total=99999.0,
    )

    dre_response = _dre_response(
        tenant_id=tenant_id,
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
        production_unit_id=pu_a.id,
        area_total_ha=20.0,
        receita_liquida=20000.0,
        custos_diretos=4000.0,
        custos_operacionais=1000.0,
        despesas_operacionais=1000.0,
    )
    rentabilidade_response = _rentabilidade_response(
        tenant_id=tenant_id,
        safra_id=safra.id,
        unidade_produtiva_id=unidade_id,
        pu_a=pu_a.id,
    )

    calls: list[dict] = []

    class FakeDreService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append({"service": "dre", "kwargs": kwargs})
            return dre_response

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append({"service": "rentabilidade", "kwargs": kwargs})
            return rentabilidade_response

    with (
        patch("agricola.eficiencia.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.eficiencia.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
    ):
        response = await EficienciaOperacionalAgricolaV1Service(session, tenant_id).gerar(
            safra_id=safra.id,
            production_unit_id=pu_a.id,
            unidade_produtiva_id=unidade_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert len(calls) == 2
    assert calls[0]["kwargs"]["production_unit_id"] == pu_a.id
    assert calls[1]["kwargs"]["production_unit_id"] == pu_a.id
    assert response.production_unit_id == pu_a.id
    assert response.unidade_produtiva_id == unidade_id
    assert response.data_inicio == date(2026, 1, 1)
    assert response.data_fim == date(2026, 1, 31)
    assert response.safra.custo_operacional_total == 6000.0
    assert response.safra.custo_operacional_por_hectare == 300.0
    assert response.safra.horas_por_hectare == 0.8
    assert len(response.production_units) == 1
    assert response.production_units[0].id == str(pu_a.id)
    assert len(response.equipamentos) == 1
    assert response.equipamentos[0].label == "Trator A"
    assert len(response.operacoes) == 1
    assert response.operacoes[0].label == "PULVERIZACAO"
