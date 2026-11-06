from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.routers import onboarding


class _Result:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class _Session:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []
        self.added = []
        self.commit = AsyncMock()

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)

    async def get(self, model, identity):
        return SimpleNamespace(nome="Plano Teste", preco_mensal=100, preco_anual=1000)

    def add(self, value):
        self.added.append(value)


def _assert_tenant_subscription_filter(statement):
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "assinaturas_tenant.tipo_assinatura = 'TENANT'" in compiled


@pytest.mark.asyncio
async def test_obter_dados_ativacao_localiza_assinatura_tenant():
    tenant = SimpleNamespace(
        id=uuid.uuid4(), nome="Fazenda Teste", activation_expires_at=None,
        ativo=False, telefone_responsavel=None, email_responsavel="owner@example.com",
    )
    usuario = SimpleNamespace(email="owner@example.com", nome_completo="Responsável")
    assinatura = SimpleNamespace(plano_id=uuid.uuid4(), ciclo_pagamento="ANUAL")
    session = _Session([
        _Result(tenant), _Result(usuario), _Result(values=[]), _Result(assinatura),
    ])

    response = await onboarding.obter_dados_ativacao("token", session)

    _assert_tenant_subscription_filter(session.statements[3])
    assert response.plano_nome == "Plano Teste"
    assert response.ciclo_pagamento == "ANUAL"


@pytest.mark.asyncio
async def test_ativar_conta_localiza_assinatura_tenant_e_inicia_checkout(monkeypatch):
    tenant = SimpleNamespace(
        id=uuid.uuid4(), nome="Fazenda Teste", activation_expires_at=None,
        ativo=False, telefone_responsavel=None,
    )
    usuario = SimpleNamespace(email="owner@example.com", nome_completo="Antigo")
    assinatura = SimpleNamespace(
        id=uuid.uuid4(), plano_id=uuid.uuid4(), ciclo_pagamento="MENSAL",
    )
    session = _Session([
        _Result(tenant), _Result(usuario), _Result(assinatura), _Result(None),
    ])

    class _Auth:
        def __init__(self, _session):
            pass

        @staticmethod
        def get_password_hash(password):
            return f"hash:{password}"

    stripe = SimpleNamespace(criar_checkout_assinatura=AsyncMock(return_value="https://checkout.test"))
    monkeypatch.setattr(onboarding, "AuthService", _Auth)
    monkeypatch.setattr("core.services.stripe_service.StripeService", lambda: stripe)

    response = await onboarding.ativar_conta(
        "token",
        onboarding.AtivarContaRequest(nome_completo="Novo Responsável", senha="senha123"),
        session,
    )

    _assert_tenant_subscription_filter(session.statements[2])
    stripe.criar_checkout_assinatura.assert_awaited_once()
    assert response.checkout_url == "https://checkout.test"
    assert usuario.senha_hash == "hash:senha123"
    session.commit.assert_awaited_once()
