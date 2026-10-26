"""Contratos de segurança da fundação AGRO-ADMIN-01B1."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from core.config import settings
from core.dependencies import (
    _decode_platform_token,
    _validate_token_session,
    get_tenant_id,
    verify_commercial_jwt_guardrail,
)
from core.models.sessao import SessaoAtiva
from core.services.auth_service import AuthService, hash_password


def _service() -> AuthService:
    return AuthService(MagicMock())


def test_token_individual_tem_emissor_audiencia_escopo_e_expiracao():
    token = _service().create_access_token(
        {"sub": "00000000-0000-0000-0000-000000000001", "tenant_id": None},
        expires_delta=timedelta(minutes=5),
    )
    claims = _decode_platform_token(token)
    assert claims["iss"] == settings.jwt_issuer
    assert claims["aud"] == settings.jwt_audience
    assert claims["account_type"] == "INDIVIDUAL_FREE"
    assert claims["product_scope"] == ["agro:free"]
    assert claims["tenant_id"] is None
    assert claims["jti"]


def test_token_individual_nao_pode_injetar_tenant():
    forged_claims = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "account_type": "INDIVIDUAL_FREE",
        "product_scope": ["agro:free"],
    }
    token = _service().create_access_token(forged_claims)
    with pytest.raises(HTTPException) as exc:
        verify_commercial_jwt_guardrail(token)
    assert exc.value.status_code == 403


def test_token_v2_rejeita_audiencia_incorreta():
    token = _service().create_access_token({"sub": "test"})
    raw = jwt.get_unverified_claims(token)
    raw["aud"] = "outra-aplicacao"
    invalid = jwt.encode(raw, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        _decode_platform_token(invalid)
    assert exc.value.status_code == 401


def test_hash_central_permanece_bcrypt_compativel_com_agro():
    password = "SenhaSegura@123"  # noqa: S105 - credencial fictícia de teste
    password_hash = hash_password(password)
    assert _service().verify_password(password, password_hash)


@pytest.mark.asyncio
async def test_token_de_login_exige_sessao_persistida():
    token = _service().create_access_token(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "tenant_id": None,
            "session_required": True,
        }
    )
    result = MagicMock()
    result.one_or_none.return_value = None
    session = AsyncMock()
    session.execute.return_value = result
    with pytest.raises(HTTPException) as exc:
        await _validate_token_session(token, session)
    assert exc.value.status_code == 401
    assert "Sessão" in exc.value.detail


@pytest.mark.asyncio
async def test_claim_tenant_sem_vinculo_ativo_e_bloqueada():
    tenant_id = "00000000-0000-0000-0000-000000000002"
    request = MagicMock()
    request.headers = {}
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute.return_value = result
    claims = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "tenant_id": tenant_id,
        "account_type": "COMMERCIAL",
        "product_scope": ["saas"],
        "is_superuser": False,
    }
    with pytest.raises(HTTPException) as exc:
        await get_tenant_id(request, claims, session)
    assert exc.value.status_code == 403


def test_modelo_de_sessao_global_declara_tenant_nullable():
    assert SessaoAtiva.__table__.c.tenant_id.nullable is True


@pytest.mark.asyncio
async def test_recuperacao_central_nao_enumera_conta_sem_tenant():
    absent_result = MagicMock()
    absent_result.scalar_one_or_none.return_value = None
    absent_session = AsyncMock()
    absent_session.execute.return_value = absent_result
    absent = await AuthService(absent_session).create_password_reset_token(
        "pessoa@example.com"
    )

    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    user.email = "pessoa@example.com"
    user.nome_completo = "Pessoa"
    user.username = "pessoa"
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    previous_tokens_result = MagicMock()
    previous_tokens_result.scalars.return_value.all.return_value = []
    no_tenant_result = MagicMock()
    no_tenant_result.scalar_one_or_none.return_value = None
    existing_session = AsyncMock()
    existing_session.add = MagicMock()
    existing_session.execute.side_effect = [
        user_result,
        previous_tokens_result,
        no_tenant_result,
    ]
    with pytest.MonkeyPatch.context() as monkeypatch:
        send = AsyncMock()
        monkeypatch.setattr(
            "core.services.email_service.email_service.send_password_recovery", send
        )
        existing = await AuthService(existing_session).create_password_reset_token(
            "PESSOA@example.com"
        )

    assert existing == absent
    assert existing["email"] is None
    send.assert_awaited_once()
