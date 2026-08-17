from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from loguru import logger
from sqlalchemy import select

from core.config import settings
from core.dependencies import get_session, get_tenant_id, get_user_id, require_tenant_permission, require_module
from core.exceptions import EntityNotFoundError, BusinessRuleError, TenantViolationError

from balanca.models import DispositivoBalanca
from balanca.service import DispositivoService, OperadorService, PesagemService, SyncService
from balanca.schemas import (
    DeviceCreate,
    DeviceCreateResponse,
    DeviceActivateRequest,
    DeviceActivateResponse,
    DeviceReactivateRequest,
    DeviceRevokeRequest,
    DeviceResponse,
    OperadorCreate,
    OperadorResponse,
    OperadorAtivoResponse,
    OperadorLoginRequest,
    OperadorLoginResponse,
    SolicitarPesagemRequest,
    OrdemPesagemResponse,
    CancelarOrdemRequest,
    ReatribuirOrdemRequest,
    PesagemResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)

router = APIRouter(prefix="/balanca", tags=["Balança"])
sync_router = APIRouter(prefix="/sync", tags=["Sync Balança"])


def _to_naive_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def _get_device_from_token(device_id: uuid.UUID, request: Request, session: AsyncSession) -> DispositivoBalanca:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header ausente")
    token = auth.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de dispositivo inválido")

    if payload.get("type") != "device_balanca":
        raise HTTPException(status_code=401, detail="Token não é de dispositivo de balança")

    token_device_id = payload.get("device_id")
    if not token_device_id or uuid.UUID(token_device_id) != device_id:
        raise HTTPException(status_code=403, detail="device_id não confere com o token")

    device = await session.get(DispositivoBalanca, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    if device.status != "ATIVO":
        raise HTTPException(status_code=403, detail="Dispositivo não está ativo")
    if _to_naive_utc(device.expires_at) < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Token do dispositivo expirado")

    return device


# ---------------------------------------------------------------------------
# Devices — gerenciados por usuários com JWT normal
# ---------------------------------------------------------------------------


@router.post(
    "/devices",
    response_model=DeviceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:dispositivo:criar")),
    ],
)
async def criar_dispositivo(
    data: DeviceCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        device = await svc.criar(data)
        await session.commit()
        await session.refresh(device)
        return device
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/devices/activate", response_model=DeviceActivateResponse)
async def ativar_dispositivo(req: DeviceActivateRequest, session: AsyncSession = Depends(get_session)):
    # Sem tenant_id no header — a ativação identifica o tenant pelo código.
    # Busca o dispositivo primeiro para descobrir o tenant e então valida.
    result = await session.execute(
        select(DispositivoBalanca).where(DispositivoBalanca.activation_code == req.activation_code)
    )
    device_lookup = result.scalar_one_or_none()
    if not device_lookup:
        raise HTTPException(status_code=404, detail="Código de ativação inválido ou já utilizado.")

    svc = DispositivoService(session, device_lookup.tenant_id)
    try:
        device, token = await svc.ativar(req)
        await session.commit()
    except (EntityNotFoundError, BusinessRuleError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except TenantViolationError as exc:
        await session.rollback()
        raise HTTPException(status_code=403, detail=str(exc))

    return DeviceActivateResponse(
        device_token=token,
        device_id=device.id,
        tenant_id=device.tenant_id,
        nome=device.nome,
        fazenda_ids=list(device.fazenda_ids),
        expires_at=device.expires_at,
    )


@router.post(
    "/devices/revoke",
    response_model=DeviceResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:dispositivo:revogar")),
    ],
)
async def revogar_dispositivo(
    data: DeviceRevokeRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        device = await svc.revogar(data.device_id, user_id)
        await session.commit()
        await session.refresh(device)
        return device
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/devices/reactivate",
    response_model=DeviceCreateResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:dispositivo:criar")),
    ],
)
async def reativar_dispositivo(
    data: DeviceReactivateRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        device, activation_code = await svc.reativar(data)
        await session.commit()
        await session.refresh(device)
        return device
    except (EntityNotFoundError, BusinessRuleError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/devices",
    response_model=list[DeviceResponse],
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:dispositivo:listar")),
    ],
)
async def listar_dispositivos(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    return await svc.listar(skip, limit)


# ---------------------------------------------------------------------------
# Operadores — cadastro (admin, JWT de usuário) + login (estação, device token)
# ---------------------------------------------------------------------------


@router.post(
    "/operadores",
    response_model=OperadorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:operador:criar")),
    ],
)
async def criar_operador(
    data: OperadorCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = OperadorService(session, tenant_id)
    try:
        operador = await svc.criar(data)
        await session.commit()
        await session.refresh(operador)
        return operador
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/operadores",
    response_model=list[OperadorResponse],
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:operador:listar")),
    ],
)
async def listar_operadores(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = OperadorService(session, tenant_id)
    return await svc.listar(skip, limit)


@router.post(
    "/operadores/{operador_id}/revogar",
    response_model=OperadorResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:operador:revogar")),
    ],
)
async def revogar_operador(
    operador_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = OperadorService(session, tenant_id)
    try:
        operador = await svc.revogar(operador_id, user_id)
        await session.commit()
        await session.refresh(operador)
        return operador
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/operadores/ativos", response_model=list[OperadorAtivoResponse])
async def listar_operadores_ativos(
    request: Request,
    device_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Consumido pela estação (device token) para montar o seletor de operador."""
    device = await _get_device_from_token(device_id, request, session)
    svc = OperadorService(session, device.tenant_id)
    return await svc.listar_ativos()


@router.post("/operadores/login", response_model=OperadorLoginResponse)
async def login_operador(
    request: Request,
    device_id: uuid.UUID = Query(...),
    data: OperadorLoginRequest = ...,
    session: AsyncSession = Depends(get_session),
):
    """Login por PIN pessoal na estação — não gera token, o PWA guarda
    operador_id/nome_exibicao localmente até trocar de operador."""
    device = await _get_device_from_token(device_id, request, session)
    svc = OperadorService(session, device.tenant_id)
    try:
        operador = await svc.login(data)
        return OperadorLoginResponse(
            operador_id=operador.id, pessoa_id=operador.pessoa_id, nome_exibicao=operador.nome_exibicao
        )
    except (EntityNotFoundError, BusinessRuleError) as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ---------------------------------------------------------------------------
# Ordens de Pesagem — API interna consumida por módulos clientes + visão admin
# ---------------------------------------------------------------------------


@router.post(
    "/ordens",
    response_model=OrdemPesagemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:solicitar")),
    ],
)
async def solicitar_pesagem(
    data: SolicitarPesagemRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PesagemService(session, tenant_id)
    ordem = await svc.solicitar_pesagem(data)
    await session.commit()
    await session.refresh(ordem)
    return ordem


@router.get(
    "/ordens",
    response_model=list[OrdemPesagemResponse],
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:listar")),
    ],
)
async def listar_ordens(
    status_filtro: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PesagemService(session, tenant_id)
    return await svc.listar_ordens(status_filtro, skip, limit)


@router.get(
    "/ordens/pendentes-reconciliacao",
    response_model=list[OrdemPesagemResponse],
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:listar")),
    ],
)
async def listar_pendentes_reconciliacao(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Pesagens avulsas (criadas sem ordem prévia) ainda não associadas a um processo."""
    svc = PesagemService(session, tenant_id)
    return await svc.listar_pendentes_reconciliacao(skip, limit)


@router.get(
    "/ordens/{ordem_id}",
    response_model=OrdemPesagemResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:listar")),
    ],
)
async def obter_ordem(
    ordem_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PesagemService(session, tenant_id)
    try:
        return await svc.obter_ordem(ordem_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/ordens/{ordem_id}/pesagens",
    response_model=list[PesagemResponse],
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:listar")),
    ],
)
async def listar_pesagens_da_ordem(
    ordem_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PesagemService(session, tenant_id)
    return await svc.listar_pesagens_por_ordem(ordem_id)


@router.post(
    "/ordens/{ordem_id}/cancelar",
    response_model=OrdemPesagemResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:cancelar")),
    ],
)
async def cancelar_ordem(
    ordem_id: uuid.UUID,
    data: CancelarOrdemRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PesagemService(session, tenant_id)
    try:
        ordem = await svc.cancelar_ordem(ordem_id, data.motivo)
        await session.commit()
        await session.refresh(ordem)
        return ordem
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.post(
    "/ordens/{ordem_id}/reatribuir",
    response_model=OrdemPesagemResponse,
    dependencies=[
        Depends(require_module("O4_BALANCA")),
        Depends(require_tenant_permission("balanca:pesagem:reatribuir")),
    ],
)
async def reatribuir_ordem(
    ordem_id: uuid.UUID,
    data: ReatribuirOrdemRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Reconciliação: associa uma pesagem avulsa ao processo real (colheita/compra/venda/pecuária)."""
    svc = PesagemService(session, tenant_id)
    try:
        ordem = await svc.reatribuir_ordem(ordem_id, data)
        await session.commit()
        await session.refresh(ordem)
        return ordem
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Sync — consumido pelo PWA da estação (device token, sem JWT de usuário)
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
    try:
        results = await svc.push(body.items)
        disp_svc = DispositivoService(session, device.tenant_id)
        await disp_svc.atualizar_last_sync(device.id)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error(f"[balanca/sync/push] {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return SyncPushResponse(processed_at=datetime.utcnow(), results=results)
