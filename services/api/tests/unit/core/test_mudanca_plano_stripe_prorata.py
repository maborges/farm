import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.auth import Usuario
from core.models.billing import AssinaturaTenant, Fatura, PlanoAssinatura
from core.models.plan_changes import MudancaPlano, PlanoPricing
from core.models.tenant import Tenant
from core.routers import stripe_webhooks
from core.services.mudanca_plano_service import MudancaPlanoService
from core.services.stripe_service import StripeService


@pytest.fixture
async def stripe_prorata_session():
    """Cria sessão SQLite em memória com tabelas mínimas de assinatura e mudança de plano."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [
        Tenant.__table__,
        Usuario.__table__,
        PlanoAssinatura.__table__,
        PlanoPricing.__table__,
        AssinaturaTenant.__table__,
        Fatura.__table__,
        MudancaPlano.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_criar_checkout_mudanca_prorata_cria_sessao_payment_em_centavos():
    """Garante que o checkout pro-rata usa mode='payment' e valor exato em centavos."""
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_prorata_123", url="https://checkout.stripe.com/pay/cs_prorata_123")

    svc = StripeService()
    with patch("core.services.stripe_service.stripe.api_key", "sk_test_123"), patch(
        "core.services.stripe_service.stripe.checkout.Session.create", side_effect=fake_create
    ):
        url = await svc.criar_checkout_mudanca_prorata(
            tenant_id=str(uuid.uuid4()),
            assinatura_id=str(uuid.uuid4()),
            mudanca_plano_id=str(uuid.uuid4()),
            plano_destino_id=str(uuid.uuid4()),
            nome_plano_destino="Médio Produtor",
            valor_reais=123.45,
            email="produtor@fazenda.com",
            fatura_id=str(uuid.uuid4()),
        )

    assert url == "https://checkout.stripe.com/pay/cs_prorata_123"
    assert captured["mode"] == "payment"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 12345
    assert captured["metadata"]["tipo"] == "mudanca_plano_prorata"


@pytest.mark.asyncio
async def test_gerar_checkout_stripe_prorata_e_webhook_aplica_mudanca(stripe_prorata_session):
    """Valida geração de checkout pro-rata para assinatura ativa e efetivação via webhook."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plano_origem_id = uuid.uuid4()
    plano_destino_id = uuid.uuid4()
    assinatura_id = uuid.uuid4()
    fatura_id = uuid.uuid4()
    mudanca_id = uuid.uuid4()

    async with stripe_prorata_session() as db:
        db.add(Tenant(id=tenant_id, nome="Fazenda Teste", email_responsavel="fin@fazenda.com", ativo=True))
        db.add(Usuario(id=user_id, email="fin@fazenda.com", username="fin_teste", ativo=True))
        db.add(
            PlanoAssinatura(
                id=plano_origem_id,
                nome="Pequeno Produtor",
                plan_tier="BASICO",
                preco_mensal=197.0,
                preco_anual=1891.0,
                limite_usuarios_minimo=1,
                limite_usuarios_maximo=5,
                ativo=True,
            )
        )
        db.add(
            PlanoAssinatura(
                id=plano_destino_id,
                nome="Médio Produtor",
                plan_tier="PROFISSIONAL",
                preco_mensal=497.0,
                preco_anual=4771.0,
                limite_usuarios_minimo=1,
                limite_usuarios_maximo=10,
                ativo=True,
            )
        )
        db.add(
            AssinaturaTenant(
                id=assinatura_id,
                tenant_id=tenant_id,
                plano_id=plano_origem_id,
                tipo_assinatura="TENANT",
                status="ATIVA",
                ciclo_pagamento="MENSAL",
                usuarios_contratados=1,
                stripe_subscription_id="sub_stripe_ativa_123",
                data_inicio=datetime.now(timezone.utc) - timedelta(days=15),
                data_proxima_renovacao=datetime.now(timezone.utc) + timedelta(days=15),
            )
        )
        db.add(
            Fatura(
                id=fatura_id,
                tenant_id=tenant_id,
                assinatura_id=assinatura_id,
                valor=Decimal("150.00"),
                data_vencimento=datetime.now(timezone.utc) + timedelta(days=3),
                status="ABERTA",
            )
        )
        mudanca = MudancaPlano(
            id=mudanca_id,
            tenant_id=tenant_id,
            assinatura_id=assinatura_id,
            plano_origem_id=plano_origem_id,
            usuarios_origem=1,
            plano_destino_id=plano_destino_id,
            usuarios_destino=2,
            tipo_mudanca="UPGRADE_PACOTE",
            valor_calculado=Decimal("300.00"),
            valor_proporcional=Decimal("150.00"),
            dias_restantes_ciclo=15,
            solicitado_por_usuario_id=user_id,
            status="pendente_pagamento",
        )
        db.add(mudanca)
        await db.commit()

        svc = MudancaPlanoService(db, tenant_id)
        with patch.object(
            StripeService,
            "criar_checkout_mudanca_prorata",
            return_value="https://checkout.stripe.com/pay/prorata_ok",
        ) as mock_checkout:
            url = await svc.gerar_checkout_stripe(mudanca)

        assert url == "https://checkout.stripe.com/pay/prorata_ok"
        assert mudanca.url_pagamento == "https://checkout.stripe.com/pay/prorata_ok"
        mock_checkout.assert_awaited_once()

    checkout_payload = {
        "id": "cs_prorata_ok",
        "mode": "payment",
        "payment_status": "paid",
        "metadata": {
            "tipo": "mudanca_plano_prorata",
            "tenant_id": str(tenant_id),
            "assinatura_id": str(assinatura_id),
            "mudanca_plano_id": str(mudanca_id),
            "plano_destino_id": str(plano_destino_id),
            "fatura_id": str(fatura_id),
        },
    }

    with patch.object(stripe_webhooks, "async_session_maker", stripe_prorata_session), patch.object(
        StripeService, "atualizar_assinatura_recorrente", return_value=True
    ) as mock_sync:
        handled = await stripe_webhooks._handle_checkout_completed(checkout_payload)

    assert handled is True
    mock_sync.assert_called_once()
    assert mock_sync.call_args.kwargs["cobrar_prorata_no_stripe"] is False

    async with stripe_prorata_session() as db:
        fatura_atualizada = await db.get(Fatura, fatura_id)
        mudanca_atualizada = await db.get(MudancaPlano, mudanca_id)
        assinatura_atualizada = await db.get(AssinaturaTenant, assinatura_id)

        assert fatura_atualizada.status == "PAGA"
        assert mudanca_atualizada.status == "aplicado"
        assert assinatura_atualizada.plano_id == plano_destino_id
        assert assinatura_atualizada.usuarios_contratados == 2
