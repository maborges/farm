from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.rentabilidade.service import RentabilidadeAgricolaV1Service
from test_dre_agricola_v1 import _base_contexto, _criar_production_unit_extra, _garantir_tenant


def _warning(codigo: str, origem: str = "dre_agricola_v1") -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade="RISCO_ECONOMICO",
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid.uuid4())],
        meta={"codigo": codigo},
    )


def _dre_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    production_unit_id: uuid.UUID | None,
    unidade_produtiva_id: uuid.UUID | None,
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
    margem_pct = round((resultado_operacional / receita_liquida) * 100, 2) if receita_liquida > 0 else None
    custo_operacional_total = round(custos_diretos + custos_operacionais + despesas_operacionais, 2)
    receita_por_ha = round(receita_liquida / area_total_ha, 2) if area_total_ha > 0 else None
    resultado_por_ha = round(resultado_operacional / area_total_ha, 2) if area_total_ha > 0 else None
    warnings_relevantes = [warning.codigo for warning in warnings]

    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
        cultura="SOJA",
        production_unit_ids=[production_unit_id] if production_unit_id else [],
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
            margem_pct=margem_pct,
            custo_por_hectare=round(custo_operacional_total / area_total_ha, 2) if area_total_ha > 0 else None,
            receita_por_hectare=receita_por_ha,
            resultado_por_hectare=resultado_por_ha,
            sujeito_reconciliacao=bool(warnings_relevantes),
            observacao_reconciliacao="rentabilidade sujeita à reconciliação." if warnings_relevantes else None,
            warnings_relevantes=warnings_relevantes,
        ),
        receita=DREAgricolaSection(),
        custos_diretos_detalhe=DREAgricolaSection(),
        custos_operacionais_detalhe=DREAgricolaSection(),
        despesas_operacionais_detalhe=DREAgricolaSection(),
        warnings=warnings,
        reconciliacao=DREReconcilacaoMeta(),
    )


@pytest.mark.asyncio
async def test_rentabilidade_calcula_ranking_e_metricas(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu_a, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    area_b_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', 'Talhão B', 20.0, true, now(), now())"
        ),
        {"id": str(area_b_id), "tenant_id": str(tenant_id), "unidade_id": str(unidade_id)},
    )
    await session.commit()

    pu_b = await _criar_production_unit_extra(session, tenant_id, safra.id, cultivo_id, area_b_id)

    calls: list[dict] = []
    dre_map: dict[uuid.UUID | None, DREAgricolaResponse] = {
        None: _dre_response(
            tenant_id=tenant_id,
            safra_id=safra.id,
            production_unit_id=None,
            unidade_produtiva_id=unidade_id,
            area_total_ha=30.0,
            receita_liquida=30000.0,
            custos_diretos=10000.0,
            custos_operacionais=3000.0,
            despesas_operacionais=2000.0,
            warnings=[_warning("RENTABILIDADE_SAFRA_RECONCILIACAO")],
        ),
        pu_a.id: _dre_response(
            tenant_id=tenant_id,
            safra_id=safra.id,
            production_unit_id=pu_a.id,
            unidade_produtiva_id=unidade_id,
            area_total_ha=10.0,
            receita_liquida=12000.0,
            custos_diretos=5000.0,
            custos_operacionais=1500.0,
            despesas_operacionais=500.0,
        ),
        pu_b.id: _dre_response(
            tenant_id=tenant_id,
            safra_id=safra.id,
            production_unit_id=pu_b.id,
            unidade_produtiva_id=unidade_id,
            area_total_ha=20.0,
            receita_liquida=18000.0,
            custos_diretos=6000.0,
            custos_operacionais=2000.0,
            despesas_operacionais=2000.0,
            warnings=[_warning("MOVIMENTO_COM_CUSTO_SEM_ALLOCATION", origem="estoque_movimentos")],
        ),
    }

    class FakeDreService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append(kwargs)
            return dre_map[kwargs.get("production_unit_id")]

    with patch("agricola.rentabilidade.service.DREAgricolaV1Service", FakeDreService):
        response = await RentabilidadeAgricolaV1Service(session, tenant_id).gerar(
            safra_id=safra.id,
            unidade_produtiva_id=unidade_id,
        )

    assert response.safra.resultado_operacional == 15000.0
    assert response.safra.margem_pct == pytest.approx(50.0)
    assert response.safra.receita_liquida_por_hectare == 1000.0
    assert response.safra.resultado_por_hectare == 500.0

    assert [item.id for item in response.ranking] == [pu_a.id, pu_b.id]
    assert response.ranking[0].posicao == 1
    assert response.ranking[0].resultado_por_hectare == 500.0
    assert response.ranking[1].posicao == 2
    assert response.ranking[1].resultado_por_hectare == 400.0

    assert {item.id for item in response.production_units} == {pu_a.id, pu_b.id}
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "rentabilidade sujeita à reconciliação."
    assert "RENTABILIDADE_SAFRA_RECONCILIACAO" in {warning.codigo for warning in response.warnings}
    assert "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" in {warning.codigo for warning in response.warnings}
    assert all(call["safra_id"] == safra.id for call in calls)
    assert all(call["unidade_produtiva_id"] == unidade_id for call in calls)


