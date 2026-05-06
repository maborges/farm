import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import get_current_user, get_tenant_id
from core.models.auth import Usuario
from ia.ux_telemetry_service import IAUXTelemetryService

router = APIRouter(prefix="/ia/ux", tags=["IA UX Telemetry"])

@router.post("/track")
async def track_ux_evento(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Registra um evento de telemetria de UX."""
    evento = payload.get("evento")
    modo = payload.get("modo", "ESSENCIAL")
    metadados = payload.get("metadados", {})
    sessao_id = payload.get("sessao_id")

    if not evento:
        raise HTTPException(status_code=400, detail="Evento é obrigatório.")

    await IAUXTelemetryService.track_evento(
        db=db,
        tenant_id=tenant_id,
        usuario_id=user.id,
        evento=evento,
        modo=modo,
        sessao_id=sessao_id,
        metadados=metadados
    )
    return {"status": "ok"}

@router.get("/metricas")
async def obter_metricas_ux(
    dias: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna métricas de eficiência de UX para o tenant logado."""
    return await IAUXTelemetryService.obter_metricas(
        db=db,
        tenant_id=tenant_id,
        dias=dias
    )

@router.get("/perfil")
async def obter_perfil_ia(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna o perfil comportamental do usuário em relação à IA."""
    return await IAUXTelemetryService.obter_perfil_usuario_ia(
        db=db,
        tenant_id=tenant_id,
        usuario_id=user.id
    )

@router.post("/thresholds/calibrar")
async def calibrar_thresholds_ia(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user)
):
    """Recalibra os thresholds de UX baseados no comportamento global (Step UX-06)."""
    # Em produção, validar se o usuário é ADMIN
    return await IAUXTelemetryService.ajustar_thresholds_ia(db)

@router.get("/explicacao")
async def obter_explicacao_perfil(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna explicação amigável do perfil de IA (Step UX-07)."""
    return await IAUXTelemetryService.obter_explicacao_perfil(
        db=db,
        tenant_id=tenant_id,
        usuario_id=user.id
    )

@router.get("/friccao")
async def detectar_friccao(
    sessao_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Detecta sinais de fricção e sugere nudges (Step UX-08)."""
    return await IAUXTelemetryService.detectar_friccao_usuario(
        db=db,
        tenant_id=tenant_id,
        usuario_id=user.id,
        sessao_id=sessao_id
    )
