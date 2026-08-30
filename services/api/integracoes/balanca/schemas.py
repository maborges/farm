from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BalancaExternalReference(BaseModel):
    """Identidade da operação no sistema consumidor da Balança."""

    client_system: str = Field(min_length=1, max_length=80)
    client_tenant_id: str = Field(min_length=1, max_length=120)
    external_reference: str = Field(min_length=1, max_length=160)
    correlation_id: str = Field(min_length=1, max_length=160)


class BalancaOrderRequest(BalancaExternalReference):
    """Contrato para solicitar uma ordem na Plataforma Balança."""

    subject_type: Literal["VEICULO", "ANIMAL"]
    tipo_pesagem: Literal[
        "UNICA",
        "DUPLA",
        "DUPLA_ENTRADA_DESCARGA",
        "DUPLA_SAIDA_CARREGAMENTO",
    ]
    contexto: dict[str, Any] = Field(default_factory=dict)
    data_agendada: datetime | None = None


class BalancaEventEnvelope(BaseModel):
    """Envelope versionado usado por API, webhook e arquivo."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=180)
    capture_id: str = Field(min_length=1, max_length=120)
    event_type: Literal["balanca.pesagem.concluida.v1"]
    event_version: Literal["v1"]
    occurred_at: datetime
    received_at: datetime
    account_id: UUID
    client_system: str = Field(min_length=1, max_length=80)
    client_tenant_id: str = Field(min_length=1, max_length=120)
    correlation_id: str = Field(min_length=1, max_length=160)
    external_reference: str = Field(min_length=1, max_length=160)
    entity_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)


class BalancaOperatorLink(BaseModel):
    """Vínculo opcional entre operador da Balança e pessoa do cliente."""

    operador_balanca_id: UUID
    pessoa_cliente_id: UUID | None = None