@pytest.mark.asyncio
async def test_rentabilidade_isola_tenant_e_respeita_ranking(session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    unidade_a, area_a, safra_a, cultivo_a, pu_a1, produto_a, deposito_a, unidade_ha_id_a = await _base_contexto(session, tenant_a)
    area_a2_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', 'Talhão A2', 25.0, true, now(), now())"
        ),
        {"id": str(area_a2_id), "tenant_id": str(tenant_a), "unidade_id": str(unidade_a)},
    )
    await session.commit()
    pu_a2 = await _criar_production_unit_extra(session, tenant_a, safra_a.id, cultivo_a, area_a2_id)

    unidade_b, area_b, safra_b, cultivo_b, pu_b, produto_b, deposito_b, unidade_ha_id_b = await _base_contexto(session, tenant_b)

    dre_map: dict[uuid.UUID | None, DREAgricolaResponse] = {
        None: _dre_response(
            tenant_id=tenant_a,
            safra_id=safra_a.id,
            production_unit_id=None,
            unidade_produtiva_id=unidade_a,
            area_total_ha=55.0,
            receita_liquida=22000.0,
            custos_diretos=7000.0,
            custos_operacionais=3000.0,
            despesas_operacionais=2000.0,
        ),
        pu_a1.id: _dre_response(
            tenant_id=tenant_a,
            safra_id=safra_a.id,
            production_unit_id=pu_a1.id,
            unidade_produtiva_id=unidade_a,
            area_total_ha=30.0,
            receita_liquida=18000.0,
            custos_diretos=5000.0,
            custos_operacionais=2000.0,
            despesas_operacionais=1000.0,
        ),
        pu_a2.id: _dre_response(
            tenant_id=tenant_a,
            safra_id=safra_a.id,
            production_unit_id=pu_a2.id,
            unidade_produtiva_id=unidade_a,
            area_total_ha=25.0,
            receita_liquida=14000.0,
            custos_diretos=5000.0,
            custos_operacionais=1000.0,
            despesas_operacionais=1000.0,
        ),
    }

    class FakeDreService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            production_unit_id = kwargs.get("production_unit_id")
            if production_unit_id not in dre_map:
                raise AssertionError(f"ProductionUnit fora do tenant não deveria ser consultada: {production_unit_id}")
            return dre_map[production_unit_id]

    with patch("agricola.rentabilidade.service.DREAgricolaV1Service", FakeDreService):
        response = await RentabilidadeAgricolaV1Service(session, tenant_a).gerar(
            safra_id=safra_a.id,
            unidade_produtiva_id=unidade_a,
        )

    assert {item.id for item in response.production_units} == {pu_a1.id, pu_a2.id}
    assert pu_b.id not in {item.id for item in response.production_units}
    assert response.ranking[0].resultado_por_hectare >= response.ranking[1].resultado_por_hectare


@pytest.mark.asyncio
async def test_rentabilidade_respeita_filtros_e_propagacao_de_warnings(session: AsyncSession):
    tenant_id = uuid.uuid4()
    unidade_id, area_id, safra, cultivo_id, pu, produto, deposito, unidade_ha_id = await _base_contexto(session, tenant_id)
    inicio = date(2026, 1, 1)
    fim = date(2026, 1, 31)

    calls: list[dict] = []
    dre = _dre_response(
        tenant_id=tenant_id,
        safra_id=safra.id,
        production_unit_id=pu.id,
        unidade_produtiva_id=unidade_id,
        area_total_ha=30.0,
        receita_liquida=9000.0,
        custos_diretos=2000.0,
        custos_operacionais=1000.0,
        despesas_operacionais=500.0,
        warnings=[_warning("MOVIMENTO_COM_CUSTO_SEM_ALLOCATION")],
    )

    class FakeDreService:
        def __init__(self, session, tenant_id):
            self.session = session
            self.tenant_id = tenant_id

        async def gerar(self, **kwargs):
            calls.append(kwargs)
            return dre

    with patch("agricola.rentabilidade.service.DREAgricolaV1Service", FakeDreService):
        response = await RentabilidadeAgricolaV1Service(session, tenant_id).gerar(
            safra_id=safra.id,
            unidade_produtiva_id=unidade_id,
            production_unit_id=pu.id,
            data_inicio=inicio,
            data_fim=fim,
        )

    assert len(calls) == 1
    assert calls[0]["safra_id"] == safra.id
    assert calls[0]["production_unit_id"] == pu.id
    assert calls[0]["unidade_produtiva_id"] == unidade_id
    assert calls[0]["data_inicio"] == inicio
    assert calls[0]["data_fim"] == fim
    assert response.safra.production_unit_id == pu.id
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "rentabilidade sujeita à reconciliação."
    assert response.warnings[0].codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION"
