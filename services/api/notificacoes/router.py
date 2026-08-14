from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status, Body, HTTPException
import asyncio
from loguru import logger
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.dependencies import get_tenant_id, get_session, get_current_admin
from core.database import async_session_maker
from notificacoes.models import Notificacao
from notificacoes.schemas import NotificacaoCreate, NotificacaoResponse, MarcarLidasRequest, NotificacaoPreferenciaUpdate, NotificacaoPreferenciaResponse
from notificacoes.service import NotificacaoService, manager
from notificacoes.alertas_engine import AlertasEngine
from core.dependencies import get_current_user

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])

# Intervalo máximo sem atividade do cliente antes de revalidar usuário/tenant no banco.
REVALIDATE_INTERVAL_SECONDS = 5 * 60


# ── REST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[NotificacaoResponse])
async def listar(
    lida: Optional[bool] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificacaoService(session, tenant_id)
    return await svc.listar(UUID(current_user["sub"]), lida=lida, limit=limit)


@router.get("/nao-lidas-count")
async def count_nao_lidas(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificacaoService(session, tenant_id)
    return {"count": await svc.total_nao_lidas(UUID(current_user["sub"]))}


@router.post("/marcar-lidas")
async def marcar_lidas(
    dados: MarcarLidasRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificacaoService(session, tenant_id)
    count = await svc.marcar_lidas(UUID(current_user["sub"]), dados.ids)
    return {"message": f"{count} notificação(ões) marcada(s) como lida(s)"}


@router.post("/", response_model=NotificacaoResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    dados: NotificacaoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = NotificacaoService(session, tenant_id)
    return await svc.criar_e_push(dados)


@router.get("/preferencias", response_model=List[NotificacaoPreferenciaResponse])
async def listar_preferencias(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    usuario_id = UUID(current_user["sub"])
    svc = NotificacaoService(session, tenant_id)
    return await svc.listar_preferencias(usuario_id)


@router.patch("/preferencias/{tipo}", response_model=NotificacaoPreferenciaResponse)
async def atualizar_preferencia(
    tipo: str,
    dados: NotificacaoPreferenciaUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    usuario_id = UUID(current_user["sub"])
    svc = NotificacaoService(session, tenant_id)
    return await svc.upsert_preferencia(usuario_id, tipo, dados)


@router.post("/demo")
async def gerar_demo(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Cria notificações de demonstração para testar o sistema. Indisponível em produção."""
    from core.config import settings
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Recurso indisponível.")

    svc = NotificacaoService(session, tenant_id)
    demos = [
        NotificacaoCreate(
            tipo="PREVISAO_CHUVA",
            titulo="Chuva prevista nas próximas 24h",
            mensagem="Risco de perda de eficiência em aplicações de defensivos. Evite aplicações nos Talhões A1 e B2.",
            meta={"talhoes": ["A1", "B2"], "precipitacao_mm": 35},
        ),
        NotificacaoCreate(
            tipo="NDVI_BAIXO",
            titulo="NDVI crítico — Talhão Norte",
            mensagem="NDVI do Talhão Norte caiu para 0.42, abaixo do limiar de 0.55. Verifique o desenvolvimento da cultura.",
            meta={"talhao": "Talhão Norte", "ndvi": 0.42, "limiar": 0.55},
        ),
        NotificacaoCreate(
            tipo="DIARIA_PENDENTE",
            titulo="3 diárias pendentes há mais de 15 dias",
            mensagem="Colaboradores com diárias não pagas: João Silva (3×), Maria Santos (2×). Total: R$ 750,00.",
            meta={"total_pendente": 750.0, "colaboradores": 2},
        ),
        NotificacaoCreate(
            tipo="VENCIMENTO_APLICACAO",
            titulo="Carência de aplicação vence amanhã",
            mensagem="O defensivo aplicado no Talhão Sul (Lote 04/B) tem carência vencendo em 24h. Não colher antes.",
            meta={"talhao": "Talhão Sul", "defensivo": "Fungicida X", "carencia_dias": 1},
        ),
    ]
    for d in demos:
        await svc.criar_e_push(d)
    return {"message": f"{len(demos)} notificações de demonstração criadas"}


@router.post("/sincronizar", response_model=List[NotificacaoResponse])
async def sincronizar_notificacoes(
    safra_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Cria notificações a partir das ações pendentes do plano de ação da safra."""
    svc = NotificacaoService(session, tenant_id)
    return await svc.sincronizar_safra(safra_id)


@router.patch("/{notificacao_id}/lida", response_model=NotificacaoResponse)
async def marcar_uma_lida(
    notificacao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificacaoService(session, tenant_id)
    usuario_id = UUID(current_user["sub"])
    await svc.marcar_lidas(usuario_id, [notificacao_id])
    result = await session.get(Notificacao, notificacao_id)
    if result is not None:
        session.expunge(result)
        result.lida = True  # reflete a leitura do usuário atual; não é persistido na coluna tenant-wide
    return result


@router.post("/alertas/verificar", response_model=dict)
async def verificar_alertas_automaticos(
    tenant_id: Optional[UUID] = Depends(get_tenant_id),
    admin: dict = Depends(get_current_admin),  # Apenas admin SaaS pode executar
):
    """
    Executa o motor de alertas automáticos manualmente.
    Apenas administradores do SaaS podem executar.
    """
    logger.info(f"Admin {admin.get('sub')} solicitou verificação de alertas")

    engine = AlertasEngine()

    if tenant_id:
        # Verificar apenas um tenant específico
        alertas = await engine.verificar_tenant(tenant_id)
        return {
            "message": f"Verificação concluída para tenant {tenant_id}",
            "alertas_gerados": len(alertas),
        }
    else:
        # Verificar todos os tenants
        resultados = await engine.verificar_todos_tenants()
        return resultados


# ── WebSocket ─────────────────────────────────────────────────────────────────

async def _autenticar_ws_notificacoes(token: str) -> tuple[str, str] | None:
    """
    Valida o JWT do WebSocket e confirma no banco que o usuário está ativo
    e vinculado (status ATIVO) ao tenant informado no token.

    Mesmo padrão de validação usado em core/routers/support_ws.py — o token
    chega via query param (não é possível reaproveitar get_current_user_claims/
    get_tenant_id, que dependem de Authorization header via Request), mas a
    checagem de usuário/tenant ativos no banco é obrigatória, igual ao REST.

    Retorna (tenant_id, usuario_id) validados, ou None se a autenticação falhar.
    Usuario_id é necessário para leitura por usuário (notificacoes_leituras).
    """
    from core.config import settings
    from jose import jwt as jose_jwt, JWTError

    try:
        payload = jose_jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None

    user_id_str = payload.get("sub")
    tenant_id_str = payload.get("tenant_id")
    if not user_id_str or not tenant_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
        tenant_id = UUID(tenant_id_str)
    except ValueError:
        return None

    from core.models.auth import Usuario, TenantUsuario

    async with async_session_maker() as session:
        usuario = await session.get(Usuario, user_id)
        if not usuario or not usuario.ativo:
            return None

        result = await session.execute(
            select(TenantUsuario.id).where(
                TenantUsuario.tenant_id == tenant_id,
                TenantUsuario.usuario_id == user_id,
                TenantUsuario.status == "ATIVO",
            )
        )
        if result.scalar_one_or_none() is None:
            return None

    return tenant_id_str, user_id_str


@router.websocket("/ws")
async def ws_notificacoes(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket de notificações em tempo real.
    Conecte com: ws://<host>/api/v1/notificacoes/ws?token=<jwt>
    """
    auth = await _autenticar_ws_notificacoes(token)
    if not auth:
        await websocket.close(code=1008)
        return
    tenant_id, usuario_id = auth

    await manager.connect(tenant_id, websocket)
    try:
        # Send initial unread count on connect
        async with async_session_maker() as session:
            svc = NotificacaoService(session, UUID(tenant_id))
            count = await svc.total_nao_lidas(UUID(usuario_id))
            await websocket.send_json({"tipo": "init", "nao_lidas": count})

        # Listen for client-side actions (e.g. mark as read). A conexão fica
        # aberta por horas — sem revalidar periodicamente, um usuário
        # desativado ou removido do tenant continuaria recebendo pushes até
        # a conexão cair por outro motivo. A cada REVALIDATE_INTERVAL_SECONDS
        # sem mensagem do cliente, reautentica; se o token/usuário/tenant não
        # forem mais válidos, encerra a conexão.
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(), timeout=REVALIDATE_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                if not await _autenticar_ws_notificacoes(token):
                    manager.disconnect(tenant_id, websocket)
                    await websocket.close(code=1008)
                    return
                continue

            action = data.get("action")

            if action == "marcar_lidas":
                raw_ids = data.get("ids")
                ids = [UUID(i) for i in raw_ids] if raw_ids else None
                async with async_session_maker() as session:
                    svc = NotificacaoService(session, UUID(tenant_id))
                    await svc.marcar_lidas(UUID(usuario_id), ids)
                    count = await svc.total_nao_lidas(UUID(usuario_id))
                    await websocket.send_json({"tipo": "contagem_atualizada", "nao_lidas": count})

            elif action == "ping":
                await websocket.send_json({"tipo": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(tenant_id, websocket)
    except Exception as exc:
        logger.exception(f"WS notificacoes erro inesperado (tenant={tenant_id}): {exc}")
        manager.disconnect(tenant_id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
