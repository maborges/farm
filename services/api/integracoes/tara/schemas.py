"""Contratos públicos da integração HTTP com a Plataforma TARA."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class TaraConfigUpsert(BaseModel):
    """Dados persistidos para conectar uma Conta TARA."""

    base_url: HttpUrl
    client_id: str = Field(min_length=1, max_length=160)
    client_secret: str | None = Field(default=None, min_length=1, max_length=512)
    client_system: str | None = Field(default=None, min_length=1, max_length=80)
    client_tenant_id: str | None = Field(default=None, min_length=1, max_length=160)


class TaraConfigResponse(BaseModel):
    """Configuração TARA sem materializar o segredo."""

    id: int
    tenant_id: str
    base_url: str
    client_id: str
    client_secret_configured: bool
    client_system: str | None = None
    client_tenant_id: str | None = None
    tara_client_id: str | None = None
    status: str


class TaraOrderCreate(BaseModel):
    """Ordem criada pelo sistema consumidor."""

    client_system: str = Field(min_length=1, max_length=80)
    client_tenant_id: str = Field(min_length=1, max_length=160)
    external_reference: str = Field(min_length=1, max_length=160)
    correlation_id: str = Field(min_length=1, max_length=160)
    subject_type: Literal["VEICULO", "ANIMAL"]
    tipo_pesagem: str = Field(min_length=1, max_length=60)
    contexto: dict[str, Any] = Field(default_factory=dict)


class TaraClientRegistration(BaseModel):
    """Identidade idempotente do sistema consumidor dentro da Conta."""

    sistema_cliente: str = Field(min_length=1, max_length=80)
    tenant_cliente_id: str = Field(min_length=1, max_length=160)
    nome_exibicao: str = Field(min_length=1, max_length=160)


class TaraOperatorCreate(BaseModel):
    """Projeção mínima de operador enviada pelo sistema cliente."""

    external_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    status: Literal["ATIVO", "INATIVO", "REVOGADO"] = "ATIVO"


class TaraWeighingPage(BaseModel):
    """Página opaca de pesagens retornada pela TARA."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
