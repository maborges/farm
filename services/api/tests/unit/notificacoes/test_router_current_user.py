"""Regressão: get_current_user retorna o objeto Usuario (ORM), não um dict.

Bug real em produção: endpoints de notificações faziam current_user["sub"],
mas core.dependencies.get_current_user devolve `Usuario` (SQLAlchemy model),
que não é subscriptable — TypeError 500 em toda chamada autenticada.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from notificacoes import router as notificacoes_router


def _current_user(usuario_id: uuid.UUID) -> MagicMock:
    """Simula o retorno real de get_current_user: um objeto com atributo .id, não dict."""
    user = MagicMock()
    user.id = usuario_id
    # Garantir que o mock não suporta __getitem__ como um dict suportaria,
    # reproduzindo o TypeError real do bug original.
    del user.__getitem__
    return user


@pytest.mark.asyncio
async def test_listar_nao_falha_com_objeto_usuario_real():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    current_user = _current_user(usuario_id)

    with pytest.MonkeyPatch.context() as mp:
        svc_mock = AsyncMock()
        svc_mock.listar = AsyncMock(return_value=[])
        mp.setattr(notificacoes_router, "NotificacaoService", MagicMock(return_value=svc_mock))

        await notificacoes_router.listar(
            lida=None, limit=50, session=AsyncMock(), tenant_id=tenant_id, current_user=current_user
        )

    svc_mock.listar.assert_awaited_once_with(usuario_id, lida=None, limit=50)


@pytest.mark.asyncio
async def test_count_nao_lidas_nao_falha_com_objeto_usuario_real():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    current_user = _current_user(usuario_id)

    with pytest.MonkeyPatch.context() as mp:
        svc_mock = AsyncMock()
        svc_mock.total_nao_lidas = AsyncMock(return_value=3)
        mp.setattr(notificacoes_router, "NotificacaoService", MagicMock(return_value=svc_mock))

        result = await notificacoes_router.count_nao_lidas(
            session=AsyncMock(), tenant_id=tenant_id, current_user=current_user
        )

    assert result == {"count": 3}
    svc_mock.total_nao_lidas.assert_awaited_once_with(usuario_id)


@pytest.mark.asyncio
async def test_marcar_lidas_nao_falha_com_objeto_usuario_real():
    from notificacoes.schemas import MarcarLidasRequest

    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    current_user = _current_user(usuario_id)

    with pytest.MonkeyPatch.context() as mp:
        svc_mock = AsyncMock()
        svc_mock.marcar_lidas = AsyncMock(return_value=2)
        mp.setattr(notificacoes_router, "NotificacaoService", MagicMock(return_value=svc_mock))

        await notificacoes_router.marcar_lidas(
            dados=MarcarLidasRequest(ids=None), session=AsyncMock(), tenant_id=tenant_id, current_user=current_user
        )

    svc_mock.marcar_lidas.assert_awaited_once_with(usuario_id, None)
