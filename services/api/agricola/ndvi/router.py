from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_tenant_id, require_module, require_role
from core.dependencies import get_session
from agricola.ndvi.schemas import NDVICreate, NDVIResponse
from agricola.ndvi.service import NDVIService

router = APIRouter(prefix="/ndvi", tags=["NDVI (Sentinel-2)"])

@router.post("/sincronizar/{talhao_id}", status_code=status.HTTP_202_ACCEPTED)
async def sincronizar_talhao_api_satelite(
    talhao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """Aciona um job (Celery simulado) para buscar novas imagens do Sentinel-2 para o polígono deste talhão."""
    svc = NDVIService(session, tenant_id)
    msg = await svc.sync_sentinel2_data(talhao_id)
    return {"message": msg}

@router.post("/registro-manual", response_model=NDVIResponse, status_code=status.HTTP_201_CREATED)
async def registrar_ndvi_manual(
    data: NDVICreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    """OPERATIONS-GAP-01 §21.32: registro manual de índice NDVI calculado
    externamente (QGIS, provedor terceiro, planilha) — a sincronização
    automática via Sentinel-2/Copernicus (`sync_sentinel2_data`) continua mock,
    pendente de decisão de produto sobre custo/quota de API e infraestrutura
    de processamento de imagem (rasterio + storage de GeoTIFF). Esta via
    alimenta o mesmo `ImagemNDVI`/`get_serie_temporal` já consumido pelo
    frontend real (`ndvi-talhao.tsx`), sem depender dessa decisão."""
    svc = NDVIService(session, tenant_id)
    imagem = await svc.create(data)
    await session.commit()
    return NDVIResponse.model_validate(imagem)


@router.get("/serie-temporal/{talhao_id}")
async def obter_serie_temporal_ndvi(
    talhao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    svc = NDVIService(session, tenant_id)
    return await svc.get_serie_temporal(talhao_id)

@router.get("/", response_model=List[NDVIResponse])
async def listar_imagens_ndvi(
    talhao_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A4_PRECISAO")),
):
    svc = NDVIService(session, tenant_id)
    filters = {}
    if talhao_id: filters["talhao_id"] = talhao_id
    imagens = await svc.list_all(**filters)
    return [NDVIResponse.model_validate(img) for img in imagens]
