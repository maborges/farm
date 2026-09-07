from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from events import DomainEvent, enqueue_domain_event
from integracoes.models import BalancaInboundEvent

from .schemas import BalancaEventEnvelope
from .webhook_credentials import resolve_webhook_secret


@dataclass(frozen=True)
class WebhookDelivery:
    """Transport-neutral representation of an incoming webhook request."""

    body: bytes
    headers: Mapping[str, str]
    path: str


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of durable ingestion, including duplicate detection."""

    accepted: bool


class WebhookIngestionError(Exception):
    """Expected contract error that the HTTP adapter maps to a status code."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def ingest_event(
    delivery: WebhookDelivery, session: AsyncSession, config: Settings
) -> IngestionResult:
    """Authenticate, validate, and durably accept one TARA webhook delivery."""
    account_id = _header_account_id(delivery.headers)
    envelope = _parse_envelope(delivery.body)
    try:
        secret = await resolve_webhook_secret(session, envelope, account_id, config)
    except ValueError as exc:
        raise WebhookIngestionError(400, str(exc)) from exc
    verify_signature(
        delivery.body, delivery.headers, delivery.path, secret,
        config.balanca_webhook_max_skew_seconds,
    )
    _validate_headers(delivery.headers, envelope, account_id)
    return IngestionResult(accepted=await accept_event(session, envelope))


def _parse_envelope(body: bytes) -> BalancaEventEnvelope:
    try:
        return BalancaEventEnvelope.model_validate_json(body)
    except ValidationError as exc:
        raise WebhookIngestionError(422, "Envelope TARA inválido") from exc


def _header_account_id(headers: Mapping[str, str]) -> UUID:
    value = _header(headers, "x-tara-account-id")
    try:
        return UUID(value)
    except ValueError as exc:
        raise WebhookIngestionError(401, "Conta TARA ausente ou inválida") from exc


def _validate_headers(headers: Mapping[str, str], envelope: BalancaEventEnvelope, account_id: UUID) -> None:
    if _header(headers, "x-tara-event-id") != str(envelope.event_id):
        raise WebhookIngestionError(400, "event_id divergente do header")
    if envelope.account_id != account_id:
        raise WebhookIngestionError(400, "account_id divergente do header")


def verify_signature(
    body: bytes, headers: Mapping[str, str], path: str, secret: str, max_skew: int
) -> None:
    """Validate TARA's timestamped HMAC signature over the raw HTTP request."""
    timestamp = _header(headers, "x-tara-timestamp")
    signature = _header(headers, "x-tara-signature")
    event_id = _header(headers, "x-tara-event-id")
    if not secret or not timestamp or not signature.startswith("sha256=") or not event_id:
        raise WebhookIngestionError(401, "Assinatura TARA ausente")
    try:
        timestamp_value = int(timestamp)
        supplied = base64.b64decode(signature.removeprefix("sha256="), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise WebhookIngestionError(401, "Assinatura TARA inválida") from exc
    if abs(time.time() - timestamp_value) > max_skew:
        raise WebhookIngestionError(401, "Timestamp TARA expirado")
    path = path or "/"
    message = b"\n".join((b"POST", path.encode(), timestamp.encode(), body))
    expected = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, supplied):
        raise WebhookIngestionError(401, "Assinatura TARA inválida")
    try:
        UUID(event_id)
    except ValueError as exc:
        raise WebhookIngestionError(400, "X-TARA-Event-Id inválido") from exc


def to_domain_event(envelope: BalancaEventEnvelope) -> DomainEvent:
    """Translate the public TARA envelope into the AgroSaaS event model."""
    tenant_id = _uuid_or_bad_request(envelope.client_tenant_id, "client_tenant_id")
    correlation_id = _optional_uuid(envelope.correlation_id)
    return DomainEvent(
        event_id=envelope.event_id,
        tenant_id=tenant_id,
        domain="OPERACAO_PESAGEM",
        event_type=envelope.event_type,
        source_type="tara",
        entity_type="pesagem",
        entity_id=envelope.entity_id,
        occurred_at=envelope.occurred_at,
        correlation_id=correlation_id,
        metadata=envelope.model_dump(mode="json"),
    )


async def accept_event(session: AsyncSession, envelope: BalancaEventEnvelope) -> bool:
    """Persist one TARA event and enqueue its business processing."""
    tenant_id = _uuid_or_bad_request(envelope.client_tenant_id, "client_tenant_id")
    await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": str(tenant_id)})
    existing = await session.get(BalancaInboundEvent, envelope.event_id)
    if existing:
        return False
    session.add(BalancaInboundEvent(
        event_id=envelope.event_id, tenant_id=tenant_id, account_id=envelope.account_id,
        event_type=envelope.event_type, idempotency_key=envelope.idempotency_key,
        payload=envelope.model_dump(mode="json"), received_at=envelope.received_at,
    ))
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return False
    await enqueue_domain_event(
        to_domain_event(envelope), session=session, commit=False
    )
    inbound = await session.get(BalancaInboundEvent, envelope.event_id)
    inbound.processed_at = datetime.now(timezone.utc)
    await session.commit()
    return True


def _uuid_or_bad_request(value: str, field: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise WebhookIngestionError(400, f"{field} inválido") from exc


def _optional_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _header(headers: Mapping[str, str], name: str) -> str:
    return headers.get(name.lower(), "") or headers.get(name, "")
