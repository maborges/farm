from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from agricola.ndvi.router import sincronizar_talhao_api_satelite
from agricola.ndvi.schemas import NDVICreate
from agricola.ndvi.service import NDVIService
from core.exceptions import EntityNotFoundError


def _make_exec_result(*, scalar_one_or_none=None, scalars_all=None, all_rows=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    scalars = MagicMock()
    scalars.all.return_value = scalars_all or []
    result.scalars.return_value = scalars
    result.all.return_value = all_rows or []
    return result


def test_ndvi_create_valida_faixas_indice_e_nuvens():
    talhao_id = uuid.uuid4()

    with pytest.raises(ValidationError):
        NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 11, 1), indice_medio=1.25)

    with pytest.raises(ValidationError):
        NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 11, 1), indice_medio=-1.1)

    with pytest.raises(ValidationError):
        NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 11, 1), cobertura_nuvens_pct=120.0)

    with pytest.raises(ValidationError):
        NDVICreate(talhao_id=talhao_id, data_captura=date(2026, 11, 1), cobertura_nuvens_pct=-5.0)

    with pytest.raises(ValidationError):
        NDVICreate(
            talhao_id=talhao_id,
            data_captura=date(2026, 11, 1),
            indice_minimo=0.8,
            indice_maximo=0.5,
        )

    with pytest.raises(ValidationError):
        NDVICreate(
            talhao_id=talhao_id,
            data_captura=date(2026, 11, 1),
            indice_minimo=0.4,
            indice_medio=0.9,
            indice_maximo=0.8,
        )

    valido = NDVICreate(
        talhao_id=talhao_id,
        data_captura=date(2026, 11, 1),
        indice_minimo=0.4,
        indice_medio=0.65,
        indice_maximo=0.85,
        cobertura_nuvens_pct=12.5,
        satelite="QGIS",
    )
    assert valido.indice_medio == 0.65


@pytest.mark.asyncio
async def test_registrar_manual_rejeita_talhao_inexistente_ou_outro_tenant():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_exec_result(scalar_one_or_none=None))

    svc = NDVIService(session, tenant_id)
    payload = NDVICreate(
        talhao_id=uuid.uuid4(),
        data_captura=date(2026, 11, 1),
        indice_medio=0.72,
    )

    with pytest.raises(EntityNotFoundError):
        await svc.registrar_manual(payload)


@pytest.mark.asyncio
async def test_registrar_manual_cria_imagem_quando_talhao_valido():
    tenant_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_exec_result(scalar_one_or_none=talhao_id))

    svc = NDVIService(session, tenant_id)
    payload = NDVICreate(
        talhao_id=talhao_id,
        data_captura=date(2026, 11, 1),
        indice_medio=0.74,
        satelite="Manual",
    )
    criado = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id, talhao_id=talhao_id)

    with patch.object(svc, "create", new=AsyncMock(return_value=criado)) as mock_create:
        resultado = await svc.registrar_manual(payload)

    assert resultado.id == criado.id
    mock_create.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_obter_resumo_propriedade_vazia_ou_sem_imagens():
    tenant_id = uuid.uuid4()
    up_id = uuid.uuid4()
    session_sem_areas = AsyncMock()
    session_sem_areas.execute = AsyncMock(return_value=_make_exec_result(all_rows=[]))

    resumo_vazio = await NDVIService(session_sem_areas, tenant_id).obter_resumo_propriedade(
        unidade_produtiva_id=up_id
    )
    assert resumo_vazio.total_areas_produtivas == 0
    assert resumo_vazio.areas_monitoradas == 0
    assert resumo_vazio.media_ndvi_propriedade is None
    assert resumo_vazio.variacao_media_pct is None
    assert resumo_vazio.classificacao_geral == "Sem dados"
    assert resumo_vazio.alertas == []
    assert resumo_vazio.sincronizacao_automatica_disponivel is False

    area = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Talhão Norte",
        tipo="TALHAO",
        area_hectares=Decimal("120.5"),
        area_hectares_manual=None,
        unidade_produtiva_id=up_id,
    )
    session_sem_imgs = AsyncMock()
    session_sem_imgs.execute = AsyncMock(
        side_effect=[
            _make_exec_result(all_rows=[area]),
            _make_exec_result(scalars_all=[]),
        ]
    )
    resumo_sem_imgs = await NDVIService(session_sem_imgs, tenant_id).obter_resumo_propriedade(
        unidade_produtiva_id=up_id
    )
    assert resumo_sem_imgs.total_areas_produtivas == 1
    assert resumo_sem_imgs.areas_monitoradas == 0
    assert resumo_sem_imgs.media_ndvi_propriedade is None
    assert resumo_sem_imgs.classificacao_geral == "Sem dados"
    assert resumo_sem_imgs.talhoes[0].classificacao == "Sem dados"


