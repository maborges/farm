from __future__ import annotations
import uuid
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from loguru import logger
from sqlalchemy import select, and_

from core.config import settings
from core.database import get_session
from core.dependencies import get_tenant_id, get_user_id
from core.exceptions import EntityNotFoundError, BusinessRuleError, TenantViolationError

from campo.models import DispositivoCampo
from campo.service import DispositivoService, SyncService, TarefaProgramadaService
from campo.schemas import (
    DeviceCreate,
    DeviceCreateResponse,
    DeviceActivateRequest,
    DeviceActivateResponse,
    DeviceRevokeRequest,
    DeviceResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    TarefaProgramadaCreate,
    TarefaProgramadaResponse,
    ExecucaoUpdate,
)

router = APIRouter(prefix="/campo", tags=["Campo PWA"])
sync_router = APIRouter(prefix="/sync", tags=["Sync Campo"])


# ---------------------------------------------------------------------------
# Helper: valida device_token JWT e retorna DispositivoCampo
# ---------------------------------------------------------------------------

async def _get_device_from_token(
    device_id: uuid.UUID,
    request: Request,
    session: AsyncSession,
) -> DispositivoCampo:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header ausente")
    token = auth.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de dispositivo inválido")

    if payload.get("type") != "device":
        raise HTTPException(status_code=401, detail="Token não é de dispositivo de campo")

    token_device_id = payload.get("device_id")
    if not token_device_id or uuid.UUID(token_device_id) != device_id:
        raise HTTPException(status_code=403, detail="device_id não confere com o token")

    result = await session.execute(
        select(DispositivoCampo).where(DispositivoCampo.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    if device.status != "ATIVO":
        raise HTTPException(status_code=403, detail="Dispositivo não está ativo")
    if device.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Token do dispositivo expirado")

    return device


# ---------------------------------------------------------------------------
# Devices — gerenciados por usuários com JWT normal
# ---------------------------------------------------------------------------

@router.post("/devices", response_model=DeviceCreateResponse, status_code=status.HTTP_201_CREATED)
async def criar_dispositivo(
    data: DeviceCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        device = await svc.criar(data)
        await session.commit()
        await session.refresh(device)
        return device
    except Exception as exc:
        await session.rollback()
        logger.error(f"[campo/devices] {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/devices/activate", response_model=DeviceActivateResponse)
async def ativar_dispositivo(
    req: DeviceActivateRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DispositivoCampo).where(
            and_(
                DispositivoCampo.activation_code == req.activation_code,
                DispositivoCampo.status == "PENDENTE",
            )
        )
    )
    device_row = result.scalar_one_or_none()
    if not device_row:
        raise HTTPException(status_code=404, detail="Código de ativação inválido ou já utilizado.")

    svc = DispositivoService(session, device_row.tenant_id)
    try:
        device, token = await svc.ativar(req)
        await session.commit()
        await session.refresh(device)

        from core.models.auth import Usuario
        user_result = await session.execute(select(Usuario).where(Usuario.id == device.user_id))
        user = user_result.scalar_one_or_none()

        return DeviceActivateResponse(
            device_token=token,
            device_id=device.id,
            tenant_id=device.tenant_id,
            user_id=device.user_id,
            user_name=user.nome if user else "Operador",
            fazenda_ids=device.fazenda_ids,
            modulos=device.modulos,
            expires_at=device.expires_at,
        )
    except (EntityNotFoundError, BusinessRuleError) as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except TenantViolationError as exc:
        await session.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/devices/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revogar_dispositivo(
    req: DeviceRevokeRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        await svc.revogar(req.device_id, user_id or uuid.uuid4())
        await session.commit()
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/devices", response_model=list[DeviceResponse])
async def listar_dispositivos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    return await svc.listar()


# ---------------------------------------------------------------------------
# Tarefas Programadas — gerenciadas pelo backoffice (apps/web)
# ---------------------------------------------------------------------------

@router.post("/tarefas", response_model=TarefaProgramadaResponse, status_code=status.HTTP_201_CREATED)
async def criar_tarefa_programada(
    data: TarefaProgramadaCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = TarefaProgramadaService(session, tenant_id, user_id or uuid.uuid4())
    try:
        tarefa = await svc.criar(data)
        await session.commit()
        await session.refresh(tarefa)
        return tarefa
    except Exception as exc:
        await session.rollback()
        logger.error(f"[campo/tarefas] {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tarefas", response_model=list[TarefaProgramadaResponse])
async def listar_tarefas_programadas(
    fazenda_id: uuid.UUID | None = Query(default=None),
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    status_execucao: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    user_id = uuid.uuid4()
    svc = TarefaProgramadaService(session, tenant_id, user_id)
    return await svc.listar(
        fazenda_id=fazenda_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status_execucao=status_execucao,
        skip=skip,
        limit=limit,
    )


@router.get("/tarefas/{tarefa_id}", response_model=TarefaProgramadaResponse)
async def get_tarefa(
    tarefa_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from core.exceptions import EntityNotFoundError
    svc = TarefaProgramadaService(session, tenant_id, uuid.uuid4())
    try:
        return await svc.get_or_fail(tarefa_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/tarefas/{tarefa_id}/execucao", response_model=TarefaProgramadaResponse)
async def atualizar_execucao(
    tarefa_id: uuid.UUID,
    data: ExecucaoUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    from core.exceptions import EntityNotFoundError, BusinessRuleError
    svc = TarefaProgramadaService(session, tenant_id, user_id or uuid.uuid4())
    try:
        tarefa = await svc.atualizar_execucao(tarefa_id, data)
        await session.commit()
        await session.refresh(tarefa)
        return tarefa
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/tarefas/{tarefa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_tarefa(
    tarefa_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from core.exceptions import EntityNotFoundError
    svc = TarefaProgramadaService(session, tenant_id, uuid.uuid4())
    try:
        await svc.cancelar(tarefa_id)
        await session.commit()
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Sync — autenticados com device_token
# ---------------------------------------------------------------------------

@sync_router.get("/pull", response_model=SyncPullResponse)
async def sync_pull(
    request: Request,
    device_id: uuid.UUID = Query(...),
    last_sync_at: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    device = await _get_device_from_token(device_id, request, session)
    svc = SyncService(session, device.tenant_id, device)
    data = await svc.pull(last_sync_at)

    disp_svc = DispositivoService(session, device.tenant_id)
    await disp_svc.atualizar_last_sync(device.id)
    await session.commit()

    return data


@sync_router.post("/push", response_model=SyncPushResponse)
async def sync_push(
    request: Request,
    body: SyncPushRequest,
    session: AsyncSession = Depends(get_session),
):
    device = await _get_device_from_token(body.device_id, request, session)
    svc = SyncService(session, device.tenant_id, device)
    results = await svc.push(body.items)

    disp_svc = DispositivoService(session, device.tenant_id)
    await disp_svc.atualizar_last_sync(device.id)
    await session.commit()

    return SyncPushResponse(processed_at=datetime.utcnow(), results=results)
