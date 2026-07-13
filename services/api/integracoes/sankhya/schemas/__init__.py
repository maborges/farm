"""Schemas para integração Sankhya."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SankhyaConfigCreate(BaseModel):
    auth_model: str | None = Field(
        default=None,
        description="Modelo de autenticação: gateway_oauth_client_credentials ou gateway_legacy_login",
    )
    sankhya_environment: str = Field(
        default="producao",
        description="Ambiente do Gateway Sankhya.",
    )
    sankhya_api_base_url: str | None = Field(
        default=None,
        description="Base URL do Gateway Sankhya.",
    )
    sankhya_auth_url: str | None = Field(
        default=None,
        description="Endpoint de autenticação /authenticate ou /login.",
    )
    sankhya_client_id: str | None = Field(default=None, description="Client ID do Gateway.")
    sankhya_client_secret: str | None = Field(
        default=None,
        description="Client Secret do Gateway.",
    )
    sankhya_x_token: str | None = Field(default=None, description="X-Token do Gateway.")
    sankhya_token: str | None = Field(
        default=None,
        description="[LEGACY GATEWAY] Token do login legado.",
    )
    sankhya_appkey: str | None = Field(
        default=None,
        description="[LEGACY GATEWAY] AppKey do login legado.",
    )
    sync_interval: int = Field(default=900, ge=60)
    # LEGACY: aceito apenas para compatibilidade com dados antigos.
    ws_url: str | None = Field(default=None, description="[LEGACY] URL do WS Sankhya.")
    username: str | None = Field(default=None, description="[LEGACY] Usuário do WS Sankhya.")
    password: str | None = Field(default=None, description="[LEGACY] Senha do WS Sankhya.")

    model_config = ConfigDict(extra="ignore")


class SankhyaConfigResponse(BaseModel):
    id: int
    tenant_id: str
    provider_code: str | None = None
    provider_name: str | None = None
    provider_display_name: str | None = None
    sankhya_environment: str | None = None
    sankhya_api_base_url: str | None = None
    sankhya_auth_url: str | None = None
    sankhya_client_id: str | None = None
    sankhya_client_secret_configured: bool = False
    sankhya_client_secret_mask: str | None = None
    sankhya_x_token_configured: bool = False
    sankhya_x_token_mask: str | None = None
    sankhya_token_configured: bool = False
    sankhya_token_mask: str | None = None
    sankhya_appkey_configured: bool = False
    sankhya_appkey_mask: str | None = None
    ws_url: str | None = None
    username: str | None = None
    password_configured: bool = False
    password_mask: str | None = None
    connection_schema: dict | None = None
    credential_schema: dict | None = None
    provider_definition: dict | None = None
    feature_schema: dict | None = None
    sync_schema: dict | None = None
    health_schema: dict | None = None
    ativo: bool
    ultimo_teste: datetime | None
    teste_status: str | None
    ultimo_sync: datetime | None
    sync_interval: int
    auth_model: str = "legacy_ws_basic_auth"
    legacy_configured: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SankhyaSyncLogResponse(BaseModel):
    id: int
    tenant_id: str
    tipo: str
    operacao: str
    status: str
    registros_processados: int
    registros_sucesso: int
    registros_erro: int
    tempo_execucao_ms: float | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    origem_dados: str = "legacy"
    integration_job_id: str | None = None
    feature_code: str | None = None
    job_status: str | None = None
    trigger_type: str | None = None
    job_started_at: datetime | None = None
    job_finished_at: datetime | None = None
    result_payload: dict | list | None = None
    error_payload: dict | list | str | None = None

    model_config = ConfigDict(from_attributes=True)


class SankhyaPessoaResponse(BaseModel):
    id: int
    sankhya_id: str
    tipo: str
    nome: str
    nome_fantasia: str | None
    cpf: str | None
    cnpj: str | None
    email: str | None
    telefone: str | None
    cidade: str | None
    uf: str | None
    ativo: bool
    sincronizado_em: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SankhyaProdutoResponse(BaseModel):
    id: int
    sankhya_id: str
    codigo: str
    nome: str
    ncm: str | None
    unidade: str
    preco_custo: float | None
    preco_venda: float | None
    ativo: bool
    sincronizado_em: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SankhyaNFEResponse(BaseModel):
    id: int
    sankhya_id: str | None
    tipo_operacao: str
    numero: str
    serie: str | None
    chave_acesso: str | None
    valor_total: float
    data_emissao: date | None
    status_sankhya: str | None
    exportado_sankhya: bool
    sincronizado_em: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SankhyaLancamentoFinanceiroResponse(BaseModel):
    id: int
    sankhya_id: str | None
    tipo: str
    numero_documento: str | None
    valor: float
    valor_saldo: float | None
    data_vencimento: date | None
    status: str | None
    exportado_sankhya: bool
    sincronizado_em: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SankhyaTestConnectionResponse(BaseModel):
    sucesso: bool
    mensagem: str
    ambiente: str | None = None
    base_url: str | None = None
    auth_url: str | None = None
    client_id_mask: str | None = None
    x_token_mask: str | None = None
    token_obtido: bool = False
    token_expires_at: datetime | None = None
    auth_model: str | None = None


class SankhyaSyncStatusResponse(BaseModel):
    configurado: bool
    ativo: bool
    ultimo_sync: datetime | None
    proximo_sync: datetime | None
    status_conexao: str
    status_legado: str | None = None
    status_canonico: str | None = None
    status_origem: str = "legacy"
    health_origem: str = "legacy"
    config_id_canonico: int | None = None
    lifecycle_state: str | None = None
    health_status: str | None = None
    health_summary: str | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    features_habilitadas: list[str] = Field(default_factory=list)
    policies_resumidas: list[dict[str, str | bool | int | None]] = Field(default_factory=list)
    provider_definition: dict | None = None
    feature_schema: dict | None = None
    sync_schema: dict | None = None
    health_schema: dict | None = None
    readiness: dict | None = None


class SankhyaHealthResponse(BaseModel):
    configurado: bool
    origem: str = "legacy"
    status: str
    summary: str | None = None
    checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    details: dict | list | str | None = None


class SankhyaIntegrationJobResponse(BaseModel):
    id: str
    tenant_id: str
    config_id: int | None = None
    feature_code: str | None = None
    job_status: str
    trigger_type: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    processados: int = 0
    sucessos: int = 0
    erros: int = 0
    correlation_id: str | None = None
    legacy_log_id: int | None = None
    result_payload: dict | list | None = None
    error_payload: dict | list | str | None = None


class SankhyaTimelineItemResponse(BaseModel):
    id: str
    tipo_registro: str
    origem_dado: str
    feature_code: str | None = None
    status: str
    event_type: str | None = None
    resumo: str
    occurred_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duracao_ms: float | None = None
    processados: int = 0
    sucessos: int = 0
    erros: int = 0
    correlation_id: str | None = None
    payload: dict | list | str | None = None


class SankhyaOperationalDiagnosisResponse(BaseModel):
    origem: str = "legacy"
    health_atual: str
    status_degradacao: str
    ultimo_sucesso_at: datetime | None = None
    ultima_falha_at: datetime | None = None
    falhas_consecutivas: int = 0
    feature_mais_problematica: str | None = None
    jobs_pendentes: int = 0
    jobs_falhos: int = 0
    recomendacao_operacional: str
