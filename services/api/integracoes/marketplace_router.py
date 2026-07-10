from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, require_tenant_permission
from integracoes.models import MarketplaceIntegracao

router = APIRouter(prefix="/marketplace", tags=["Integração Marketplace"])


@router.get(
    "/erps",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
    summary="Lista provedores de ERP disponíveis no catálogo",
)
async def listar_erps_disponiveis(
    ativa: bool = Query(True, description="Filtrar apenas provedores ativos"),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """
    Retorna o catálogo de ERPs disponíveis no Marketplace para seleção no Wizard
    ou em configurações da plataforma.
    """
    stmt = (
        select(
            MarketplaceIntegracao.id,
            MarketplaceIntegracao.nome,
            MarketplaceIntegracao.slug,
            MarketplaceIntegracao.descricao,
            MarketplaceIntegracao.logo_url,
        )
        .where(MarketplaceIntegracao.provider_type == "ERP")
    )
    
    if ativa:
        stmt = stmt.where(MarketplaceIntegracao.ativa.is_(True))
        
    stmt = stmt.order_by(MarketplaceIntegracao.nome.asc())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": row.id,
            "nome": row.nome,
            "slug": row.slug,
            "descricao": row.descricao,
            "logo_url": row.logo_url,
        }
        for row in rows
    ]
