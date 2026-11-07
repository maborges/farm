from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import stripe
from fastapi import HTTPException

from core.models.billing import AssinaturaTenant, Fatura, PlanoAssinatura
from core.models.tenant import Tenant
from core.routers import stripe_webhooks
from core.services.auth_service import AuthService
from core.services.onboarding_service import OnboardingService

# Register mapped relationship targets before SQLAlchemy configures the global registry.
import agricola.cultivos.models  # noqa: F401
import agricola.analises_solo.models  # noqa: F401
import agricola.tarefas.models  # noqa: F401
import agricola.production_units.models  # noqa: F401
import agricola.romaneios.models  # noqa: F401
import agricola.operacoes.models  # noqa: F401
import agricola.receituario_agronomico.models  # noqa: F401
import operacional.models.qualidade  # noqa: F401
import operacional.models.frota  # noqa: F401
import operacional.models.apontamento  # noqa: F401


class Result:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalars(self):
        return self

    def first(self):
        return self.values[0] if self.values else None

    def all(self):
        return self.values

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, *, objects=None, results=None, commit_error=None):
        self.objects = objects or {}
        self.results = iter(results or [])
        self.statements = []
        self.added = []
        self.commit_error = commit_error
        self.commit = AsyncMock(side_effect=commit_error)
        self.rollback = AsyncMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, identity):
        return self.objects.get((model, str(identity)))

    async def execute(self, statement):
        self.statements.append(statement)
        try:
            return next(self.results)
        except StopIteration:
            return Result()

    def add(self, value):
        self.added.append(value)


def _plan(*, is_free: bool, tem_trial: bool, dias_trial: int = 14):
    return SimpleNamespace(
        id=uuid.uuid4(), is_free=is_free, tem_trial=tem_trial,
        dias_trial=dias_trial, preco_mensal=1, preco_anual=12,
        limite_usuarios_minimo=1, ativo=True,
    )


class OnboardingInitialStatusTests(unittest.IsolatedAsyncioTestCase):
    async def _register(self, *, is_free: bool, tem_trial: bool):
        plan = _plan(is_free=is_free, tem_trial=tem_trial)
        session = FakeSession(results=[Result(), Result(value=plan)])
        service = OnboardingService(session, MagicMock(get_password_hash=MagicMock(return_value="hash")))
        service._get_perfil_owner_sistema = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
        payload = SimpleNamespace(
            email="owner@example.test", username="owner", nome_completo="Owner",
            apelido="Owner", senha="secret", cpf=None, telefone=None,
            nome_produtor="Fazenda Teste", cnpj_tenant=None,
            plano_id=plan.id, ciclo="MENSAL",
        )
        send_activation = AsyncMock()
        send_registration = AsyncMock()
        with (
            patch(
                "core.services.onboarding_service.email_service.send_activation_link",
                new=send_activation,
            ),
            patch(
                "core.services.onboarding_service.email_service.send_registration_confirmation",
                new=send_registration,
            ),
        ):
            await service.register_new_tenant(payload)
        tenant = next(value for value in session.added if isinstance(value, Tenant))
        assinatura = next(value for value in session.added if isinstance(value, AssinaturaTenant))
        return tenant, assinatura, send_activation, send_registration

    async def test_plano_gratuito_inicia_ativa(self):
        tenant, assinatura, send_activation, send_registration = await self._register(
            is_free=True, tem_trial=False
        )
        self.assertEqual(assinatura.status, "ATIVA")
        self.assertTrue(tenant.ativo)
        send_registration.assert_awaited_once()
        send_activation.assert_not_awaited()

    async def test_plano_pago_com_trial_inicia_trial(self):
        tenant, assinatura, send_activation, send_registration = await self._register(
            is_free=False, tem_trial=True
        )
        self.assertEqual(assinatura.status, "TRIAL")
        self.assertTrue(tenant.ativo)
        send_registration.assert_awaited_once()
        send_activation.assert_not_awaited()

    async def test_plano_pago_sem_trial_aguarda_pagamento(self):
        tenant, assinatura, send_activation, send_registration = await self._register(
            is_free=False, tem_trial=False
        )
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertFalse(tenant.ativo)
        send_activation.assert_awaited_once()
        send_registration.assert_not_awaited()


