from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from integracoes.balanca import BalancaEventEnvelope, BalancaOrderRequest
from integracoes.balanca.events import completed_weighing_metadata


def test_ordem_balanca_exige_referencia_externa_e_correlacao() -> None:
    with pytest.raises(ValidationError):
        BalancaOrderRequest(
            client_system="agrosaas",
            client_tenant_id="tenant-a",
            external_reference="",
            correlation_id="corr-1",
            subject_type="VEICULO",
            tipo_pesagem="UNICA",
        )


def test_evento_balanca_tem_envelope_versionado() -> None:
    tenant_id = uuid4()
    event = BalancaEventEnvelope(
        event_id=uuid4(),
        idempotency_key="pesagem-1-concluida",
        capture_id="capture-1",
        event_type="balanca.pesagem.concluida.v1",
        event_version="v1",
        occurred_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        account_id=uuid4(),
        client_system="agrosaas",
        client_tenant_id=str(tenant_id),
        correlation_id="corr-1",
        external_reference="compra-1",
        entity_id=uuid4(),
        payload={"peso_liquido_kg": "100.000"},
    )

    assert event.event_version == "v1"
    assert event.payload["peso_liquido_kg"] == "100.000"


def test_referencia_externa_e_payload_sao_normalizados_para_consumidores() -> None:
    event = type(
        "ExternalEvent",
        (),
        {
            "external_reference": "operacional:compra:" + str(uuid4()),
            "payload": {"peso_aferido_kg": "1500.000", "peso_tara_kg": "500.000"},
            "metadata": {},
        },
    )()

    metadata = completed_weighing_metadata(event)

    assert metadata["origem_tipo"] == "COMPRA"
    assert metadata["peso_bruto_kg"] == "1500.000"
    assert metadata["peso_tara_kg"] == "500.000"
