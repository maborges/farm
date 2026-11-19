from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.ndvi.schemas import NDVICreate, NDVIResponse, NDVIResumoPropriedadeResponse
from agricola.ndvi.service import NDVIService
from core.dependencies import get_session, get_tenant_id, require_module

router = APIRouter(prefix="/ndvi", tags=["NDVI (Sentinel-2)"])


@router.get("/resumo", response_model=NDVIResumoPropriedadeResponse)
async def obter_resumo_ndvi_propriedade(
    unidade_produtiva_id: UUID | None = None,
    periodo_dias: int | None = Query(default=None, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Consolida o monitoramento NDVI real das áreas produtivas da propriedade."""
    svc = NDVIService(session, tenant_id)
    return await svc.obter_resumo_propriedade(
        unidade_produtiva_id=unidade_produtiva_id,
        periodo_dias=periodo_dias,
    )


@router.post("/sincronizar/{talhao_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def sincronizar_talhao_api_satelite(
    talhao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Informa indisponibilidade honesta enquanto a integração Sentinel-2 não estiver ativa."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Sincronização automática via Sentinel-2 ainda não configurada. "
            "Utilize o registro manual de NDVI."
        ),
    )


@router.post("/registro-manual", response_model=NDVIResponse, status_code=status.HTTP_201_CREATED)
async def registrar_ndvi_manual(
    data: NDVICreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Registra manualmente um índice NDVI calculado externamente (QGIS, drone ou provedor)."""
    svc = NDVIService(session, tenant_id)
    imagem = await svc.registrar_manual(data)
    await session.commit()
    return NDVIResponse.model_validate(imagem)


@router.get("/serie-temporal/{talhao_id}")
async def obter_serie_temporal_ndvi(
    talhao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Retorna a série temporal de leituras NDVI para uma área produtiva."""
    svc = NDVIService(session, tenant_id)
    return await svc.get_serie_temporal(talhao_id)


@router.get("/", response_model=List[NDVIResponse])
async def listar_imagens_ndvi(
    talhao_id: UUID | None = None,
    periodo_dias: int | None = Query(default=None, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Lista os registros NDVI do tenant com filtros opcionais por área e período."""
    svc = NDVIService(session, tenant_id)
    imagens = await svc.listar_imagens(talhao_id=talhao_id, periodo_dias=periodo_dias)
    return [NDVIResponse.model_validate(img) for img in imagens]


@router.delete("/{imagem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_registro_ndvi(
    imagem_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Exclui um registro NDVI pertencente ao tenant autenticado."""
    svc = NDVIService(session, tenant_id)
    await svc.excluir_registro(imagem_id)
    await session.commit()
