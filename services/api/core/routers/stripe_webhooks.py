"""
Webhook handler para eventos Stripe.

Registra: POST /stripe/webhook

Eventos tratados:
- checkout.session.completed → ativa tenant + assinatura + converte lead
"""
import stripe
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from pydantic import BaseModel
from core.dependencies import require_permission
from sqlalchemy import select
from datetime import datetime, timezone
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

    if event["type"] in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        session = event["data"]["object"]
        if hasattr(session, "to_dict"):
            session = session.to_dict()
        processed = await _handle_checkout_completed(session)
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


async def _handle_checkout_completed(session: dict) -> bool:
    """Activate a subscription only after paid checkout or an eligible trial/free flow."""
    payment_status = session.get("payment_status")
    if payment_status == "unpaid":
        return False
    if payment_status not in {"paid", "no_payment_required"}:
        raise HTTPException(status_code=400, detail="Status de pagamento do checkout inválido")

    tenant_id, assinatura_id, plano_id = _checkout_ids(session.get("metadata") or {})
    stripe_subscription_id = _checkout_subscription_id(session)
    async with async_session_maker() as db:
        try:
            tenant = await db.get(Tenant, tenant_id)
            assinatura = await db.get(AssinaturaTenant, assinatura_id)
            plano = await db.get(PlanoAssinatura, plano_id)
            if not tenant or not assinatura or not plano:
                raise HTTPException(status_code=500, detail="Entidade do checkout ainda não foi persistida")
            if (
                assinatura.tenant_id != tenant_id
                or assinatura.plano_id != plano_id
                or assinatura.tipo_assinatura != "TENANT"
            ):
                raise HTTPException(status_code=400, detail="Vínculo da assinatura no checkout é inválido")
            if assinatura.stripe_subscription_id not in (None, stripe_subscription_id):
                raise HTTPException(status_code=409, detail="Assinatura já vinculada a outro registro Stripe")

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
            tenant.ativo = True
            tenant.activation_token = None
            tenant.activation_expires_at = None
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
