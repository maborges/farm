from __future__ import annotations
import uuid
from datetime import datetime, date, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from loguru import logger
from sqlalchemy import select, and_

from core.config import settings
from core.dependencies import get_session, get_tenant_id, get_user_id, require_tenant_permission
from core.exceptions import EntityNotFoundError, BusinessRuleError, TenantViolationError
from alert_engine.models import Domain
from events import DomainEvent, publish_domain_event_safe

from campo.models import DispositivoCampo, TarefaCampo
from campo.service import CampoAgricolaSyncService, DispositivoService, SyncService, TarefaProgramadaService
from campo.schemas import (
    DeviceCreate,
    DeviceCreateResponse,
    DeviceActivateRequest,
    DeviceActivateResponse,
    DeviceReactivateRequest,
    DeviceRevokeRequest,
    DeviceResponse,
    DeviceSelfResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    TarefaProgramadaCreate,
    TarefaProgramadaUpdate,
    TarefaProgramadaResponse,
    TarefaProgramadaInvalidarRequest,
    ExecucaoUpdate,
)

router = APIRouter(prefix="/campo", tags=["Campo PWA"])
sync_router = APIRouter(prefix="/sync", tags=["Sync Campo"])

def _to_naive_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _uuid_from_string(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


async def _publish_campo_event(
    *,
    session: AsyncSession,
    event: DomainEvent,
    status: str,
) -> None:
    await publish_domain_event_safe(
        event,
        session=session,
        commit=False,
        logger_context={
            "component": "campo_router",
            "status": status,
        },
    )


def _build_tarefa_invalidada_event(tarefa, motivo: str) -> DomainEvent:
    return DomainEvent(
        tenant_id=tarefa.tenant_id,
        unidade_produtiva_id=tarefa.unidade_produtiva_id,
        domain=Domain.FIELD,
        event_type="campo.tarefa.invalidada",
        source_type="CAMPO_TAREFA_INVALIDADA",
        entity_type="tarefa_campo",
        entity_id=tarefa.id,
        correlation_id=_uuid_from_string(getattr(tarefa, "client_id", None)),
        metadata={
            "status_anterior": "CONCLUIDA",
            "status_novo": "INVALIDADA",
            "motivo": motivo,
            "tarefa_id": str(tarefa.id),
            "module": tarefa.module,
            "type": tarefa.type,
        },
    )


def _build_sync_failure_event(tarefa, error: Exception, *, status: str) -> DomainEvent:
    sync_meta = dict((tarefa.dados or {}).get("sync_pecuaria") or {})
    sync_meta.setdefault("status", status)
    sync_meta.setdefault("erros", [str(error)])
    return DomainEvent(
        tenant_id=tarefa.tenant_id,
        unidade_produtiva_id=tarefa.unidade_produtiva_id,
        domain=Domain.FIELD,
        event_type="campo.sync.falha",
        source_type="CAMPO_SYNC_FALHA",
        entity_type="sync_campo",
        entity_id=tarefa.id,
        correlation_id=_uuid_from_string(getattr(tarefa, "client_id", None)),
        metadata={
            "sync_status": sync_meta.get("status"),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "origin": "sync_push",
            "tarefa_id": str(tarefa.id),
            "module": tarefa.module,
            "type": tarefa.type,
        },
    )


def _marcar_resultado_sync_com_erro(
    results: list,
    tarefa_id: uuid.UUID,
    error: Exception,
) -> None:
    for result in results:
        server_id = result.get("server_id") if isinstance(result, dict) else result.server_id
        if server_id == str(tarefa_id):
            if isinstance(result, dict):
                result["status"] = "ERROR"
                result["error_message"] = str(error)
            else:
                result.status = "ERROR"
                result.error_message = str(error)
            return


def _materializacao_pecuaria_error(resultado) -> Exception | None:
    if getattr(resultado, "status", None) == "SUCCESS":
        return None
    erros = getattr(resultado, "erros", None) or []
    mensagem = erros[0] if erros else f"Materialização pecuária retornou status {getattr(resultado, 'status', 'UNKNOWN')}"
    return RuntimeError(mensagem)


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
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
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
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
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
            user_name=(user.apelido or user.nome_completo or user.username) if user else "Operador",
            user_avatar_url=user.foto_perfil_url if user else None,
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


@router.post(
    "/devices/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
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


@router.post(
    "/devices/reactivate",
    response_model=DeviceCreateResponse,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
async def reativar_dispositivo(
    req: DeviceReactivateRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    try:
        device, activation_code = await svc.reativar(req)
        await session.commit()
        await session.refresh(device)
        return DeviceCreateResponse(
            id=device.id,
            nome=device.nome,
            activation_code=activation_code,
            activation_code_expires_at=device.activation_code_expires_at,
            expires_at=device.expires_at,
            status=device.status,
        )
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/devices", response_model=list[DeviceResponse])
async def listar_dispositivos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = DispositivoService(session, tenant_id)
    return await svc.listar()


@router.get("/devices/me", response_model=DeviceSelfResponse)
async def get_device_self(
    request: Request,
    device_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
):
    device = await _get_device_from_token(device_id, request, session)

    from core.models.auth import Usuario

    user_result = await session.execute(select(Usuario).where(Usuario.id == device.user_id))
    user = user_result.scalar_one_or_none()

    disp_svc = DispositivoService(session, device.tenant_id)
    await disp_svc.atualizar_last_seen(device.id)
    await session.commit()

    return DeviceSelfResponse(
        id=device.id,
        nome=device.nome,
        status=device.status,
        user_id=device.user_id,
        user_name=(user.apelido or user.nome_completo or user.username) if user else "Operador",
        user_avatar_url=user.foto_perfil_url if user else None,
        fazenda_ids=device.fazenda_ids,
        modulos=device.modulos,
        expires_at=device.expires_at,
    )


# ---------------------------------------------------------------------------
# Tarefas Programadas — gerenciadas pelo backoffice (apps/web)
# ---------------------------------------------------------------------------

@router.post(
    "/tarefas",
    response_model=TarefaProgramadaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
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


@router.patch(
    "/tarefas/{tarefa_id}",
    response_model=TarefaProgramadaResponse,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
async def atualizar_tarefa_programada(
    tarefa_id: uuid.UUID,
    data: TarefaProgramadaUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from core.exceptions import EntityNotFoundError, BusinessRuleError
    svc = TarefaProgramadaService(session, tenant_id, uuid.uuid4())
    try:
        tarefa = await svc.atualizar(tarefa_id, data)
        await session.commit()
        await session.refresh(tarefa)
        return tarefa
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/tarefas", response_model=list[TarefaProgramadaResponse])
async def listar_tarefas_programadas(
    fazenda_id: uuid.UUID | None = Query(default=None),
    safra_id: uuid.UUID | None = Query(default=None),
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
        safra_id=safra_id,
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


@router.patch(
    "/tarefas/{tarefa_id}/execucao",
    response_model=TarefaProgramadaResponse,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
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


@router.delete(
    "/tarefas/{tarefa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
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


@router.post(
    "/tarefas/{tarefa_id}/invalidar",
    response_model=TarefaProgramadaResponse,
    dependencies=[Depends(require_tenant_permission("campo:*"))],
)
async def invalidar_tarefa(
    tarefa_id: uuid.UUID,
    body: TarefaProgramadaInvalidarRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    from core.exceptions import EntityNotFoundError, BusinessRuleError

    if not user_id:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    svc = TarefaProgramadaService(session, tenant_id, user_id, request.client.host if request.client else None)
    try:
        tarefa = await svc.invalidar(tarefa_id, body.motivo)
        await _publish_campo_event(
            session=session,
            event=_build_tarefa_invalidada_event(tarefa, body.motivo),
            status="published",
        )
        await session.commit()
        await session.refresh(tarefa)
        return tarefa
    except EntityNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# Requisições de material — autenticados com device_token + PIN pessoal
# ---------------------------------------------------------------------------

@router.get("/requisicoes", response_model=list[dict])
async def listar_requisicoes_campo(
    device_id: uuid.UUID,
    operacao_agricola_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Requisições (picking list) vinculadas à OS da tarefa — pode haver mais
    de uma (inicial + complementos)."""
    from operacional.services.estoque_service import EstoqueService

    device = await _get_device_from_token(device_id, request, session)
    svc = EstoqueService(session, device.tenant_id)
    requisicoes = await svc.listar_requisicoes_por_operacao(operacao_agricola_id)
    from operacional.schemas.estoque import RequisicaoResponse
    return [RequisicaoResponse.model_validate(r).model_dump(mode="json") for r in requisicoes]


@router.post("/requisicoes/{req_id}/confirmar-retirada", response_model=dict)
async def confirmar_retirada_campo(
    req_id: uuid.UUID,
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Confirma retirada de material a partir do app de campo — reautentica
    por PIN pessoal do operador do dispositivo (não é o mesmo PIN local do
    app; validado aqui contra o hash guardado no servidor na ativação)."""
    from operacional.services.estoque_service import EstoqueService
    from operacional.schemas.estoque import ItemConferidoUpdate, RequisicaoResponse

    device_id = uuid.UUID(body["device_id"])
    device = await _get_device_from_token(device_id, request, session)

    disp_svc = DispositivoService(session, device.tenant_id)
    try:
        await disp_svc.verificar_pin(device_id, body["pin"])
    except (EntityNotFoundError, BusinessRuleError) as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    itens = [ItemConferidoUpdate(**item) for item in body.get("itens", [])]
    est_svc = EstoqueService(session, device.tenant_id)
    try:
        requisicao = await est_svc.confirmar_retirada_requisicao_dispositivo(req_id, device.user_id, itens)
        await session.commit()
    except (EntityNotFoundError, BusinessRuleError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    return RequisicaoResponse.model_validate(requisicao).model_dump(mode="json")


@router.post("/requisicoes/{req_id}/confirmar-devolucao", response_model=dict)
async def confirmar_devolucao_campo(
    req_id: uuid.UUID,
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Confirma devolução de sobra de insumo a partir do app de campo — mesma
    reautenticação por PIN do dispositivo usada na retirada."""
    from operacional.services.estoque_service import EstoqueService
    from operacional.schemas.estoque import ItemDevolvidoUpdate, RequisicaoResponse

    device_id = uuid.UUID(body["device_id"])
    device = await _get_device_from_token(device_id, request, session)

    disp_svc = DispositivoService(session, device.tenant_id)
    try:
        await disp_svc.verificar_pin(device_id, body["pin"])
    except (EntityNotFoundError, BusinessRuleError) as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    itens = [ItemDevolvidoUpdate(**item) for item in body.get("itens", [])]
    est_svc = EstoqueService(session, device.tenant_id)
    try:
        requisicao = await est_svc.confirmar_devolucao_requisicao_dispositivo(req_id, device.user_id, itens)
        await session.commit()
    except (EntityNotFoundError, BusinessRuleError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    return RequisicaoResponse.model_validate(requisicao).model_dump(mode="json")


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

    # Materialização pós-commit segura: a tarefa já foi persistida e o retorno do
    # sync continua refletindo falhas de efeitos colaterais para permitir retry.
    tarefas_agricola_sync = getattr(svc, "tarefas_agricola_sync", [])
    if tarefas_agricola_sync:
        for tarefa_id in tarefas_agricola_sync:
            try:
                await CampoAgricolaSyncService(session, device.tenant_id).processar_tarefa_campo(tarefa_id)
            except Exception as e:
                logger.error(f"[sync/push] Erro ao materializar evento agricola para tarefa {tarefa_id}: {e}")
                await session.rollback()
                _marcar_resultado_sync_com_erro(results, tarefa_id, e)

    tarefas_pecuaria_sync = getattr(svc, "tarefas_pecuaria_sync", [])
    if tarefas_pecuaria_sync:
        from pecuaria.services.manejo_sync_service import ManejoSyncService
        for tarefa_id in tarefas_pecuaria_sync:
            try:
                msvc = ManejoSyncService(session, device.tenant_id)
                resultado = await msvc.processar_tarefa_campo(tarefa_id)
                erro_materializacao = _materializacao_pecuaria_error(resultado)
                if erro_materializacao is not None:
                    _marcar_resultado_sync_com_erro(results, tarefa_id, erro_materializacao)
                await session.commit()
            except Exception as e:
                # O erro não falha a sincronização, apenas gera log
                logger.error(f"[sync/push] Erro ao materializar evento pecuario para tarefa {tarefa_id}: {e}")
                await session.rollback()
                _marcar_resultado_sync_com_erro(results, tarefa_id, e)

                # Falha catastrófica
                try:
                    tarefa = await session.get(TarefaCampo, tarefa_id)
                    if tarefa:
                        dados = dict(tarefa.dados or {})
                        dados["sync_pecuaria"] = {
                            "status": "ERROR",
                            "total_processado": 0,
                            "erros": [f"Erro interno: {str(e)}"],
                            "data_processamento": datetime.utcnow().isoformat()
                        }
                        tarefa.dados = dados
                        await _publish_campo_event(
                            session=session,
                            event=_build_sync_failure_event(tarefa, e, status="ERROR"),
                            status="published",
                        )
                        await session.commit()
                except Exception:
                    await session.rollback()

    return SyncPushResponse(processed_at=datetime.utcnow(), results=results)