@pytest.mark.asyncio
async def test_obter_resumo_propriedade_calcula_medias_tendencia_e_alertas_reais():
    tenant_id = uuid.uuid4()
    up_id = uuid.uuid4()
    t1_id = uuid.uuid4()
    t2_id = uuid.uuid4()
    t3_id = uuid.uuid4()

    areas = [
        SimpleNamespace(
            id=t1_id,
            nome="Talhão 01",
            tipo="TALHAO",
            area_hectares=Decimal("80.0"),
            area_hectares_manual=None,
            unidade_produtiva_id=up_id,
        ),
        SimpleNamespace(
            id=t2_id,
            nome="Talhão 02",
            tipo="TALHAO",
            area_hectares=None,
            area_hectares_manual=Decimal("55.0"),
            unidade_produtiva_id=up_id,
        ),
        SimpleNamespace(
            id=t3_id,
            nome="Piquete 03",
            tipo="PIQUETE",
            area_hectares=Decimal("30.0"),
            area_hectares_manual=None,
            unidade_produtiva_id=up_id,
        ),
    ]

    hoje = date.today()
    imagens = [
        # T1: subiu de 0.70 para 0.77 (+10.0%) -> Excelente / SUBINDO
        SimpleNamespace(
            id=uuid.uuid4(),
            talhao_id=t1_id,
            data_captura=hoje - timedelta(days=10),
            indice_medio=Decimal("0.700"),
            cobertura_nuvens_pct=Decimal("5.0"),
            satelite="QGIS",
            created_at=datetime.now(),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            talhao_id=t1_id,
            data_captura=hoje - timedelta(days=2),
            indice_medio=Decimal("0.770"),
            cobertura_nuvens_pct=Decimal("4.0"),
            satelite="QGIS",
            created_at=datetime.now(),
        ),
        # T2: caiu de 0.50 para 0.35 (-30.0%), nuvem 45% -> Atenção / CAINDO + ESTRESSE ATENCAO + QUEDA CRITICO + NUVEM_ALTA
        SimpleNamespace(
            id=uuid.uuid4(),
            talhao_id=t2_id,
            data_captura=hoje - timedelta(days=15),
            indice_medio=Decimal("0.500"),
            cobertura_nuvens_pct=Decimal("10.0"),
            satelite="Drone",
            created_at=datetime.now(),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            talhao_id=t2_id,
            data_captura=hoje - timedelta(days=1),
            indice_medio=Decimal("0.350"),
            cobertura_nuvens_pct=Decimal("45.0"),
            satelite="Drone",
            created_at=datetime.now(),
        ),
        # T3: solo exposto / estresse severo (0.15) -> Crítico + ESTRESSE CRITICO
        SimpleNamespace(
            id=uuid.uuid4(),
            talhao_id=t3_id,
            data_captura=hoje - timedelta(days=3),
            indice_medio=Decimal("0.150"),
            cobertura_nuvens_pct=Decimal("8.0"),
            satelite="Manual",
            created_at=datetime.now(),
        ),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_exec_result(all_rows=areas),
            _make_exec_result(scalars_all=imagens),
        ]
    )

    resumo = await NDVIService(session, tenant_id).obter_resumo_propriedade(
        unidade_produtiva_id=up_id,
        periodo_dias=30,
    )

    assert resumo.periodo_dias == 30
    assert resumo.total_areas_produtivas == 3
    assert resumo.areas_monitoradas == 3
    assert resumo.total_registros == 5
    # Média de (0.77 + 0.35 + 0.15) / 3 = 0.423
    assert resumo.media_ndvi_propriedade == pytest.approx(0.423, abs=0.001)
    assert resumo.classificacao_geral == "Moderado"
    # Variação média de (+10.0 e -30.0) = -10.0
    assert resumo.variacao_media_pct == pytest.approx(-10.0, abs=0.1)

    por_id = {t.talhao_id: t for t in resumo.talhoes}
    assert por_id[t1_id].tendencia == "SUBINDO"
    assert por_id[t1_id].classificacao == "Excelente"
    assert por_id[t2_id].tendencia == "CAINDO"
    assert por_id[t2_id].variacao_pct == pytest.approx(-30.0, abs=0.1)
    assert por_id[t2_id].area_hectares == 55.0
    assert por_id[t3_id].classificacao == "Crítico"

    tipos_alertas = {(a.talhao_id, a.tipo, a.severidade) for a in resumo.alertas}
    assert (t3_id, "ESTRESSE_HIDRICO", "CRITICO") in tipos_alertas
    assert (t2_id, "QUEDA_VIGOR", "CRITICO") in tipos_alertas
    assert (t2_id, "ESTRESSE_HIDRICO", "ATENCAO") in tipos_alertas
    assert (t2_id, "NUVEM_ALTA", "ATENCAO") in tipos_alertas
    # Críticos ordenados antes dos de atenção
    severidades = [a.severidade for a in resumo.alertas]
    assert severidades.index("ATENCAO") > severidades.index("CRITICO")

    # Confirma que periodo_dias aplicou filtro de data_captura na segunda query
    segunda_stmt = session.execute.call_args_list[1].args[0]
    sql_text = str(segunda_stmt)
    assert "data_captura >=" in sql_text


@pytest.mark.asyncio
async def test_excluir_registro_usa_hard_delete_e_propaga_not_found():
    tenant_id = uuid.uuid4()
    img_id = uuid.uuid4()
    session = AsyncMock()
    svc = NDVIService(session, tenant_id)

    with patch.object(svc, "hard_delete", new=AsyncMock(return_value=None)) as mock_del:
        await svc.excluir_registro(img_id)
    mock_del.assert_awaited_once_with(img_id)

    with patch.object(svc, "hard_delete", new=AsyncMock(side_effect=EntityNotFoundError("nao existe"))):
        with pytest.raises(EntityNotFoundError):
            await svc.excluir_registro(img_id)


@pytest.mark.asyncio
async def test_sincronizar_sentinel2_retorna_http_501_honesto():
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await sincronizar_talhao_api_satelite(
            talhao_id=uuid.uuid4(),
            session=session,
            tenant_id=tenant_id,
            _=None,
        )

    assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert "Sentinel-2" in exc_info.value.detail
    assert "manual" in exc_info.value.detail.lower()
