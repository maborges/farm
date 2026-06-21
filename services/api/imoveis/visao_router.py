from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from core.dependencies import get_tenant_id, get_session
from core.cadastros.propriedade_imovel.visao_service import VisaoTerritorialService
from core.cadastros.propriedade_imovel.visao_schemas import VisaoFundiariaRead


router = APIRouter(prefix="/imoveis-rurais", tags=["Fundiário — Visão Consolidada"])


@router.get("/{imovel_id}/visao-fundiaria", response_model=VisaoFundiariaRead)
async def visao_fundiaria(
    imovel_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session=Depends(get_session),
):
    """Retorna visão consolidada read-only de Imóvel Rural, documentos e vínculos."""
    service = VisaoTerritorialService(session, tenant_id)
    return await service.obter_visao_fundiaria(imovel_id)

