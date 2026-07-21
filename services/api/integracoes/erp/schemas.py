"""Contratos HTTP para políticas canônicas de sincronização ERP."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ErpPolicyMode = Literal["MANUAL", "AGENDADO", "PULL"]
ErpPolicyPriority = Literal["LOW", "NORMAL", "HIGH", "URGENT"]
ErpRecordScope = Literal["LINKED_ONLY", "ALL_EXTERNAL"]


class ErpPersonRecord(BaseModel):
    """Pessoa externa normalizada sem expor detalhes específicos do provider."""

    external_id: str = Field(min_length=1, max_length=255)
    tipo: Literal["PF", "PJ"]
    nome_exibicao: str = Field(min_length=1, max_length=200)
    cpf: str | None = None
    cnpj: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    inscricao_estadual: str | None = None
    email: str | None = None
    telefone: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    ativo_no_erp: bool = True


class ErpPersonImportRequest(BaseModel):
    """Confirmação de criação ou atualização de Pessoa a partir do ERP."""

    external_id: str = Field(min_length=1, max_length=255)
    pessoa_id: str | None = None
    base_legal: str = Field(default="CONTRATO", min_length=1, max_length=30)
    relacionamento_tipo_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)


class ErpPersonLookupRequest(BaseModel):
    """Identificador informado pelo usuário para pré-visualização no ERP."""

    external_id: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(str_strip_whitespace=True)


class ErpPersonImportResponse(BaseModel):
    """Resultado seguro da promoção do registro externo."""

    pessoa_id: str
    external_id: str
    created: bool
    provider_slug: str
    message: str


class ErpSyncPolicyUpdate(BaseModel):
    """Campos operacionais editáveis de uma política por fluxo."""

    mode: ErpPolicyMode
    record_scope: ErpRecordScope = "LINKED_ONLY"
    ativa: bool = True
    prioridade: ErpPolicyPriority = "NORMAL"
    retry_ativo: bool = True
    retry_limite: int = Field(default=3, ge=0, le=10)
    batch_size: int = Field(default=100, ge=1, le=1000)
    backoff_seconds: int = Field(default=30, ge=0, le=3600)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    trigger_expression: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validar_agendamento(self) -> ErpSyncPolicyUpdate:
        """Exigir agenda somente para políticas agendadas."""
        if self.mode == "AGENDADO" and not self.trigger_expression:
            raise ValueError("Informe a frequência da sincronização agendada.")
        if self.mode != "AGENDADO":
            self.trigger_expression = None
        return self


class ErpSyncPolicyResponse(BaseModel):
    """Representação segura da política e do fluxo associado."""

    feature_code: str
    feature_name: str
    feature_description: str | None = None
    feature_enabled: bool
    mode: str
    record_scope: ErpRecordScope = "LINKED_ONLY"
    ativa: bool
    prioridade: str
    retry_ativo: bool
    retry_limite: int
    batch_size: int
    backoff_seconds: int
    timeout_seconds: int
    trigger_expression: str | None = None
    supported_modes: list[str] = Field(default_factory=list)
    endpoint_url: str | None = None
    endpoint_service: str | None = None
    endpoint_entity: str | None = None
