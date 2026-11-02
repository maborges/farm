"""
Testes Unitários — Autenticação e Autorização
CORE-AUTH-01 a 08: Lógica pura do AuthService (sem HTTP)
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta
from jose import jwt

from core.services.auth_service import AuthService, hash_password
from core.schemas.auth_schemas import LoginRequest, UserCreateRequest
from core.config import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_mock_user(
    email="fazendeiro@teste.com",
    senha="Senha@123",
    ativo=True,
    is_superuser=False,
):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.username = "fazendeiro"
    user.nome_completo = "Fazendeiro Teste"
    user.senha_hash = hash_password(senha)
    user.ativo = ativo
    user.is_superuser = is_superuser
    user.foto_perfil_url = None
    return user


def make_login_material(user):
    return {
        "usuario_id": user.id,
        "email": user.email,
        "username": user.username,
        "senha_hash": user.senha_hash,
        "is_superuser": user.is_superuser,
        "ativo": user.ativo,
    }


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def auth_service(mock_session):
    return AuthService(mock_session)


# ---------------------------------------------------------------------------
# CORE-AUTH-01: Login com credenciais válidas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_credenciais_validas(auth_service, mock_session):
    """CORE-AUTH-01: Login com credenciais válidas retorna usuário e token JWT"""
    user = make_mock_user()

    result_mock = MagicMock()
    result_mock.mappings.return_value.one_or_none.return_value = make_login_material(user)
    result_mock.scalars.return_value.all.return_value = []  # sem tenants
    mock_session.execute.return_value = result_mock

    login_data = LoginRequest(email="fazendeiro@teste.com", senha="Senha@123")
    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_sucesso", new=AsyncMock()):
        returned_user, token = await auth_service.authenticate_user(login_data)

    assert returned_user.id == user.id
    assert token is not None
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert payload["sub"] == str(user.id)


# ---------------------------------------------------------------------------
# CORE-AUTH-02: Login com email inválido
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_email_invalido(auth_service, mock_session):
    """CORE-AUTH-02: Login com email inexistente retorna 401"""
    from fastapi import HTTPException

    result_mock = MagicMock()
    result_mock.mappings.return_value.one_or_none.return_value = None
    mock_session.execute.return_value = result_mock

    login_data = LoginRequest(email="naoexiste@teste.com", senha="qualquer")

    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_falha", new=AsyncMock()):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(login_data)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# CORE-AUTH-03: Login com senha inválida
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_senha_invalida(auth_service, mock_session):
    """CORE-AUTH-03: Login com senha errada retorna 401"""
    from fastapi import HTTPException

    user = make_mock_user(senha="SenhaCorreta@123")

    result_mock = MagicMock()
    result_mock.mappings.return_value.one_or_none.return_value = make_login_material(user)
    mock_session.execute.return_value = result_mock

    login_data = LoginRequest(email="fazendeiro@teste.com", senha="SenhaErrada@999")

    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_falha", new=AsyncMock()):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(login_data)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# CORE-AUTH-04: JWT gerado com claims corretos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_claims_corretos(auth_service, mock_session):
    """CORE-AUTH-04: Token JWT contém sub, tenant_id, modules, exp"""
    user = make_mock_user()

    result_mock = MagicMock()
    result_mock.mappings.return_value.one_or_none.return_value = make_login_material(user)
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result_mock

    login_data = LoginRequest(email="fazendeiro@teste.com", senha="Senha@123")
    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_sucesso", new=AsyncMock()):
        _, token = await auth_service.authenticate_user(login_data)

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert "sub" in payload
    assert "modules" in payload
    assert "exp" in payload
    assert "CORE" in payload["modules"]


# ---------------------------------------------------------------------------
# CORE-AUTH-05: Usuário inativo bloqueado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_usuario_inativo(auth_service, mock_session):
    """CORE-AUTH-05: Usuário inativo retorna 403"""
    from fastapi import HTTPException

    user = make_mock_user(ativo=False)

    result_mock = MagicMock()
    result_mock.mappings.return_value.one_or_none.return_value = make_login_material(user)
    mock_session.execute.return_value = result_mock

    login_data = LoginRequest(email="fazendeiro@teste.com", senha="Senha@123")

    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_falha", new=AsyncMock()):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(login_data)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# CORE-AUTH-05B: Login sem tenant ativo continua funcional
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sem_tenant_ativo(auth_service, mock_session):
    """CORE-AUTH-05B: Usuário sem tenant ativo ainda recebe token."""
    user = make_mock_user()

    user_result = MagicMock()
    user_result.mappings.return_value.one_or_none.return_value = make_login_material(user)

    tenant_usuario_result = MagicMock()
    tenant_usuario_result.scalar_one_or_none.return_value = None
    tenant_usuario_result.scalars.return_value.all.return_value = []

    tenant_links_result = MagicMock()
    tenant_links_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        user_result,
        tenant_usuario_result,
        tenant_links_result,
    ]
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    login_data = LoginRequest(email=user.email, senha="Senha@123")

    with patch("core.services.login_rate_limit_service.LoginRateLimitService.verificar_bloqueio", new=AsyncMock(return_value=(False, None))), \
         patch("core.services.login_rate_limit_service.LoginRateLimitService.registrar_tentativa_sucesso", new=AsyncMock()), \
         patch("core.services.auth_service.get_session_idle_minutes", new=AsyncMock(return_value=30)):
        returned_user, token = await auth_service.authenticate_user(login_data)

    assert returned_user.id == user.id
    assert token is not None
    assert mock_session.add.call_count == 1
    persisted_session = mock_session.add.call_args.args[0]
    assert persisted_session.tenant_id is None
    assert persisted_session.usuario_id == user.id
    mock_session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# CORE-AUTH-06: Senha hasheada com bcrypt
# ---------------------------------------------------------------------------

def test_senha_hash_bcrypt():
    """CORE-AUTH-06: Senha é armazenada como hash bcrypt (nunca plain text)"""
    senha = "MinhaSenha@123"
    hashed = hash_password(senha)

    assert hashed != senha
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    import bcrypt
    assert bcrypt.checkpw(senha.encode('utf-8'), hashed.encode('utf-8'))


# ---------------------------------------------------------------------------
# CORE-AUTH-07: Registro de novo usuário
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registro_novo_usuario(auth_service, mock_session):
    """CORE-AUTH-07: Registro com dados válidos cria usuário"""
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None  # sem duplicata
    mock_session.execute.return_value = result_mock
    mock_session.commit = AsyncMock()

    user_data = UserCreateRequest(
        email="novo@fazenda.com",
        username="novo_fazendeiro",
        nome_completo="Novo Fazendeiro",
        apelido="Novo",
        senha="Senha@456",
    )

    # Captura o objeto adicionado à session
    added_objects = []
    mock_session.add.side_effect = lambda obj: added_objects.append(obj)

    from core.models import Usuario
    with patch.object(Usuario, "__init__", lambda self, **kw: self.__dict__.update(kw)):
        await auth_service.register_user(user_data)

    mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# CORE-AUTH-08: Registro com email duplicado retorna erro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registro_email_duplicado(auth_service, mock_session):
    """CORE-AUTH-08: Registro com email já cadastrado retorna 400"""
    from fastapi import HTTPException

    existing_user = make_mock_user()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = existing_user
    mock_session.execute.return_value = result_mock

    user_data = UserCreateRequest(
        email="fazendeiro@teste.com",
        username="outro_user",
        nome_completo="Outro",
        apelido="Outro",
        senha="Senha@789",
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register_user(user_data)

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# CORE-AUTH helper: create_access_token com expiração customizada
# ---------------------------------------------------------------------------

def test_token_expiracao_customizada():
    """create_access_token respeita expires_delta"""
    from core.services.auth_service import AuthService
    from unittest.mock import MagicMock
    svc = AuthService(MagicMock())

    token = svc.create_access_token({"sub": "test"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )

    from datetime import datetime, timezone
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff_minutes = (exp - now).total_seconds() / 60

    assert 4 <= diff_minutes <= 6
