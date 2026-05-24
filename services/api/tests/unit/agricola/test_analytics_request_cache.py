from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre.kpis_service import AgricolaDreKpiService
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.dre.service import DREAgricolaV1Service
from agricola.rentabilidade.service import RentabilidadeAgricolaV1Service, _ScopedProductionUnit
from core.services.analytics_request_cache import clear_analytics_request_cache


@pytest.fixture(autouse=True)
def _limpar_cache_analytics():
    clear_analytics_request_cache()
    yield
    clear_analytics_request_cache()


def _fake_dre_response(
    *,
    tenant_id: UUID,
    safra_id: UUID,
    unidade_produtiva_id: UUID,
    production_unit_id: UUID,
) -> DREAgricolaResponse:
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
        cultura="SOJA",
        production_unit_ids=[production_unit_id],
        receita_bruta=100.0,
        deducoes=0.0,
        receita_liquida=100.0,
        custos_diretos=20.0,
        custos_operacionais=10.0,
        margem_bruta=80.0,
        despesas_operacionais=5.0,
        resultado_operacional=65.0,
        receita=DREAgricolaSection(valor=100.0),
        custos_diretos_detalhe=DREAgricolaSection(valor=20.0),
        custos_operacionais_detalhe=DREAgricolaSection(valor=10.0),
        despesas_operacionais_detalhe=DREAgricolaSection(valor=5.0),
        kpis=DREAgricolaKpis(
            area_total_ha=10.0,
            receita_liquida=100.0,
            custo_operacional_total=35.0,
            margem_bruta=80.0,
            resultado_operacional=65.0,
            margem_pct=65.0,
            custo_por_hectare=3.5,
            receita_por_hectare=10.0,
            resultado_por_hectare=6.5,
            sujeito_reconciliacao=False,
            warnings_relevantes=[],
        ),
        warnings=[
            DREWarning(
                codigo="CUSTO_HECTARE_ACIMA_MEDIA",
                titulo="Custo acima da média",
                severidade="INCONSISTENCIA_MODERADA",
                mensagem="Aviso sintético de teste.",
                origem="test",
            )
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "altered_kwargs",
    [
        {"safra_id": uuid4()},
        {"unidade_produtiva_id": uuid4()},
        {"production_unit_id": uuid4()},
        {"data_inicio": date(2026, 2, 1)},
        {"data_fim": date(2026, 2, 28)},
    ],
)
async def test_dre_cache_respeita_escopo_e_tenant(altered_kwargs):
    session = AsyncMock(spec=AsyncSession)
    tenant_a = uuid4()
    tenant_b = uuid4()
    base_safra_id = uuid4()
    base_unidade_produtiva_id = uuid4()
    base_production_unit_id = uuid4()
    base_args = {
        "safra_id": base_safra_id,
        "unidade_produtiva_id": base_unidade_produtiva_id,
        "production_unit_id": base_production_unit_id,
        "data_inicio": date(2026, 1, 1),
        "data_fim": date(2026, 1, 31),
    }

    async def fake_resolver(
        *,
        safra_id,
        unidade_produtiva_id,
        production_unit_id,
        production_unit_ids,
        cultura,
        unidade_operacional_id,
    ):
        effective_production_unit_id = production_unit_id or base_production_unit_id
        return {
            "production_units": [
                SimpleNamespace(id=effective_production_unit_id, area_ha=10.0),
            ],
            "production_unit_ids": [effective_production_unit_id],
            "safra_id": safra_id,
            "safra": None,
            "cultura": cultura or "SOJA",
            "unidade_produtiva_id": unidade_produtiva_id,
            "unidade_operacional_id": unidade_operacional_id,
            "unidade_operacional_resolvida": None,
        }

    async def fake_consolidar_costs(scope, *, direct, data_inicio=None, data_fim=None):
        return DREAgricolaSection(valor=20.0 if direct else 10.0)

    with (
        patch.object(DREAgricolaV1Service, "_resolver_escopo", new=AsyncMock(side_effect=fake_resolver)) as resolver_mock,
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_receitas",
            new=AsyncMock(return_value=(DREAgricolaSection(valor=100.0), 0.0, [], 0)),
        ) as receitas_mock,
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_costs",
            new=AsyncMock(side_effect=fake_consolidar_costs),
        ) as costs_mock,
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_despesas",
            new=AsyncMock(return_value=(DREAgricolaSection(valor=5.0), 0)),
        ) as despesas_mock,
        patch.object(
            DREAgricolaV1Service,
            "_montar_reconciliacao",
            new=AsyncMock(return_value=DREReconcilacaoMeta()),
        ) as reconc_mock,
        patch.object(
            DREAgricolaV1Service,
            "_montar_warnings",
            new=AsyncMock(return_value=[]),
        ) as warnings_mock,
    ):
        svc_a = DREAgricolaV1Service(session, tenant_a)
        resposta_1 = await svc_a.gerar(**base_args)
        resposta_2 = await svc_a.gerar(**base_args)
        await svc_a.gerar(**{**base_args, **altered_kwargs})

        svc_b = DREAgricolaV1Service(session, tenant_b)
        await svc_b.gerar(**base_args)

    assert resposta_1.model_dump() == resposta_2.model_dump()
    assert resolver_mock.await_count == 4
    assert receitas_mock.await_count == 3
    assert costs_mock.await_count == 6
    assert despesas_mock.await_count == 3
    assert reconc_mock.await_count == 3
    assert warnings_mock.await_count == 3


