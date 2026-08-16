from __future__ import annotations

import uuid
from datetime import date

import pytest

from agricola.ndvi.models import ImagemNDVI
from agricola.ndvi.schemas import NDVICreate
from agricola.ndvi.service import NDVIService
from test_operational_workflow_governance_step03 import _criar_area, _criar_unidade_produtiva, _garantir_tenant


@pytest.mark.asyncio
async def test_registro_manual_persiste_indice_e_aparece_na_serie_temporal(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_id = await _criar_area(session, tenant_id, unidade_id)

    svc = NDVIService(session, tenant_id)
    imagem = await svc.create(NDVICreate(
        talhao_id=talhao_id,
        data_captura=date(2026, 8, 1),
        indice_medio=0.72,
        indice_minimo=0.55,
        indice_maximo=0.85,
        satelite="Manual (QGIS)",
    ))
    await session.commit()

    assert imagem.id is not None
    assert imagem.tenant_id == tenant_id
    assert float(imagem.indice_medio) == 0.72

    serie = await svc.get_serie_temporal(talhao_id)
    assert serie["total_imagens"] == 1
    assert serie["indice_atual"] == 0.72
    assert serie["tendencia"] is None
    assert len(serie["dados"]) == 1
    assert serie["dados"][0]["data"] == "2026-08-01"
    assert serie["dados"][0]["indice_medio"] == 0.72


@pytest.mark.asyncio
async def test_serie_temporal_calcula_tendencia_subindo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_id = await _criar_area(session, tenant_id, unidade_id)

    svc = NDVIService(session, tenant_id)
    await svc.create(NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 7, 1), indice_medio=0.40))
    await svc.create(NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 8, 1), indice_medio=0.60))
    await session.commit()

    serie = await svc.get_serie_temporal(talhao_id)
    assert serie["total_imagens"] == 2
    assert serie["indice_atual"] == 0.60
    assert serie["tendencia"] == "SUBINDO"


@pytest.mark.asyncio
async def test_isolamento_tenant_ndvi_manual(session_a, session_b, tenant_id, outro_tenant_id):
    await _garantir_tenant(session_a, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session_a, tenant_id)
    talhao_id = await _criar_area(session_a, tenant_id, unidade_id)

    svc_a = NDVIService(session_a, tenant_id)
    imagem = await svc_a.create(NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 8, 1), indice_medio=0.6))
    await session_a.commit()

    from sqlalchemy import select
    stmt = select(ImagemNDVI).where(ImagemNDVI.tenant_id == outro_tenant_id, ImagemNDVI.id == imagem.id)
    assert (await session_b.execute(stmt)).scalars().first() is None
