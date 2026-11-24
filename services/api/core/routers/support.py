from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from core.constants import DEMO_EXTENSION_TICKET_CATEGORY
from core.dependencies import get_session, get_current_user, get_current_user_claims, get_current_tenant
from core.models.tenant import Tenant
from core.models.auth import Usuario
from core.models.support import ChamadoSuporte, MensagemChamado, TicketStatus
from core.schemas.support_schemas import (
    ChamadoSuporteCreate, ChamadoSuporteResponse, 
    ChamadoDetalheResponse, MensagemChamadoCreate, MensagemChamadoResponse
)
from core.services.demo_config_service import get_demo_saas_config

router = APIRouter(prefix="/support", tags=["Suporte / Tickets"])


def _is_isolated_demo_user(claims: dict) -> bool:
    """Indica se o usuário deve enxergar somente os próprios chamados no tenant."""
    return bool(claims.get("is_demo_visitor") or claims.get("is_read_only"))


@router.post("/tickets", response_model=ChamadoSuporteResponse)
async def create_ticket(
    data: ChamadoSuporteCreate,
    user: Usuario = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Abre um novo chamado de suporte."""
    if data.categoria == DEMO_EXTENSION_TICKET_CATEGORY:
        if _is_isolated_demo_user(claims):
            demo_cfg = await get_demo_saas_config(session)
            if not demo_cfg.permitir_solicitacao_prorrogacao:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solicitações automáticas de prorrogação estão temporariamente desabilitadas. Entre em contato com nossa equipe comercial.",
                )
        aberto_stmt = (
            select(ChamadoSuporte.id)
            .where(
                ChamadoSuporte.tenant_id == tenant.id,
                ChamadoSuporte.usuario_abertura_id == user.id,
                ChamadoSuporte.categoria == DEMO_EXTENSION_TICKET_CATEGORY,
                ChamadoSuporte.status.in_([
                    TicketStatus.ABERTO,
                    TicketStatus.EM_ATENDIMENTO,
                    TicketStatus.AGUARDANDO_CLIENTE,
                ]),
            )
            .limit(1)
        )
        if (await session.execute(aberto_stmt)).scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Você já possui uma solicitação de prorrogação em andamento. Acompanhe pelo chamado aberto.",
            )

    chamado = ChamadoSuporte(
        tenant_id=tenant.id,
        usuario_abertura_id=user.id,
        assunto=data.assunto,
        categoria=data.categoria,
        prioridade=data.prioridade,
        status=TicketStatus.ABERTO
    )
    session.add(chamado)
    await session.flush()
    
    # Criar a primeira mensagem
    msg = MensagemChamado(
        chamado_id=chamado.id,
        usuario_id=user.id,
        conteudo=data.mensagem_inicial,
        is_admin_reply=False
    )
    session.add(msg)
    
    await session.commit()
    return chamado

@router.get("/tickets", response_model=List[ChamadoSuporteResponse])
async def list_my_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: Usuario = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Lista chamados da empresa logada (escopo individual para visitantes de demonstração)."""
    stmt = select(ChamadoSuporte).where(ChamadoSuporte.tenant_id == tenant.id)
    if _is_isolated_demo_user(claims):
        stmt = stmt.where(ChamadoSuporte.usuario_abertura_id == user.id)
    stmt = stmt.order_by(ChamadoSuporte.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/tickets/{ticket_id}", response_model=ChamadoDetalheResponse)
async def get_ticket_details(
    ticket_id: uuid.UUID,
    user: Usuario = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna os detalhes e mensagens de um chamado."""
    stmt = select(ChamadoSuporte).where(
        ChamadoSuporte.id == ticket_id,
        ChamadoSuporte.tenant_id == tenant.id
    )
    if _is_isolated_demo_user(claims):
        stmt = stmt.where(ChamadoSuporte.usuario_abertura_id == user.id)
    result = await session.execute(stmt)
    chamado = result.scalar_one_or_none()
    
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")
    
    return chamado

@router.post("/tickets/{ticket_id}/messages", response_model=MensagemChamadoResponse)
async def reply_to_ticket(
    ticket_id: uuid.UUID,
    data: MensagemChamadoCreate,
    user: Usuario = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Usuário envia uma nova mensagem no chamado."""
    chamado = await session.get(ChamadoSuporte, ticket_id)
    if not chamado or chamado.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")
    if _is_isolated_demo_user(claims) and chamado.usuario_abertura_id != user.id:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")
    
    if chamado.status == TicketStatus.CONCLUIDO:
        raise HTTPException(status_code=400, detail="Este chamado já foi concluído.")

    msg = MensagemChamado(
        chamado_id=ticket_id,
        usuario_id=user.id,
        conteudo=data.conteudo,
        anexo_url=data.anexo_url,
        is_admin_reply=False
    )
    
    # Se o cliente respondeu, volta para status ABERTO ou EM_ATENDIMENTO se já estava sendo atendido
    if chamado.status == TicketStatus.AGUARDANDO_CLIENTE:
        chamado.status = TicketStatus.EM_ATENDIMENTO

    session.add(msg)
    await session.commit()
    return msg
