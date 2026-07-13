import pytest
import httpx
from httpx import Response
from fastapi.exceptions import HTTPException

from integracoes.sankhya.routers import configurar_sankhya
from integracoes.sankhya.schemas import SankhyaConfigCreate
from integracoes.sankhya.services.sync_service import SankhyaSyncService
import uuid

@pytest.fixture
def mock_httpx_auth_ok(monkeypatch):
    async def _post(*args, **kwargs):
        # Retorna token fake
        return Response(
            200, 
            json={"bearerToken": "fake_token", "expiresIn": 3600},
            request=httpx.Request("POST", "https://gateway.example")
        )
    
    # Mock httpx.AsyncClient.post
    monkeypatch.setattr("httpx.AsyncClient.post", _post)

    async def _fake_publish(*args, **kwargs):
        pass
    monkeypatch.setattr("integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe", _fake_publish)

@pytest.mark.asyncio
async def test_fluxo_e2e_gateway_oauth_completo(session, mock_dns_globally, mock_httpx_auth_ok):
    tenant_id = uuid.uuid4()
    sync_service = SankhyaSyncService(session)

    payload = SankhyaConfigCreate(
        auth_model="gateway_oauth_client_credentials",
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/auth",
        sankhya_client_id="client123",
        sankhya_client_secret="secret456",
        sankhya_x_token="xtoken789",
        sync_interval=900,
    )

    response = await configurar_sankhya(
        config=payload,
        tenant_id=tenant_id,
        sync_service=sync_service,
    )

    config_salva = await sync_service.get_config(str(tenant_id))
    assert config_salva is not None
    assert config_salva.api_base_url == "https://gateway.example/api"
    
    from integracoes.sankhya.services.auth_service import SankhyaGatewayAuthService
    auth = SankhyaGatewayAuthService(config_salva)
    assert auth.auth_model() == "gateway_oauth_client_credentials"

    test_result = await sync_service.testar_conexao(str(tenant_id))
    assert test_result.sucesso is True

@pytest.mark.asyncio
async def test_fluxo_e2e_legacy_login_nao_cai_no_fallback_oauth(session, mock_dns_globally, mock_httpx_auth_ok, monkeypatch):
    tenant_id = uuid.uuid4()
    sync_service = SankhyaSyncService(session)

    # Legacy basic uses ws_url, username, password instead. Legacy gateway uses token and appkey
    payload = SankhyaConfigCreate(
        auth_model="legacy_ws_basic_auth",
        sankhya_environment="producao",
        ws_url="https://legacy.example/api",
        username="legacyUser",
        password="legacyPassword",
        sync_interval=900,
    )

    await configurar_sankhya(
        config=payload,
        tenant_id=tenant_id,
        sync_service=sync_service,
    )

    config_salva = await sync_service.get_config(str(tenant_id))
    from integracoes.sankhya.services.auth_service import SankhyaGatewayAuthService
    auth = SankhyaGatewayAuthService(config_salva)
    
    assert auth.auth_model() == "legacy_ws_basic_auth"

@pytest.mark.asyncio
async def test_save_bloqueia_auth_model_invalido(session, mock_dns_globally, mock_httpx_auth_ok):
    tenant_id = uuid.uuid4()
    sync_service = SankhyaSyncService(session)

    payload = SankhyaConfigCreate(
        auth_model="hacker_model",
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/auth",
        sankhya_client_id="client123",
        sync_interval=900,
    )

    with pytest.raises(HTTPException) as excinfo:
        await configurar_sankhya(
            config=payload,
            tenant_id=tenant_id,
            sync_service=sync_service,
        )
    assert "auth_model inválido: hacker_model" in str(excinfo.value.detail)
