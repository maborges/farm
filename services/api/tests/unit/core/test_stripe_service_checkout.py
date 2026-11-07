from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import stripe

from core.services import stripe_service


PLANO_ID = "88e51b0f-b2ca-4142-9efc-81034226a072"
TENANT_ID = "tenant-test-123"
ASSINATURA_ID = "assinatura-test-456"
EMAIL = "produtor@example.test"
PRICE_ID = "price_test_sandbox"
FRONTEND_URL = "https://frontend.example.test"


class StripeServiceCheckoutTests(unittest.IsolatedAsyncioTestCase):
    def _mocks(self):
        price_list = Mock(return_value=SimpleNamespace(data=[SimpleNamespace(id=PRICE_ID)]))
        session_create = Mock(
            return_value=SimpleNamespace(
                id="cs_test_123", url="https://checkout.example.test/session"
            )
        )
        return price_list, session_create

    async def test_busca_preco_e_cria_checkout_com_metadados_vinculados(self):
        price_list, session_create = self._mocks()
        with (
            patch.object(stripe_service.stripe.Price, "list", price_list),
            patch.object(stripe_service.stripe.checkout.Session, "create", session_create),
            patch.object(stripe_service.stripe, "api_key", "sk_test_fake_only"),
            patch.object(stripe_service, "FRONTEND_URL", FRONTEND_URL),
        ):
            url = await stripe_service.StripeService().criar_checkout_assinatura(
                TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
            )

        price_list.assert_called_once_with(
            lookup_keys=[f"plano_{PLANO_ID}_MENSAL"], limit=1
        )
        session_create.assert_called_once_with(
            customer_email=EMAIL,
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=(
                f"{FRONTEND_URL}/onboarding/sucesso?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{FRONTEND_URL}/onboarding/cancelado",
            metadata={
                "tenant_id": TENANT_ID,
                "assinatura_id": ASSINATURA_ID,
                "plano_id": PLANO_ID,
            },
        )
        self.assertEqual(url, "https://checkout.example.test/session")

    async def test_erro_quando_preco_nao_existe(self):
        price_list, session_create = self._mocks()
        price_list.return_value = SimpleNamespace(data=[])
        with (
            patch.object(stripe_service.stripe.Price, "list", price_list),
            patch.object(stripe_service.stripe.checkout.Session, "create", session_create),
            patch.object(stripe_service.stripe, "api_key", "sk_test_fake_only"),
        ):
            with self.assertRaisesRegex(ValueError, "Preço não configurado no Stripe"):
                await stripe_service.StripeService().criar_checkout_assinatura(
                    TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
                )
        session_create.assert_not_called()

    async def test_converte_erro_da_api_stripe(self):
        price_list, session_create = self._mocks()
        session_create.side_effect = stripe.StripeError("falha simulada da API")
        with (
            patch.object(stripe_service.stripe.Price, "list", price_list),
            patch.object(stripe_service.stripe.checkout.Session, "create", session_create),
            patch.object(stripe_service.stripe, "api_key", "sk_test_fake_only"),
        ):
            with self.assertRaisesRegex(
                ValueError, "Erro ao criar sessão de pagamento: falha simulada da API"
            ):
                await stripe_service.StripeService().criar_checkout_assinatura(
                    TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
                )

    async def test_fallback_sem_api_key_nao_chama_stripe(self):
        price_list, session_create = self._mocks()
        with (
            patch.object(stripe_service.stripe.Price, "list", price_list),
            patch.object(stripe_service.stripe.checkout.Session, "create", session_create),
            patch.object(stripe_service.stripe, "api_key", None),
            patch.object(stripe_service, "FRONTEND_URL", FRONTEND_URL),
        ):
            url = await stripe_service.StripeService().criar_checkout_assinatura(
                TENANT_ID, ASSINATURA_ID, EMAIL, PLANO_ID, "MENSAL"
            )
        self.assertEqual(
            url,
            f"{FRONTEND_URL}/onboarding/pagamento-simulado?assinatura_id={ASSINATURA_ID}",
        )
        price_list.assert_not_called()
        session_create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
