"""
Webhook handler para eventos Stripe.

Registra: POST /stripe/webhook

Eventos tratados:
- checkout.session.completed / checkout.session.async_payment_succeeded → ativa tenant + assinatura + vincula stripe_subscription_id
- invoice.paid / invoice.payment_succeeded → renova ciclo da assinatura recorrente e registra fatura PAGA
- invoice.payment_failed → marca fatura como VENCIDA e suspende assinatura/tenant por inadimplência
- customer.subscription.updated / customer.subscription.deleted → sincroniza status (ATIVA, SUSPENSA, CANCELADA)
"""
from decimal import Decimal
import stripe
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from pydantic import BaseModel
from core.dependencies import require_permission
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import uuid
from loguru import logger

from core.database import async_session_maker
from core.models.tenant import Tenant
from core.models.billing import AssinaturaTenant, Fatura, PlanoAssinatura
from core.models.crm import LeadCRM
from core.services.stripe_service import StripeService

router = APIRouter(prefix="/stripe", tags=["Stripe — Webhooks"])


class SyncSessionRequest(BaseModel):
    session_id: str | None = None
    payment_intent_id: str | None = None


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Cabeçalho Stripe-Signature ausente")
    payload = await request.body()

    stripe_svc = StripeService()
    try:
        event = stripe_svc.verificar_webhook(payload, stripe_signature)
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook Stripe rejeitado: assinatura inválida")
        raise HTTPException(status_code=400, detail="Assinatura Stripe inválida")
    except ValueError as e:
        logger.warning(f"Webhook Stripe inválido: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    obj = event["data"]["object"]
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()

    if event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        processed = await _handle_checkout_completed(obj)
        if not processed:
            return {"status": "ignored"}

    elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        processed = await _handle_invoice_paid(obj)
        if not processed:
            return {"status": "ignored"}

    elif event_type == "invoice.payment_failed":
        processed = await _handle_invoice_payment_failed(obj)
        if not processed:
            return {"status": "ignored"}

    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        processed = await _handle_subscription_status_changed(obj, event_type)
        if not processed:
            return {"status": "ignored"}

    return {"status": "ok"}


def _checkout_ids(metadata: dict) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Parse checkout metadata IDs without allowing malformed references.

    Args:
        metadata: Signed checkout session metadata.

    Returns:
        Tenant, subscription and plan UUIDs.

    Raises:
        HTTPException: When any required metadata ID is missing or malformed.
    """
    try:
        return tuple(
            uuid.UUID(str(metadata[key]))
            for key in ("tenant_id", "assinatura_id", "plano_id")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Metadados de checkout inválidos") from exc


def _checkout_subscription_id(session: dict) -> str:
    """Resolve the subscription ID from a signed Stripe Checkout Session.

    Args:
        session: Signed Checkout Session event object.

    Returns:
        Stripe subscription identifier.

    Raises:
        HTTPException: When session mode or subscription ID is invalid.
    """
    subscription = session.get("subscription")
    if isinstance(subscription, dict):
        subscription = subscription.get("id")
    if session.get("mode") != "subscription" or not isinstance(subscription, str) or not subscription:
        raise HTTPException(status_code=400, detail="Checkout não corresponde a uma assinatura")
    return subscription


async def _convert_approved_lead(db, tenant_id: uuid.UUID) -> None:
    """Convert the approved CRM lead associated with a paid tenant.

    Args:
        db: Active webhook database session.
        tenant_id: Tenant associated with the approved lead.

    Returns:
        None.

    Raises:
        Exception: Database failures are propagated to the transaction handler.
    """
    stmt = select(LeadCRM).where(LeadCRM.tenant_convertido_id == tenant_id)
    lead = (await db.execute(stmt)).scalar_one_or_none()
    if lead and lead.status == "aprovado":
        lead.status = "convertido"
        lead.data_conversao = datetime.now(timezone.utc).date()


async def _handle_prorata_upgrade_checkout(session: dict) -> bool:
    """Processa pagamento avulso (pro-rata) de upgrade de plano via Stripe Checkout."""
    from core.models.plan_changes import MudancaPlano
    from core.services.mudanca_plano_service import MudancaPlanoService

    payment_status = session.get("payment_status")
    if payment_status == "unpaid":
        return False
    if payment_status != "paid":
        raise HTTPException(status_code=400, detail="Status de pagamento pro-rata inválido")

    metadata = session.get("metadata") or {}
    try:
        tenant_id = uuid.UUID(str(metadata["tenant_id"]))
        assinatura_id = uuid.UUID(str(metadata["assinatura_id"]))
        mudanca_id = uuid.UUID(str(metadata["mudanca_plano_id"]))
        fatura_id = uuid.UUID(str(metadata["fatura_id"])) if metadata.get("fatura_id") else None
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Metadata pro-rata inválida no checkout") from exc

    async with async_session_maker() as db:
        try:
            mudanca = await db.get(MudancaPlano, mudanca_id)
            assinatura = await db.get(AssinaturaTenant, assinatura_id)
            if not mudanca or not assinatura or mudanca.assinatura_id != assinatura.id or assinatura.tenant_id != tenant_id:
                raise HTTPException(status_code=400, detail="Vínculo da mudança pro-rata inválido")

            if mudanca.status == "aplicado":
                return True

            if fatura_id:
                fatura = await db.get(Fatura, fatura_id)
                if fatura and fatura.assinatura_id == assinatura.id and fatura.status == "ABERTA":
                    fatura.status = "PAGA"
                    fatura.data_aprovacao_rejeicao = datetime.now(timezone.utc)
            else:
                faturas = await _load_subscription_invoices(db, tenant_id, assinatura_id)
                for fatura in faturas:
                    if fatura.status == "ABERTA":
                        fatura.status = "PAGA"
                        fatura.data_aprovacao_rejeicao = datetime.now(timezone.utc)
                        break

            mudanca_svc = MudancaPlanoService(db, tenant_id)
            await mudanca_svc._aplicar_mudanca(mudanca)
            await db.commit()
            logger.info(f"Upgrade pro-rata Stripe aplicado: mudança {mudanca.id}")
            return True
        except HTTPException:
            await _rollback_webhook(db)
            raise
        except Exception as exc:
            await _rollback_webhook(db)
            logger.error(f"Falha persistindo upgrade pro-rata Stripe ({mudanca_id}): {exc}")
            raise HTTPException(
                status_code=500,
                detail="Falha ao persistir pagamento pro-rata; o webhook deve ser repetido.",
            ) from exc


async def _handle_checkout_completed(session: dict) -> bool:
    """Activate a subscription only after paid checkout or an eligible trial/free flow."""
    metadata = session.get("metadata") or {}
    if session.get("mode") == "payment" and metadata.get("tipo") == "mudanca_plano_prorata":
        return await _handle_prorata_upgrade_checkout(session)

    payment_status = session.get("payment_status")
    if payment_status == "unpaid":
        return False
    if payment_status not in {"paid", "no_payment_required"}:
        raise HTTPException(status_code=400, detail="Status de pagamento do checkout inválido")

    tenant_id, assinatura_id, plano_id = _checkout_ids(metadata)
    stripe_subscription_id = _checkout_subscription_id(session)
    async with async_session_maker() as db:
        try:
            tenant = await db.get(Tenant, tenant_id)
            assinatura = await db.get(AssinaturaTenant, assinatura_id)
            plano = await db.get(PlanoAssinatura, plano_id)
            if not tenant or not assinatura or not plano:
                raise HTTPException(status_code=500, detail="Entidade do checkout ainda não foi persistida")
            if assinatura.tenant_id != tenant_id or assinatura.tipo_assinatura != "TENANT":
                raise HTTPException(status_code=400, detail="Vínculo da assinatura no checkout é inválido")
            if assinatura.plano_id != plano_id:
                from core.models.plan_changes import MudancaPlano

                mudanca_match = (
                    await db.execute(
                        select(MudancaPlano).where(
                            MudancaPlano.assinatura_id == assinatura.id,
                            MudancaPlano.plano_destino_id == plano_id,
                            MudancaPlano.status == "pendente_pagamento",
                        )
                    )
                ).scalar_one_or_none()
                if not mudanca_match:
                    raise HTTPException(status_code=400, detail="Vínculo da assinatura no checkout é inválido")
            if assinatura.stripe_subscription_id not in (None, stripe_subscription_id):
                raise HTTPException(status_code=409, detail="Assinatura já vinculada a outro registro Stripe")

            if "usuarios_contratados" in (session.get("metadata") or {}):
                try:
                    assinatura.usuarios_contratados = int(session["metadata"]["usuarios_contratados"])
                except (TypeError, ValueError):
                    pass

            if payment_status == "no_payment_required":
                eligible = plano.is_free or (assinatura.status == "TRIAL" and plano.tem_trial)
                if not eligible:
                    await _rollback_webhook(db)
                    return False
                assinatura.stripe_subscription_id = stripe_subscription_id
                tenant.ativo = True
                tenant.activation_token = None
                tenant.activation_expires_at = None
                await db.commit()
                return True

            faturas = await _load_subscription_invoices(db, tenant_id, assinatura_id)
            already_processed = (
                assinatura.status == "ATIVA"
                and tenant.ativo
                and assinatura.stripe_subscription_id == stripe_subscription_id
                and any(fatura.status == "PAGA" for fatura in faturas)
            )
            if already_processed:
                return True

            abertas = [fatura for fatura in faturas if fatura.status == "ABERTA"]
            pagas = [fatura for fatura in faturas if fatura.status == "PAGA"]
            if len(abertas) > 1:
                raise HTTPException(status_code=500, detail="Fatura do checkout é ambígua")
            if abertas:
                abertas[0].status = "PAGA"
                abertas[0].data_aprovacao_rejeicao = datetime.now(timezone.utc)
            elif not pagas:
                raise HTTPException(status_code=500, detail="Fatura do checkout ainda não foi persistida")

            assinatura.stripe_subscription_id = stripe_subscription_id
            assinatura.status = "ATIVA"
            assinatura.data_bloqueio = None
            dias_ciclo = 365 if assinatura.ciclo_pagamento == "ANUAL" else 30
            assinatura.data_proxima_renovacao = datetime.now(timezone.utc) + timedelta(days=dias_ciclo)
            tenant.ativo = True
            tenant.activation_token = None
            tenant.activation_expires_at = None
            await _apply_pending_plan_change(db, assinatura)
            await _convert_approved_lead(db, tenant_id)
            await db.commit()
            logger.info("Checkout Stripe pago processado.")
            return True
        except HTTPException:
            await _rollback_webhook(db)
            raise
        except Exception as exc:
            await _rollback_webhook(db)
            logger.error("Falha persistindo checkout Stripe; o evento poderá ser repetido.")
            raise HTTPException(
                status_code=500,
                detail="Falha ao persistir o pagamento; o webhook deve ser repetido.",
            ) from exc


def _extract_subscription_id_from_invoice(invoice_obj: dict) -> str | None:
    """Extrai o ID da assinatura Stripe (sub_...) de um objeto Invoice."""
    sub = invoice_obj.get("subscription")
    if isinstance(sub, dict):
        sub = sub.get("id")
    if isinstance(sub, str) and sub:
        return sub
    return None


async def _apply_pending_plan_change(db, assinatura: AssinaturaTenant) -> None:
    """
    Se houver aditivo de novos acessos simultâneos ou upgrade de pacote pendente de pagamento
    (MudancaPlano com status='pendente_pagamento'), aplica automaticamente na assinatura ao confirmar o pagamento.
    """
    from core.models.plan_changes import MudancaPlano

    stmt = (
        select(MudancaPlano)
        .where(
            MudancaPlano.assinatura_id == assinatura.id,
            MudancaPlano.status == "pendente_pagamento",
        )
        .order_by(MudancaPlano.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    mudanca = res.scalar_one_or_none() if res else None
    if not mudanca or getattr(mudanca, "status", None) != "pendente_pagamento":
        return

    assinatura.plano_id = mudanca.plano_destino_id
    assinatura.usuarios_contratados = mudanca.usuarios_destino
    mudanca.status = "aplicado"
    mudanca.aplicado_em = datetime.now(timezone.utc)
    mudanca.aplicado_por_job = True


async def _handle_invoice_paid(invoice_obj: dict) -> bool:
    """
    Trata renovação recorrente paga no Stripe (invoice.paid / invoice.payment_succeeded).
    Dá continuidade automática ao contrato (status ATIVA, renova data_proxima_renovacao e quita fatura).
    """
    stripe_sub_id = _extract_subscription_id_from_invoice(invoice_obj)
    if not stripe_sub_id:
        return False

    agora = datetime.now(timezone.utc)
    amount_paid_cents = int(invoice_obj.get("amount_paid") or 0)
    valor_pago = (Decimal(amount_paid_cents) / Decimal(100)).quantize(Decimal("0.01"))

    async with async_session_maker() as db:
        try:
            stmt = select(AssinaturaTenant).where(
                AssinaturaTenant.stripe_subscription_id == stripe_sub_id
            )
            assinatura = (await db.execute(stmt)).scalar_one_or_none()
            if not assinatura:
                return False

            tenant = await db.get(Tenant, assinatura.tenant_id)
            faturas = await _load_subscription_invoices(db, assinatura.tenant_id, assinatura.id)
            pendentes = [f for f in faturas if f.status in {"ABERTA", "VENCIDA", "REJEITADA"}]

            if pendentes:
                pendentes[0].status = "PAGA"
                pendentes[0].data_aprovacao_rejeicao = agora
                if valor_pago > Decimal("0.00"):
                    pendentes[0].valor = valor_pago
            elif valor_pago > Decimal("0.00"):
                nova_fatura = Fatura(
                    id=uuid.uuid4(),
                    tenant_id=assinatura.tenant_id,
                    assinatura_id=assinatura.id,
                    valor=valor_pago,
                    data_vencimento=agora,
                    status="PAGA",
                    data_aprovacao_rejeicao=agora,
                )
                db.add(nova_fatura)

            dias_ciclo = 365 if assinatura.ciclo_pagamento == "ANUAL" else 30
            assinatura.status = "ATIVA"
            assinatura.data_bloqueio = None
            assinatura.data_proxima_renovacao = agora + timedelta(days=dias_ciclo)
            if tenant:
                tenant.ativo = True
            await _apply_pending_plan_change(db, assinatura)

            await db.commit()
            logger.info(f"Renovação Stripe paga para assinatura {assinatura.id} ({stripe_sub_id})")
            return True
        except Exception as exc:
            await _rollback_webhook(db)
            logger.error(f"Falha ao processar invoice.paid ({stripe_sub_id}): {exc}")
            raise HTTPException(status_code=500, detail="Falha ao processar renovação Stripe") from exc


async def _handle_invoice_payment_failed(invoice_obj: dict) -> bool:
    """
    Trata inadimplência na cobrança recorrente do Stripe (invoice.payment_failed).
    Marca a fatura como VENCIDA e suspende a assinatura/tenant por falta de pagamento.
    """
    stripe_sub_id = _extract_subscription_id_from_invoice(invoice_obj)
    if not stripe_sub_id:
        return False

    agora = datetime.now(timezone.utc)
    amount_due_cents = int(invoice_obj.get("amount_due") or 0)
    valor_devido = (Decimal(amount_due_cents) / Decimal(100)).quantize(Decimal("0.01"))

    async with async_session_maker() as db:
        try:
            stmt = select(AssinaturaTenant).where(
                AssinaturaTenant.stripe_subscription_id == stripe_sub_id
            )
            assinatura = (await db.execute(stmt)).scalar_one_or_none()
            if not assinatura:
                return False

            tenant = await db.get(Tenant, assinatura.tenant_id)
            faturas = await _load_subscription_invoices(db, assinatura.tenant_id, assinatura.id)
            abertas = [f for f in faturas if f.status == "ABERTA"]

            if abertas:
                abertas[0].status = "VENCIDA"
            elif valor_devido > Decimal("0.00"):
                fatura_vencida = Fatura(
                    id=uuid.uuid4(),
                    tenant_id=assinatura.tenant_id,
                    assinatura_id=assinatura.id,
                    valor=valor_devido,
                    data_vencimento=agora,
                    status="VENCIDA",
                )
                db.add(fatura_vencida)

            assinatura.status = "SUSPENSA"
            assinatura.data_bloqueio = agora
            if tenant:
                tenant.ativo = False

            await db.commit()
            logger.warning(f"Inadimplência Stripe: assinatura {assinatura.id} ({stripe_sub_id}) suspensa")
            return True
        except Exception as exc:
            await _rollback_webhook(db)
            logger.error(f"Falha ao processar invoice.payment_failed ({stripe_sub_id}): {exc}")
            raise HTTPException(status_code=500, detail="Falha ao processar falha de pagamento Stripe") from exc


async def _handle_subscription_status_changed(sub_obj: dict, event_type: str) -> bool:
    """
    Sincroniza alterações de status do contrato no Stripe
    (customer.subscription.updated / customer.subscription.deleted).
    """
    stripe_sub_id = sub_obj.get("id")
    if not isinstance(stripe_sub_id, str) or not stripe_sub_id:
        return False

    stripe_status = str(sub_obj.get("status") or "").lower()
    agora = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        try:
            stmt = select(AssinaturaTenant).where(
                AssinaturaTenant.stripe_subscription_id == stripe_sub_id
            )
            assinatura = (await db.execute(stmt)).scalar_one_or_none()
            if not assinatura:
                return False

            tenant = await db.get(Tenant, assinatura.tenant_id)

            if event_type == "customer.subscription.deleted" or stripe_status == "canceled":
                assinatura.status = "CANCELADA"
                assinatura.data_bloqueio = agora
                if tenant:
                    tenant.ativo = False
            elif stripe_status in {"past_due", "unpaid", "incomplete_expired"}:
                assinatura.status = "SUSPENSA"
                assinatura.data_bloqueio = agora
                if tenant:
                    tenant.ativo = False
            elif stripe_status == "active":
                assinatura.status = "ATIVA"
                assinatura.data_bloqueio = None
                if tenant:
                    tenant.ativo = True

            await db.commit()
            return True
        except Exception as exc:
            await _rollback_webhook(db)
            logger.error(f"Falha ao sincronizar subscription ({stripe_sub_id}): {exc}")
            raise HTTPException(status_code=500, detail="Falha ao sincronizar assinatura Stripe") from exc


async def _load_subscription_invoices(db, tenant_id, assinatura_id) -> list[Fatura]:
    """Load invoices constrained to the signed tenant and subscription IDs.

    Args:
        db: Active webhook database session.
        tenant_id: Validated tenant UUID.
        assinatura_id: Validated subscription UUID.

    Returns:
        Matching invoice rows.

    Raises:
        Exception: Database failures are propagated to the transaction handler.
    """
    stmt = select(Fatura).where(
        Fatura.tenant_id == tenant_id,
        Fatura.assinatura_id == assinatura_id,
    )
    return (await db.execute(stmt)).scalars().all()


async def _rollback_webhook(db) -> None:
    """Rollback webhook writes without exposing database error details.

    Args:
        db: Active webhook database session.

    Returns:
        None.

    Raises:
        None: Rollback errors are suppressed so the original failure is preserved.
    """
    try:
        await db.rollback()
    except Exception:
        logger.error("Rollback do webhook Stripe também falhou.")


@router.post(
    "/sync-session",
    summary="Sincronizar sessão Stripe manualmente",
    dependencies=[Depends(require_permission("backoffice:billing:manage"))],
)
async def sync_stripe_session(body: SyncSessionRequest):
    """
    Busca uma checkout session no Stripe pelo ID e reprocessa o evento
    manualmente. Útil quando o webhook não foi recebido.
    """
    if not body.session_id and not body.payment_intent_id:
        raise HTTPException(status_code=422, detail="Informe session_id ou payment_intent_id")

    stripe_svc = StripeService()
    if not stripe_svc.stripe_configured():
        raise HTTPException(status_code=503, detail="Stripe não configurado neste ambiente")

    try:
        if body.session_id:
            session = stripe.checkout.Session.retrieve(body.session_id)
        else:
            # Busca a sessão pelo Payment Intent
            sessions = stripe.checkout.Session.list(payment_intent=body.payment_intent_id, limit=1)
            if not sessions.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Nenhuma checkout session encontrada para o Payment Intent {body.payment_intent_id}",
                )
            session = sessions.data[0]
    except HTTPException:
        raise
    except stripe.InvalidRequestError as e:
        raise HTTPException(status_code=404, detail=f"Registro não encontrado no Stripe: {e}")
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar Stripe: {e}")

    if getattr(session, "payment_status", None) not in ("paid", "no_payment_required"):
        raise HTTPException(
            status_code=400,
            detail=f"Sessão ainda não foi paga (status: {session.get('payment_status')})",
        )

    # Normaliza para dict pois _handle_checkout_completed espera dict com .get()
    session_dict = {
        "id": session.id,
        "mode": session.mode,
        "subscription": session.subscription,
        "payment_status": session.payment_status,
        "metadata": session.metadata._to_dict_recursive() if session.metadata else {},
    }
    processed = await _handle_checkout_completed(session_dict)
    if not processed:
        raise HTTPException(status_code=409, detail="Checkout ainda não está elegível para ativação")
    logger.info("Sincronização manual de checkout Stripe concluída.")
    return {"status": "ok", "session_id": session.id}