@pytest.mark.asyncio
async def test_rentabilidade_reaproveita_dre_no_mesmo_contexto():
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    scope_unit = _ScopedProductionUnit(
        id=production_unit_id,
        safra_id=safra_id,
        area_id=uuid4(),
        area_nome="Talhão teste",
        unidade_produtiva_id=unidade_produtiva_id,
        area_ha=10.0,
    )
    fake_dre = _fake_dre_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )

    with (
        patch.object(
            RentabilidadeAgricolaV1Service,
            "_listar_production_units",
            new=AsyncMock(return_value=[scope_unit]),
        ) as listar_mock,
        patch.object(
            DREAgricolaV1Service,
            "gerar",
            new=AsyncMock(return_value=fake_dre),
        ) as dre_mock,
    ):
        service = RentabilidadeAgricolaV1Service(session, tenant_id)
        resposta_1 = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )
        resposta_2 = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert resposta_1.model_dump() == resposta_2.model_dump()
    assert listar_mock.await_count == 1
    assert dre_mock.await_count == 1


@pytest.mark.asyncio
async def test_request_cache_nao_vaza_entre_requests():
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()

    with (
        patch.object(DREAgricolaV1Service, "_resolver_escopo", new=AsyncMock(return_value={
            "production_units": [SimpleNamespace(id=production_unit_id, area_ha=10.0)],
            "production_unit_ids": [production_unit_id],
            "safra_id": safra_id,
            "safra": None,
            "cultura": "SOJA",
            "unidade_produtiva_id": unidade_produtiva_id,
            "unidade_operacional_id": None,
            "unidade_operacional_resolvida": None,
        })),
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_receitas",
            new=AsyncMock(return_value=(DREAgricolaSection(valor=100.0), 0.0, [], 0)),
        ),
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_costs",
            new=AsyncMock(side_effect=lambda scope, *, direct, data_inicio=None, data_fim=None: DREAgricolaSection(valor=20.0 if direct else 10.0)),
        ),
        patch.object(
            DREAgricolaV1Service,
            "_consolidar_despesas",
            new=AsyncMock(return_value=(DREAgricolaSection(valor=5.0), 0)),
        ),
        patch.object(
            DREAgricolaV1Service,
            "_montar_reconciliacao",
            new=AsyncMock(return_value=DREReconcilacaoMeta()),
        ),
        patch.object(
            DREAgricolaV1Service,
            "_montar_warnings",
            new=AsyncMock(return_value=[]),
        ),
    ):
        svc = DREAgricolaV1Service(session, tenant_id)
        resposta_1 = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )
        clear_analytics_request_cache()
        resposta_2 = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert resposta_1.model_dump(exclude={"gerado_em"}) == resposta_2.model_dump(exclude={"gerado_em"})


def test_dre_kpis_request_cache_reutiliza_mesmo_payload():
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    dre = _fake_dre_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )

    kpis_1 = AgricolaDreKpiService.calcular(dre, area_total_ha=10.0, warnings=dre.warnings)
    kpis_2 = AgricolaDreKpiService.calcular(dre, area_total_ha=10.0, warnings=dre.warnings)
    kpis_3 = AgricolaDreKpiService.calcular(dre, area_total_ha=15.0, warnings=dre.warnings)

    assert kpis_1.model_dump() == kpis_2.model_dump()
    assert kpis_1.model_dump() != kpis_3.model_dump()
