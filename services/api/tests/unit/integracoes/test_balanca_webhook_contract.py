from __future__ import annotations

import base64
import hashlib
import hmac
import time
from uuid import UUID, uuid4

import pytest
from integracoes.balanca.schemas import BalancaEventEnvelope
from integracoes.balanca.webhook import WebhookIngestionError, to_domain_event, verify_signature


def _envelope() -> BalancaEventEnvelope:
    tenant_id = uuid4()
    return BalancaEventEnvelope(
        event_id=uuid4(), idempotency_key="capture:abc", capture_id="abc",
        event_type="balanca.pesagem.concluida.v1", event_version="v1",
        occurred_at="2026-08-28T12:00:00Z", received_at="2026-08-28T12:00:01Z",
        account_id=uuid4(), client_system="deepfarms", client_tenant_id=str(tenant_id),
        correlation_id="correlation-1", external_reference="pecuaria:animal:" + str(uuid4()),
        entity_id=uuid4(), payload={"peso_liquido_kg": "10"},
    )


def test_signature_covers_method_path_timestamp_and_raw_body() -> None:
    body = b'{"event_id":"x"}'
    timestamp = str(int(time.time()))
    secret = "shared-secret"
    message = b"\n".join((b"POST", b"/api/v1/integracoes/balanca/events", timestamp.encode(), body))
    digest = base64.b64encode(hmac.new(secret.encode(), message, hashlib.sha256).digest()).decode()
    headers = {
        "X-TARA-Timestamp": timestamp,
        "X-TARA-Signature": "sha256=" + digest,
        "X-TARA-Event-Id": str(uuid4()),
    }
    with pytest.raises(WebhookIngestionError) as error:
        verify_signature(body + b"tampered", headers, "/api/v1/integracoes/balanca/events", secret, 300)
    assert error.value.status_code == 401


def test_envelope_translates_to_internal_event_and_preserves_metadata() -> None:
    envelope = _envelope()
    event = to_domain_event(envelope)
    assert event.tenant_id == UUID(envelope.client_tenant_id)
    assert event.event_id == envelope.event_id
    assert event.metadata["external_reference"] == envelope.external_reference
