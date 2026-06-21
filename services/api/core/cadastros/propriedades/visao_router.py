from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from core.dependencies import get_tenant_id, get_session
from core.cadastros.propriedade_imovel.visao_service import VisaoTerritorialService
from core.cadastros.propriedade_imovel.visao_schemas import VisaoTerritorialRead


router = APIRouter(prefix="/propriedades", tags=["Territorial — Visão Consolidada"])


@router.get("/{propriedade_id}/visao-territorial", response_model=VisaoTerritorialRead)
async def visao_territorial(
    propriedade_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session=Depends(get_session),
):
    """Retorna visão consolidada read-only de Propriedade, áreas e vínculos."""
    service = VisaoTerritorialService(session, tenant_id)
    return await service.obter_visao_territorial(propriedade_id)

