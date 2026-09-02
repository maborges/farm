from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.models import BalancaWebhookCredential

from .webhook import WebhookDelivery, WebhookIngestionError, ingest_event
from .webhook_credentials import upsert_webhook_credential

router = APIRouter(prefix="/balanca", tags=["Integração TARA"])


@router.post("/events", status_code=204)
async def receive_event(request: Request, session: AsyncSession = Depends(get_session)) -> None:
    """Accept a signed TARA event after durable, idempotent processing."""
    delivery = WebhookDelivery(
        body=await request.body(),
        headers={key.lower(): value for key, value in request.headers.items()},
        path=request.url.path,
    )
    try:
        await ingest_event(delivery, session, settings)
    except WebhookIngestionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


class BalancaWebhookCredentialRequest(BaseModel):
    account_id: UUID
    secret: str = Field(min_length=32)


class BalancaWebhookCredentialResponse(BaseModel):
    account_id: UUID
    status: str
    rotated_at: datetime | None


@router.put(
    "/webhook-credentials",
    response_model=BalancaWebhookCredentialResponse,
    dependencies=[Depends(require_tenant_permission("integrations:configure"))],
)
async def configure_webhook_credential(
    data: BalancaWebhookCredentialRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> BalancaWebhookCredentialResponse:
    """Persist or rotate the HMAC secret for a TARA account."""
    credential = await upsert_webhook_credential(session, tenant_id, data.account_id, data.secret)
    await session.commit()
    return BalancaWebhookCredentialResponse.model_validate(credential, from_attributes=True)


@router.get(
    "/webhook-credentials",
    response_model=list[BalancaWebhookCredentialResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def list_webhook_credentials(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[BalancaWebhookCredentialResponse]:
    result = await session.execute(select(BalancaWebhookCredential).where(
        BalancaWebhookCredential.tenant_id == tenant_id,
    ).order_by(BalancaWebhookCredential.balanca_account_id))
    return [BalancaWebhookCredentialResponse.model_validate(row, from_attributes=True) for row in result.scalars()]
