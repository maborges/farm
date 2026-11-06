from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import stripe

from core.services import stripe_service


PLANO_ID = "88e51b0f-b2ca-4142-9efc-81034226a072"
TENANT_ID = "tenant-test-123"
ASSINATURA_ID = "assinatura-test-456"
EMAIL = "produtor@example.test"
PRICE_ID = "price_test_sandbox"
FRONTEND_URL = "https://frontend.example.test"


@pytest.fixture
def stripe_mocks(monkeypatch):
    price_list = Mock(return_value=SimpleNamespace(data=[SimpleNamespace(id=PRICE_ID)]))
    session_create = Mock(
        return_value=SimpleNamespace(id="cs_test_123", url="https://checkout.example.test/session")
    )
    monkeypatch.setattr(stripe_service.stripe.Price, "list", price_list)
    monkeypatch.setattr(stripe_service.stripe.checkout.Session, "create", session_create)
    monkeypatch.setattr(stripe_service, "FRONTEND_URL", FRONTEND_URL)
    monkeypatch.setattr(stripe_service.stripe, "api_key", "sk_test_fake_only")
    return price_list, session_create


@pytest.mark.asyncio
async def test_criar_checkout_assinatura_busca_preco_e_cria_checkout(stripe_mocks):
    price_list, session_create = stripe_mocks

    url = await stripe_service.StripeService().criar_checkout_assinatura(
        tenant_id=TENANT_ID,
        assinatura_id=ASSINATURA_ID,
        email=EMAIL,
        plano_id=PLANO_ID,
        ciclo="MENSAL",
    )

    price_list.assert_called_once_with(
        lookup_keys=[f"plano_{PLANO_ID}_MENSAL"], limit=1
    )
    session_create.assert_called_once_with(
        customer_email=EMAIL,
        payment_method_types=["card"],
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=(
            f"{FRONTEND_URL}/onboarding/sucesso?session_id={{CHECKOUT_SESSION_ID}}"
        ),
        cancel_url=f"{FRONTEND_URL}/onboarding/cancelado",
        metadata={"tenant_id": TENANT_ID, "assinatura_id": ASSINATURA_ID},
    )
    assert url == "https://checkout.example.test/session"


@pytest.mark.asyncio
async def test_criar_checkout_assinatura_erro_quando_preco_nao_existe(
    stripe_mocks, monkeypatch
):
    price_list, session_create = stripe_mocks
    price_list.return_value = SimpleNamespace(data=[])

    with pytest.raises(ValueError, match="Preço não configurado no Stripe"):
        await stripe_service.StripeService().criar_checkout_assinatura(
            TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
        )

    price_list.assert_called_once_with(
        lookup_keys=[f"plano_{PLANO_ID}_MENSAL"], limit=1
    )
    session_create.assert_not_called()


@pytest.mark.asyncio
async def test_criar_checkout_assinatura_converte_erro_da_api_stripe(
    stripe_mocks,
):
    price_list, session_create = stripe_mocks
    session_create.side_effect = stripe.StripeError("falha simulada da API")

    with pytest.raises(ValueError, match="Erro ao criar sessão de pagamento: falha simulada da API"):
        await stripe_service.StripeService().criar_checkout_assinatura(
            TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
        )

    price_list.assert_called_once()
    session_create.assert_called_once()


@pytest.mark.asyncio
async def test_criar_checkout_assinatura_usa_fallback_sem_api_key(
    stripe_mocks, monkeypatch
):
    price_list, session_create = stripe_mocks
    monkeypatch.setattr(stripe_service.stripe, "api_key", None)

    url = await stripe_service.StripeService().criar_checkout_assinatura(
        TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
    )

    assert url == (
        f"{FRONTEND_URL}/onboarding/pagamento-simulado"
        f"?assinatura_id={ASSINATURA_ID}"
    )
    price_list.assert_not_called()
    session_create.assert_not_called()
