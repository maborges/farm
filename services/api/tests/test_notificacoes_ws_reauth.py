"""Testes de reautenticação periódica do WS de notificações e bloqueio do endpoint demo."""
import uuid
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from jose import jwt as jose_jwt

from core.config import settings
from notificacoes.router import _autenticar_ws_notificacoes, gerar_demo


def _make_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    return jose_jwt.encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _mock_session_maker(usuario, tenant_usuario_id):
    session = AsyncMock()
    session.get = AsyncMock(return_value=usuario)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = tenant_usuario_id
    session.execute = AsyncMock(return_value=result_mock)

    @asynccontextmanager
    async def _maker():
        yield session

    return _maker


@pytest.mark.asyncio
async def test_autenticar_ws_token_invalido_retorna_none():
    """Token malformado/assinatura errada deve falhar sem consultar o banco."""
    resultado = await _autenticar_ws_notificacoes("token-invalido")
    assert resultado is None


@pytest.mark.asyncio
async def test_autenticar_ws_usuario_inativo_retorna_none():
    """Usuário desativado no banco não deve ser revalidado com sucesso, mesmo com JWT válido."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = _make_token(user_id, tenant_id)

    usuario = MagicMock()
    usuario.ativo = False
    maker = _mock_session_maker(usuario, tenant_usuario_id=None)

    with patch("notificacoes.router.async_session_maker", maker):
        resultado = await _autenticar_ws_notificacoes(token)
    assert resultado is None


@pytest.mark.asyncio
async def test_autenticar_ws_tenant_removido_retorna_none():
    """Usuário ativo mas sem vínculo TenantUsuario ATIVO ao tenant deve falhar."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = _make_token(user_id, tenant_id)

    usuario = MagicMock()
    usuario.ativo = True
    maker = _mock_session_maker(usuario, tenant_usuario_id=None)  # sem vínculo ATIVO

    with patch("notificacoes.router.async_session_maker", maker):
        resultado = await _autenticar_ws_notificacoes(token)
    assert resultado is None


@pytest.mark.asyncio
async def test_autenticar_ws_usuario_e_tenant_validos_retorna_tenant_id():
    """Usuário ativo com vínculo ATIVO ao tenant deve revalidar com sucesso."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = _make_token(user_id, tenant_id)

    usuario = MagicMock()
    usuario.ativo = True
    maker = _mock_session_maker(usuario, tenant_usuario_id=uuid.uuid4())

    with patch("notificacoes.router.async_session_maker", maker):
        resultado = await _autenticar_ws_notificacoes(token)
    assert resultado == (str(tenant_id), str(user_id))


@pytest.mark.asyncio
async def test_autenticar_ws_token_sem_claims_obrigatorias_retorna_none():
    """Token válido mas sem sub/tenant_id no payload deve falhar antes de consultar o banco."""
    token = jose_jwt.encode({}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    resultado = await _autenticar_ws_notificacoes(token)
    assert resultado is None


@pytest.mark.asyncio
async def test_gerar_demo_bloqueado_em_producao():
    """Endpoint /notificacoes/demo deve responder 404 quando environment == production."""
    with patch("core.config.settings.environment", "production"):
        with pytest.raises(HTTPException) as exc_info:
            await gerar_demo(session=AsyncMock(), tenant_id=uuid.uuid4())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_gerar_demo_permitido_fora_de_producao():
    """Endpoint /notificacoes/demo deve funcionar normalmente fora de produção."""
    with patch("core.config.settings.environment", "development"):
        with patch("notificacoes.router.NotificacaoService") as MockService:
            MockService.return_value.criar_e_push = AsyncMock()
            resultado = await gerar_demo(session=AsyncMock(), tenant_id=uuid.uuid4())
    assert "demonstração" in resultado["message"]
    assert MockService.return_value.criar_e_push.await_count == 4