class WebhookPaymentSafetyTests(unittest.IsolatedAsyncioTestCase):
    def _session_fixture(
        self, *, payment_status="paid", signature_status="PENDENTE_PAGAMENTO",
        invoice_status="ABERTA", tenant_id=None, signature_tenant_id=None,
        signature_plan_id=None, plan=None, lead_status="aprovado", commit_error=None,
        stripe_subscription_id=None,
    ):
        tenant_id = tenant_id or uuid.uuid4()
        plan = plan or _plan(is_free=False, tem_trial=False)
        assinatura_id = uuid.uuid4()
        tenant = SimpleNamespace(
            id=tenant_id, ativo=False, activation_token="activation-token",
            activation_expires_at=datetime.now(timezone.utc),
        )
        assinatura = SimpleNamespace(
            id=assinatura_id,
            tenant_id=signature_tenant_id or tenant_id,
            plano_id=signature_plan_id or plan.id,
            tipo_assinatura="TENANT",
            status=signature_status,
            stripe_subscription_id=stripe_subscription_id,
        )
        invoice = SimpleNamespace(
            tenant_id=tenant_id, assinatura_id=assinatura_id,
            status=invoice_status, data_aprovacao_rejeicao=None,
        )
        lead = SimpleNamespace(id=uuid.uuid4(), status=lead_status, data_conversao=None)
        session = FakeSession(
            objects={
                (Tenant, str(tenant_id)): tenant,
                (AssinaturaTenant, str(assinatura_id)): assinatura,
                (PlanoAssinatura, str(plan.id)): plan,
            },
            results=[Result(values=[invoice]), Result(value=lead)],
            commit_error=commit_error,
        )
        payload = {
            "id": "cs_test_synthetic",
            "mode": "subscription",
            "payment_status": payment_status,
            "subscription": "sub_test_synthetic",
            "metadata": {
                "tenant_id": str(tenant_id),
                "assinatura_id": str(assinatura_id),
                "plano_id": str(plan.id),
            },
        }
        return session, payload, tenant, assinatura, invoice, lead

    async def test_checkout_unpaid_nao_abre_sessao_ou_ativa_acesso(self):
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(payment_status="unpaid")
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session) as maker:
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertFalse(result)
        maker.assert_not_called()
        self.assertFalse(tenant.ativo)
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertEqual(invoice.status, "ABERTA")

    async def test_no_payment_required_somente_preserva_trial_sem_marcar_fatura_paga(self):
        trial = _plan(is_free=False, tem_trial=True)
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            payment_status="no_payment_required", signature_status="TRIAL", plan=trial
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertTrue(result)
        self.assertEqual(assinatura.status, "TRIAL")
        self.assertEqual(assinatura.stripe_subscription_id, "sub_test_synthetic")
        self.assertTrue(tenant.ativo)
        self.assertEqual(invoice.status, "ABERTA")
        session.commit.assert_awaited_once()

    async def test_no_payment_required_nao_ativa_plano_pago_pendente(self):
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            payment_status="no_payment_required"
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertFalse(result)
        self.assertFalse(tenant.ativo)
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertEqual(invoice.status, "ABERTA")
        session.commit.assert_not_awaited()

    async def test_no_payment_required_e_aceito_para_plano_gratuito(self):
        free_plan = _plan(is_free=True, tem_trial=False)
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            payment_status="no_payment_required", signature_status="ATIVA", plan=free_plan
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertTrue(result)
        self.assertEqual(assinatura.status, "ATIVA")
        self.assertEqual(assinatura.stripe_subscription_id, "sub_test_synthetic")
        self.assertTrue(tenant.ativo)
        self.assertEqual(invoice.status, "ABERTA")

    async def test_checkout_pago_ativa_tenant_assinatura_e_fatura_corretos(self):
        session, payload, tenant, assinatura, invoice, lead = self._session_fixture()
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertTrue(result)
        self.assertTrue(tenant.ativo)
        self.assertIsNone(tenant.activation_token)
        self.assertEqual(assinatura.tenant_id, tenant.id)
        self.assertEqual(assinatura.status, "ATIVA")
        self.assertEqual(assinatura.stripe_subscription_id, "sub_test_synthetic")
        self.assertEqual(invoice.status, "PAGA")
        self.assertIsNotNone(invoice.data_aprovacao_rejeicao)
        self.assertEqual(lead.status, "convertido")
        session.commit.assert_awaited_once()
        sql = str(session.statements[0].compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("faturas.tenant_id", sql)
        self.assertIn("faturas.assinatura_id", sql)

    async def test_checkout_duplicado_nao_repete_baixa_ou_conversao(self):
        session, payload, tenant, assinatura, invoice, lead = self._session_fixture(
            signature_status="ATIVA", invoice_status="PAGA", lead_status="convertido",
            stripe_subscription_id="sub_test_synthetic",
        )
        paid_at = datetime(2026, 11, 1, tzinfo=timezone.utc)
        invoice.data_aprovacao_rejeicao = paid_at
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            result = await stripe_webhooks._handle_checkout_completed(payload)
        self.assertTrue(result)
        self.assertEqual(invoice.data_aprovacao_rejeicao, paid_at)
        self.assertEqual(invoice.status, "PAGA")
        self.assertEqual(lead.status, "convertido")
        self.assertEqual(assinatura.stripe_subscription_id, "sub_test_synthetic")
        session.commit.assert_awaited_once()

    async def test_assinatura_vinculada_a_outro_tenant_falha_sem_commit(self):
        other_tenant_id = uuid.uuid4()
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            signature_tenant_id=other_tenant_id
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks._handle_checkout_completed(payload)
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(tenant.ativo)
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertEqual(invoice.status, "ABERTA")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_plano_checkout_divergente_falha_sem_commit(self):
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            signature_plan_id=uuid.uuid4()
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks._handle_checkout_completed(payload)
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(tenant.ativo)
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertEqual(invoice.status, "ABERTA")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_assinatura_inexistente_falha_sem_confirmar_processamento(self):
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture()
        session.objects.pop((AssinaturaTenant, str(assinatura.id)))
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks._handle_checkout_completed(payload)
        self.assertEqual(error.exception.status_code, 500)
        self.assertFalse(tenant.ativo)
        self.assertEqual(invoice.status, "ABERTA")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_fatura_ausente_falha_para_permitir_retry(self):
        session, payload, tenant, assinatura, _, _ = self._session_fixture()
        session.results = iter([Result(values=[])])
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks._handle_checkout_completed(payload)
        self.assertEqual(error.exception.status_code, 500)
        self.assertFalse(tenant.ativo)
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    async def test_falha_de_commit_faz_rollback_e_propaga_erro(self):
        session, payload, tenant, assinatura, invoice, _ = self._session_fixture(
            commit_error=RuntimeError("db-secret-should-not-be-logged")
        )
        with patch.object(stripe_webhooks, "async_session_maker", return_value=session):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks._handle_checkout_completed(payload)
        self.assertEqual(error.exception.status_code, 500)
        session.rollback.assert_awaited_once()
        self.assertTrue(tenant.ativo)  # FakeSession confirms rollback was requested; it has no unit-of-work snapshot.

    async def test_assinatura_checkout_invalida_retorna_http_400(self):
        class RequestStub:
            async def body(self):
                return b"synthetic-payload"

        invalid = stripe.error.SignatureVerificationError("invalid signature", "sig")
        with patch(
            "core.routers.stripe_webhooks.StripeService.verificar_webhook",
            side_effect=invalid,
        ):
            with self.assertRaises(HTTPException) as error:
                await stripe_webhooks.stripe_webhook(RequestStub(), "invalid")
        self.assertEqual(error.exception.status_code, 400)

    async def test_checkout_async_pago_e_processado_para_retentativa_pos_unpaid(self):
        class RequestStub:
            async def body(self):
                return b"synthetic-payload"

        event = stripe.Event.construct_from(
            {
                "id": "evt_test_synthetic",
                "type": "checkout.session.async_payment_succeeded",
                "data": {"object": {"id": "cs_test_synthetic"}},
            },
            None,
        )
        stripe_session = event["data"]["object"]
        self.assertFalse(isinstance(stripe_session, dict))
        with (
            patch(
                "core.routers.stripe_webhooks.StripeService.verificar_webhook",
                return_value=event,
            ),
            patch(
                "core.routers.stripe_webhooks._handle_checkout_completed",
                new=AsyncMock(return_value=True),
            ) as handler,
        ):
            response = await stripe_webhooks.stripe_webhook(RequestStub(), "valid")
        self.assertEqual(response, {"status": "ok"})
        handler.assert_awaited_once_with({"id": "cs_test_synthetic"})


class AuthServiceInitialStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_tenant_for_user_nao_libera_plano_pago_sem_trial(self):
        plan = _plan(is_free=False, tem_trial=False)
        user = SimpleNamespace(email="owner@example.test", nome_completo="Owner", username="owner")
        session = FakeSession(results=[Result(value=plan), Result(), Result(value=user)])
        service = AuthService(session)
        service.generate_token_for_tenant = AsyncMock(return_value="synthetic-token")

        response = await service.create_tenant_for_user(
            uuid.uuid4(), "Fazenda Nova", plan.id
        )

        tenant = next(value for value in session.added if isinstance(value, Tenant))
        assinatura = next(value for value in session.added if isinstance(value, AssinaturaTenant))
        self.assertEqual(assinatura.status, "PENDENTE_PAGAMENTO")
        self.assertFalse(tenant.ativo)
        self.assertEqual(response["access_token"], "synthetic-token")


if __name__ == "__main__":
    unittest.main()
