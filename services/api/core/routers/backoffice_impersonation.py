"""
Router para sessões de suporte e auditoria de impersonação de tenants.

Permite que administradores e equipe de suporte acessem temporariamente
o ambiente de um assinante (tenant) de forma controlada, segura e auditada.
"""
from typing import Optional
from uuid import UUID
import uuid as uuid_module
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.dependencies import get_current_user_claims, get_session, require_permission
from core.models.admin_user import AdminUser
from core.services.impersonation_service import ImpersonationService

router = APIRouter(prefix="/backoffice/impersonate", tags=["Backoffice - Acesso Assistido (Impersonação)"])


# ============================================================================
# SCHEMAS
# ============================================================================

class StartImpersonationRequest(BaseModel):
    """Requisição para iniciar acesso assistido a um tenant."""
    tenant_id: UUID
    modo: str = Field(default="READ_ONLY", pattern="^(READ_ONLY|READ_WRITE)$")
    motivo: str = Field(..., min_length=5, max_length=500, description="Justificativa do acesso para auditoria")
    categoria: Optional[str] = Field(default="SUPORTE_TECNICO", max_length=100)
    unidade_produtiva_id: Optional[UUID] = None


class SwitchModeRequest(BaseModel):
    """Requisição para alternar entre modo Somente Leitura e Leitura/Escrita."""
    modo: str = Field(..., pattern="^(READ_ONLY|READ_WRITE)$")
    motivo: str = Field(..., min_length=5, max_length=500, description="Motivo da alteração de modo")


class StopImpersonationRequest(BaseModel):
    """Requisição opcional para encerramento de acesso assistido."""
    impersonation_id: Optional[UUID] = None
    acoes_resumo: Optional[str] = Field(None, max_length=1000)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/start", status_code=status.HTTP_200_OK)
async def start_impersonation(
    payload: StartImpersonationRequest,
    request: Request,
    claims: dict = Depends(require_permission("backoffice:impersonate")),
    session: AsyncSession = Depends(get_session),
):
    """
    Inicia uma sessão assistida de impersonação para um tenant específico.

    Exige permissão 'backoffice:impersonate' (super_admin, admin ou suporte).
    Gera um JWT com escopo de tenant, contexto RLS e registro em auditoria.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = ImpersonationService(session)
    return await service.start_impersonation(
        admin_claims=claims,
        tenant_id=payload.tenant_id,
        modo=payload.modo,
        motivo=payload.motivo,
        categoria=payload.categoria or "SUPORTE",
        unidade_produtiva_id=payload.unidade_produtiva_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.patch("/mode", status_code=status.HTTP_200_OK)
async def switch_mode(
    payload: SwitchModeRequest,
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """
    Alterna o modo da sessão atual (READ_ONLY <-> READ_WRITE).

    Pode ser invocado durante a sessão de impersonação.
    """
    if not claims.get("impersonating"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operação válida apenas dentro de uma sessão ativa de impersonação."
        )

    impersonation_id_str = claims.get("impersonation_id")
    if not impersonation_id_str:
        raise HTTPException(status_code=400, detail="Token de impersonação sem identificador.")

    try:
        impersonation_id = uuid_module.UUID(impersonation_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identificador malformado no token.")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = ImpersonationService(session)
    return await service.switch_mode(
        claims=claims,
        impersonation_id=impersonation_id,
        novo_modo=payload.modo,
        motivo=payload.motivo,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/stop", status_code=status.HTTP_200_OK)
async def stop_impersonation(
    request: Request,
    payload: Optional[StopImpersonationRequest] = None,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """
    Encerra a sessão de impersonação ativa e finaliza o log de auditoria.
    """
    impersonation_id_str = None
    if payload and payload.impersonation_id:
        impersonation_id_str = str(payload.impersonation_id)
    elif claims.get("impersonation_id"):
        impersonation_id_str = claims.get("impersonation_id")

    if not impersonation_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="impersonation_id não fornecido no corpo ou no token."
        )

    try:
        impersonation_id = uuid_module.UUID(impersonation_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="impersonation_id inválido.")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = ImpersonationService(session)
    return await service.stop_impersonation(
        claims=claims,
        impersonation_id=impersonation_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
