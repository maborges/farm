"""Contratos tipados Pydantic para as configurações do DeepFarms Agro.

Garante validação sintática e semântica, limites numéricos, valores padrão
e controle de concorrência com versionamento persistente para a administração
via Backoffice.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Chaves canônicas do Agro
KEY_CLIMA = "agro:clima:config"
KEY_MERCADO = "agro:mercado:config"
KEY_MENSAGENS = "agro:mensagens:avisos"
KEY_FLAGS = "agro:feature_flags"


class AgroConfigMetadata(BaseModel):
    """Metadados de auditoria e versionamento da configuração."""
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(default=1, ge=0, description="Número incremental de revisão")
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO 8601 da última alteração"
    )
    updated_by: str = Field(default="sistema@deepfarms.com", description="E-mail do administrador responsável")
    version: str = Field(default="1.0", description="Versão do schema")


class AgroClimaConfig(BaseModel):
    """Configuração dos provedores climáticos e políticas de resiliência."""
    model_config = ConfigDict(extra="forbid")

    active_provider: str = Field(
        default="WEATHERAPI",
        description="Provedor meteorológico ativo homologado"
    )
    fallback_chain: list[str] = Field(
        default=["OPENWEATHER", "OPEN_METEO"],
        description="Cadeia ordenada de failover em caso de indisponibilidade ou cota esgotada"
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=15.0,
        description="Timeout máximo por requisição upstream (segundos)"
    )
    cache_ttl_seconds: int = Field(
        default=1800,
        ge=300,
        le=86400,
        description="Tempo de vida do cache por nó espacial de grid (segundos)"
    )
    monthly_quota_limit: int = Field(
        default=100000,
        ge=0,
        le=10000000,
        description="Limite mensal de chamadas upstream (0 = ilimitado)"
    )
    force_contingency_mode: bool = Field(
        default=False,
        description="Se True, desvia todas as consultas diretamente para o modo de contingência"
    )
    contingency_provider: str | None = Field(
        default=None,
        description="Provedor selecionado para atender o modo de contingência"
    )
    openweather_licensed: bool = Field(
        default=False,
        description="Flag indicando se a plataforma possui licença ativa para OpenWeather"
    )
    open_meteo_licensed: bool = Field(
        default=False,
        description="Flag indicando se a plataforma possui licença ativa para Open-Meteo"
    )
    quota_alert_threshold_80: bool = Field(
        default=True,
        description="Emite aviso nos logs e interface ao atingir 80% da franquia"
    )
    quota_alert_threshold_95: bool = Field(
        default=True,
        description="Emite aviso crítico nos logs e interface ao atingir 95% da franquia"
    )

    @field_validator("fallback_chain")
    @classmethod
    def validate_fallback_chain(cls, v: list[str]) -> list[str]:
        seen = set()
        deduped = []
        for p in v:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped


class AgroMercadoConfig(BaseModel):
    """Parâmetros operacionais e de cache para o subsistema de mercado."""
    model_config = ConfigDict(extra="forbid")

    ptax_cache_ttl_seconds: int = Field(
        default=1800,
        ge=300,
        le=14400,
        description="TTL do cache para dados PTAX do Banco Central (segundos)"
    )
    macro_cache_ttl_seconds: int = Field(
        default=1800,
        ge=300,
        le=86400,
        description="TTL do cache para indicadores macroeconômicos SGS (segundos)"
    )
    sidra_cache_ttl_seconds: int = Field(
        default=3600,
        ge=300,
        le=604800,
        description="TTL do cache para estatísticas agropecuárias SIDRA/IBGE (segundos)"
    )
    precos_cache_ttl_seconds: int = Field(
        default=1800,
        ge=300,
        le=86400,
        description="TTL do cache para preços públicos DERAL (segundos)"
    )
    max_defasagem_dias: int = Field(
        default=14,
        ge=1,
        le=60,
        description="Tolerância máxima em dias antes de considerar a cotação defasada"
    )
    deral_active_snapshot: str = Field(
        default="deral-prp-2026-10-16.json",
        max_length=100,
        pattern=r"^deral-prp-[0-9]{4}-[0-9]{2}-[0-9]{2}\.(?:json|xls)$",
        description="Nome do arquivo .json ou .xls do snapshot semanal DERAL ativo"
    )
    active_snapshot_id: str = Field(
        default="2026-10-16",
        max_length=50,
        description="Identificador único ou data de referência do snapshot DERAL ativo"
    )
    deral_source_url: str = Field(
        default="https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
        max_length=300,
        description="URL institucional de origem do documento oficial DERAL"
    )
    ptax_enabled: bool = Field(
        default=True,
        description="Habilita serviço de cotação PTAX"
    )
    sgs_enabled: bool = Field(
        default=True,
        description="Habilita séries macroeconômicas SGS"
    )
    sidra_enabled: bool = Field(
        default=True,
        description="Habilita estatísticas agropecuárias SIDRA"
    )
    deral_enabled: bool = Field(
        default=True,
        description="Habilita cotações de preços públicos DERAL"
    )


class AgroMensagemItem(BaseModel):
    """Mensagem institucional ou comunicado operacional publicado para os usuários do Agro."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único da mensagem")
    titulo: str = Field(min_length=3, max_length=150, description="Título do comunicado ou aviso")
    conteudo: str = Field(min_length=5, max_length=1000, description="Corpo detalhado da mensagem")
    finalidade: Literal["REGULATORIO", "URGENTE", "MANUTENCAO", "COMUNICADO", "NOVIDADE"] = Field(
        default="COMUNICADO", description="Classificação por objetivo institucional"
    )
    ativo: bool = Field(default=True, description="Indicador se a mensagem está ativa")
    prioridade: int = Field(default=1, ge=1, le=10, description="Prioridade de exibição (1 mais alta)")
    vigencia_inicio: Optional[str] = Field(default=None, description="Data/hora inicial de vigência (ISO 8601)")
    vigencia_fim: Optional[str] = Field(default=None, description="Data/hora final de vigência (ISO 8601)")
    link_externo: Optional[str] = Field(default=None, max_length=300, description="Link de ação ou detalhamento (opcional)")
    criado_em: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp de criação"
    )


class AgroMensagensAvisosConfig(BaseModel):
    """Textos regulatórios, avisos legais e mensagens institucionais do Agro."""
    model_config = ConfigDict(extra="forbid")

    aviso_precos_deral: str = Field(
        default=(
            "Preço médio semanal recebido pelo produtor, publicado pelo DERAL/SEAB-PR. "
            "Não constitui cotação em tempo real nem contrato futuro."
        ),
        min_length=10,
        max_length=500,
        description="Aviso legal para cotações públicas DERAL"
    )
    aviso_ptax: str = Field(
        default=(
            "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. "
            "Não representa cotação de câmbio em tempo real."
        ),
        min_length=10,
        max_length=500,
        description="Aviso legal para o fechamento diário da PTAX"
    )
    aviso_macro_bcb: str = Field(
        default=(
            "Dados públicos oficiais divulgados pelo Banco Central do Brasil (BCB) e IBGE. "
            "Não constituem recomendação de investimento."
        ),
        min_length=10,
        max_length=500,
        description="Aviso legal para indicadores macroeconômicos (Selic, IPCA)"
    )
    aviso_ibge: str = Field(
        default=(
            "Estatística oficial de produção divulgada pelo IBGE (SIDRA). "
            "Não é cotação nem preço de comercialização."
        ),
        min_length=10,
        max_length=500,
        description="Aviso legal para estatísticas agropecuárias do IBGE"
    )
    banner_urgente: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Banner de utilidade pública ou aviso de manutenção exibido no topo do app (null para ocultar)"
    )
    mensagens_institucionais: list[AgroMensagemItem] = Field(
        default_factory=list,
        description="Lista de comunicados e mensagens institucionais gerenciados"
    )


class AgroFeatureFlagsConfig(BaseModel):
    """Chaves de feature flags operacionais para o aplicativo DeepFarms Agro."""
    model_config = ConfigDict(extra="forbid")

    clima_enabled: bool = Field(default=True, description="Habilita módulo de inteligência meteorológica")
    mercado_enabled: bool = Field(default=True, description="Habilita módulo de cotações e indicadores")
    byok_enabled: bool = Field(default=True, description="Habilita cofre BYOK para uso de chaves meteorológicas próprias")
    ibge_enabled: bool = Field(default=True, description="Habilita estatísticas agropecuárias históricas do IBGE")
    calculadoras_enabled: bool = Field(default=True, description="Habilita calculadoras agronômicas operacionais")


class AgroConfigItemResponse(BaseModel):
    """Item de configuração individual do Agro retornado para o Backoffice."""
    chave: str
    valor: dict[str, Any]
    meta: AgroConfigMetadata
    descricao: Optional[str] = None
    ativo: bool = True


class AgroConfigUpdateRequest(BaseModel):
    """Payload de atualização de uma configuração Agro."""
    valor: dict[str, Any]
    expected_revision: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de revisão esperado para controle otimista de concorrência"
    )
    descricao: Optional[str] = None
    ativo: Optional[bool] = None


class AgroAllConfigsResponse(BaseModel):
    """Agrupamento consolidado das configurações do Agro para o Backoffice."""
    clima: AgroConfigItemResponse
    mercado: AgroConfigItemResponse
    mensagens: AgroConfigItemResponse
    feature_flags: AgroConfigItemResponse


# ==============================================================================
# SCHEMAS DE CREDENCIAIS GLOBAIS E GESTÃO DE PROVEDORES CLIMÁTICOS (01E3)
# ==============================================================================

KEY_CREDENTIALS_CLIMA = "agro:credentials:clima"


class PlatformWeatherCredentialItem(BaseModel):
    """Metadados seguros de uma credencial meteorológica (sem expor segredos)."""
    model_config = ConfigDict(extra="forbid")

    provider_slug: str
    is_configured: bool = Field(description="Indica se há chave salva e válida no cofre")
    key_preview: str = Field(description="Máscara de pré-visualização (ex: ••••••••abcd)")
    is_licensed: bool = Field(default=False, description="Licença comercial/plano homologado")
    key_version: int = Field(default=1, description="Versão da chave criptográfica para rotação")
    kek_version: int = Field(default=1, description="Versão do KEK/algoritmo criptográfico utilizado")
    last_updated: Optional[str] = None
    updated_by: Optional[str] = None


class PlatformWeatherCredentialsStatusResponse(BaseModel):
    """Status público administrativo de todas as credenciais meteorológicas da plataforma."""
    model_config = ConfigDict(extra="forbid")

    items: list[PlatformWeatherCredentialItem]


class PlatformWeatherCredentialUpdateRequest(BaseModel):
    """Payload seguro para cadastro ou rotação de credencial meteorológica."""
    model_config = ConfigDict(extra="forbid")

    provider_slug: Literal["WEATHERAPI", "OPENWEATHER"]
    api_key: str = Field(min_length=8, max_length=256, description="Chave secreta de API a ser cifrada")
    is_licensed: bool = Field(default=True, description="Confirmação de licenciamento para a plataforma")
    key_version: int = Field(default=1, ge=1, description="Versão sequencial da chave para controle de rotação")
    force_on_upstream_incident: bool = Field(
        default=False,
        description="Permite salvar a credencial caso o upstream esteja indisponível (exceto falha de autenticação 401/403)",
    )
    incident_justification: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Justificativa operacional obrigatória caso force_on_upstream_incident seja True",
    )


class ProviderConnectivityTestRequest(BaseModel):
    """Parâmetros opcionais para teste de conectividade com o provedor."""
    model_config = ConfigDict(extra="forbid")

    provider_slug: Literal["WEATHERAPI", "OPENWEATHER", "OPEN_METEO"]
    api_key_override: Optional[str] = Field(default=None, description="Chave opcional para teste prévio antes de salvar")
    latitude: float = Field(default=-23.3103, ge=-90.0, le=90.0)
    longitude: float = Field(default=-51.1628, ge=-180.0, le=180.0)


class ProviderConnectivityTestResponse(BaseModel):
    """Resultado do teste de conectividade upstream."""
    provider_slug: str
    success: bool
    latency_ms: float
    message: str
    tested_at: str
    details: Optional[dict[str, Any]] = None


class ProviderOperationalStatusItem(BaseModel):
    """Situação de disponibilidade e saúde de um provedor meteorológico."""
    model_config = ConfigDict(extra="forbid")

    slug: str
    nome: str
    is_active: bool
    is_fallback: bool
    fallback_priority: Optional[int] = None
    status: str = Field(default="ONLINE", description="Situação operacional (ONLINE, OFFLINE, SEM_CREDENCIAL, etc)")
    has_credentials: bool
    requires_credentials: bool
    is_licensed: bool
    monthly_quota_limit: int = 0
    monthly_calls: int = 0
    quota_percentage: float = 0.0
    key_preview: Optional[str] = None
    last_error: Optional[str] = None
    last_tested_at: Optional[str] = None
    latency_p95_ms: Optional[float] = None


class ProviderOperationalStatusResponse(BaseModel):
    """Visão consolidada da gestão de provedores para o Backoffice."""
    model_config = ConfigDict(extra="forbid")

    active_provider: str
    contingency_mode: bool = False
    contingency_provider: Optional[str] = None
    providers: list[ProviderOperationalStatusItem]
    fallback_chain: list[str]
    timeout_seconds: float
    cache_ttl_seconds: int = 1800
    monthly_quota_limit: int = 0
    current_month_calls: int = 0
    quota_percentage: float = 0.0
    revision: int = 1


class ProviderMetricsResponse(BaseModel):
    """Métricas operacionais de chamadas e erros por provedor."""
    model_config = ConfigDict(extra="forbid")

    provider_slug: str
    month: str
    upstream_calls_month: int = 0
    monthly_quota_limit: int = 0
    quota_usage_percent: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    timeouts: int = 0
    failures: int = 0
    contingency_cache_used: int = 0


# ==============================================================================
# SCHEMAS DE GOVERNANÇA DE MERCADO E SNAPSHOTS DERAL (01E4)
# ==============================================================================

KEY_DERAI_INDEX = "agro:deral:snapshots:index"
KEY_DERAI_SNAPSHOT_PREFIX = "agro:deral:snap:"


class MarketSourceStatusItem(BaseModel):
    """Situação operacional e de conectividade de uma fonte oficial de mercado."""
    model_config = ConfigDict(extra="forbid")

    fonte_id: Literal["BCB_PTAX", "BCB_SGS", "IBGE_SIDRA", "DERAL_SEAB"]
    nome: str
    orgao: str
    tipo_dado: str
    url_origem: str
    status: Literal["ONLINE", "DEFASADO", "OFFLINE", "DEGRADADO"]
    cache_ttl_seconds: int
    last_success_at: Optional[str] = None
    last_error: Optional[str] = None
    defasagem_dias: Optional[int] = None
    detalhes_operacionais: dict[str, Any] = Field(default_factory=dict)


class MarketSourcesStatusResponse(BaseModel):
    """Visão consolidada da governança de todas as fontes oficiais de mercado."""
    model_config = ConfigDict(extra="forbid")

    sources: list[MarketSourceStatusItem]
    config: AgroMercadoConfig
    revision: int = 1
    updated_at: str


class DeralSnapshotMetadata(BaseModel):
    """Metadados de auditoria, integridade e versionamento de um snapshot DERAL."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identificador único (ex: 2026-10-16)")
    filename: str = Field(description="Nome do arquivo versionado")
    sha256: str = Field(description="Hash SHA-256 do documento original para integridade dos bytes")
    data_referencia: str = Field(description="Data de referência dos preços (YYYY-MM-DD)")
    data_publicacao: Optional[str] = None
    data_obtencao: Optional[str] = None
    fonte_oficial: str = "DERAL/SEAB-PR"
    origem_declarada: str = "DERAL/SEAB-PR"
    origem_verificada: bool = False
    estado_verificacao: Literal["PENDENTE", "VERIFICADO", "FALHA_VERIFICACAO"] = "PENDENTE"
    estado_aprovacao: Literal["PENDENTE", "APROVADO", "REJEITADO"] = "PENDENTE"
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    documento_oficial: str = Field(description="URL ou nome do documento oficial de origem")
    total_itens: int = Field(ge=1, description="Quantidade de cotações válidas no snapshot")
    status: Literal["VALIDADO", "APROVADO", "ATIVO", "ANTERIOR", "ARQUIVADO", "REJEITADO"] = "VALIDADO"
    is_active: bool = False
    uploaded_at: str
    uploaded_by: str
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    transformacao_aplicada: str = "Arredondamento decimal HALF_UP para 2 casas"
    tamanho_bytes: int = Field(ge=1)


class DeralSnapshotApprovalRequest(BaseModel):
    """Solicitação de aprovação ou rejeição formal de proveniência de um snapshot."""
    model_config = ConfigDict(extra="forbid")

    aprovado: bool = Field(description="True para aprovar o snapshot para publicação; False para rejeitar")
    justificativa: str = Field(
        min_length=5,
        max_length=500,
        description="Justificativa administrativa da aprovação ou rejeição da proveniência"
    )


class DeralSnapshotIntegrityResponse(BaseModel):
    """Resultado da auditoria e recálculo de integridade criptográfica dos bytes originais."""
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    sha256_registrado: str
    sha256_recalculado: str
    tamanho_bytes_registrado: int
    tamanho_bytes_armazenado: int
    integro: bool
    verificado_em: str
    origem_verificada: bool
    estado_verificacao: str
    mensagem: str


class DeralSnapshotDetailResponse(BaseModel):
    """Detalhes completos de um snapshot DERAL incluindo itens normalizados para preview."""
    model_config = ConfigDict(extra="forbid")

    metadata: DeralSnapshotMetadata
    itens: list[dict[str, Any]]
    raw_document_preview: Optional[dict[str, Any]] = None


class DeralSnapshotsListResponse(BaseModel):
    """Histórico de snapshots DERAL catalogados na plataforma."""
    model_config = ConfigDict(extra="forbid")

    active_snapshot_id: Optional[str] = None
    snapshots: list[DeralSnapshotMetadata]
    total: int


class DeralSnapshotUploadResponse(BaseModel):
    """Resultado do upload e validação de um snapshot antes da ativação."""
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    mensagem: str
    metadata: DeralSnapshotMetadata
    validacoes: list[str]
    itens_preview: list[dict[str, Any]]


class DeralSnapshotActivationRequest(BaseModel):
    """Solicitação de ativação transacional de um snapshot DERAL validado."""
    model_config = ConfigDict(extra="forbid")

    expected_revision: Optional[int] = Field(
        default=None,
        description="Revisão esperada de agro:mercado:config para concorrência otimista"
    )
    justificativa: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Justificativa administrativa para ativação do snapshot"
    )


class DeralSnapshotRollbackRequest(BaseModel):
    """Solicitação de rollback para um snapshot previamente validado."""
    model_config = ConfigDict(extra="forbid")

    target_snapshot_id: str = Field(description="ID do snapshot homologado de destino")
    expected_revision: Optional[int] = Field(
        default=None,
        description="Revisão esperada de agro:mercado:config para concorrência otimista"
    )
    justificativa: str = Field(
        min_length=5,
        max_length=500,
        description="Justificativa administrativa obrigatória para o rollback"
    )


class MarketConfigUpdateRequest(BaseModel):
    """Payload para ajuste dos parâmetros operacionais de mercado."""
    model_config = ConfigDict(extra="forbid")

    ptax_cache_ttl_seconds: Optional[int] = Field(default=None, ge=300, le=14400)
    macro_cache_ttl_seconds: Optional[int] = Field(default=None, ge=300, le=86400)
    sidra_cache_ttl_seconds: Optional[int] = Field(default=None, ge=300, le=604800)
    precos_cache_ttl_seconds: Optional[int] = Field(default=None, ge=300, le=86400)
    max_defasagem_dias: Optional[int] = Field(default=None, ge=1, le=60)
    deral_source_url: Optional[str] = Field(default=None, max_length=300)
    ptax_enabled: Optional[bool] = None
    sgs_enabled: Optional[bool] = None
    sidra_enabled: Optional[bool] = None
    deral_enabled: Optional[bool] = None
    expected_revision: Optional[int] = None


# ==============================================================================
# SCHEMAS DO CONTRATO PÚBLICO E MENSAGENS DO AGRO (01E5)
# ==============================================================================

class AgroPublicConfigResponse(BaseModel):
    """Contrato público consumido pelo DeepFarms Agro (PWA) e navegadores anônimos."""
    model_config = ConfigDict(extra="forbid")

    sucesso: bool = True
    versao: str = "1.0"
    consultado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    feature_flags: AgroFeatureFlagsConfig
    banner_urgente: Optional[str] = None
    mensagens_vigentes: list[AgroMensagemItem] = Field(default_factory=list)
    avisos_legais: dict[str, str] = Field(default_factory=dict)


class AgroMensagemCreateRequest(BaseModel):
    """Payload de cadastro de uma mensagem institucional."""
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=150)
    conteudo: str = Field(min_length=5, max_length=1000)
    finalidade: Literal["REGULATORIO", "URGENTE", "MANUTENCAO", "COMUNICADO", "NOVIDADE"] = "COMUNICADO"
    ativo: bool = True
    prioridade: int = Field(default=1, ge=1, le=10)
    vigencia_inicio: Optional[str] = None
    vigencia_fim: Optional[str] = None
    link_externo: Optional[str] = Field(default=None, max_length=300)


class AgroMensagemUpdateRequest(BaseModel):
    """Payload de atualização parcial de uma mensagem institucional."""
    model_config = ConfigDict(extra="forbid")

    titulo: Optional[str] = Field(default=None, min_length=3, max_length=150)
    conteudo: Optional[str] = Field(default=None, min_length=5, max_length=1000)
    finalidade: Optional[Literal["REGULATORIO", "URGENTE", "MANUTENCAO", "COMUNICADO", "NOVIDADE"]] = None
    ativo: Optional[bool] = None
    prioridade: Optional[int] = Field(default=None, ge=1, le=10)
    vigencia_inicio: Optional[str] = None
    vigencia_fim: Optional[str] = None
    link_externo: Optional[str] = Field(default=None, max_length=300)


# ==============================================================================
# SCHEMAS DE BIBLIOTECAS E CATÁLOGOS GLOBAIS DO AGRO (01E5)
# ==============================================================================

class AgroCommodityResponse(BaseModel):
    id: uuid.UUID
    nome: str
    codigo: str
    tipo: str
    unidade_padrao: str
    peso_unidade: Optional[float] = None
    umidade_padrao_pct: Optional[float] = None
    impureza_padrao_pct: Optional[float] = None
    possui_cotacao: bool = False
    bolsa_referencia: Optional[str] = None
    codigo_bolsa: Optional[str] = None
    ativo: bool = True
    sistema: bool = True
    descricao: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgroCommodityCreateRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    codigo: str = Field(min_length=2, max_length=50)
    tipo: str = Field(min_length=2, max_length=30)
    unidade_padrao: str = Field(min_length=1, max_length=20)
    peso_unidade: Optional[float] = Field(default=None, gt=0)
    umidade_padrao_pct: Optional[float] = Field(default=None, ge=0, le=100)
    impureza_padrao_pct: Optional[float] = Field(default=None, ge=0, le=100)
    possui_cotacao: bool = False
    bolsa_referencia: Optional[str] = None
    codigo_bolsa: Optional[str] = None
    ativo: bool = True
    descricao: Optional[str] = None


class AgroCommodityUpdateRequest(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=150)
    tipo: Optional[str] = Field(default=None, min_length=2, max_length=30)
    unidade_padrao: Optional[str] = Field(default=None, min_length=1, max_length=20)
    peso_unidade: Optional[float] = Field(default=None, gt=0)
    umidade_padrao_pct: Optional[float] = Field(default=None, ge=0, le=100)
    impureza_padrao_pct: Optional[float] = Field(default=None, ge=0, le=100)
    possui_cotacao: Optional[bool] = None
    bolsa_referencia: Optional[str] = None
    codigo_bolsa: Optional[str] = None
    ativo: Optional[bool] = None
    descricao: Optional[str] = None


class AgroCommodityListResponse(BaseModel):
    itens: list[AgroCommodityResponse]
    total: int
    pagina: int
    tamanho_pagina: int


class AgroCulturaResponse(BaseModel):
    id: uuid.UUID
    nome: str
    nome_cientifico: Optional[str] = None
    grupo: Optional[str] = None
    ciclo_dias_min: Optional[int] = None
    ciclo_dias_max: Optional[int] = None
    espacamento_cm: Optional[float] = None
    populacao_plantas_ha: Optional[int] = None
    produtividade_media_sc_ha: Optional[float] = None
    v_meta_pct_padrao: Optional[float] = None
    ativa: bool = True
    sistema: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgroCulturaCreateRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    nome_cientifico: Optional[str] = Field(default=None, max_length=150)
    grupo: Optional[str] = Field(default=None, max_length=50)
    ciclo_dias_min: Optional[int] = Field(default=None, ge=1)
    ciclo_dias_max: Optional[int] = Field(default=None, ge=1)
    espacamento_cm: Optional[float] = Field(default=None, gt=0)
    populacao_plantas_ha: Optional[int] = Field(default=None, gt=0)
    produtividade_media_sc_ha: Optional[float] = Field(default=None, gt=0)
    v_meta_pct_padrao: Optional[float] = Field(default=None, ge=0, le=100)
    ativa: bool = True


class AgroCulturaUpdateRequest(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=100)
    nome_cientifico: Optional[str] = Field(default=None, max_length=150)
    grupo: Optional[str] = Field(default=None, max_length=50)
    ciclo_dias_min: Optional[int] = Field(default=None, ge=1)
    ciclo_dias_max: Optional[int] = Field(default=None, ge=1)
    espacamento_cm: Optional[float] = Field(default=None, gt=0)
    populacao_plantas_ha: Optional[int] = Field(default=None, gt=0)
    produtividade_media_sc_ha: Optional[float] = Field(default=None, gt=0)
    v_meta_pct_padrao: Optional[float] = Field(default=None, ge=0, le=100)
    ativa: Optional[bool] = None


class AgroCulturaListResponse(BaseModel):
    itens: list[AgroCulturaResponse]
    total: int
    pagina: int
    tamanho_pagina: int


class AgroUomResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nome: str
    dimensao: str
    codigo_referencia: str
    fator_referencia: float
    casas_decimais: int
    eh_unidade_base: bool
    sistema: bool = True
    ativo: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgroUomCreateRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=16)
    nome: str = Field(min_length=2, max_length=80)
    dimensao: str = Field(min_length=2, max_length=24)
    codigo_referencia: str = Field(min_length=1, max_length=16)
    fator_referencia: float = Field(gt=0)
    casas_decimais: int = Field(default=2, ge=0, le=6)
    eh_unidade_base: bool = False
    ativo: bool = True


class AgroUomUpdateRequest(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=80)
    dimensao: Optional[str] = Field(default=None, min_length=2, max_length=24)
    codigo_referencia: Optional[str] = Field(default=None, min_length=1, max_length=16)
    fator_referencia: Optional[float] = Field(default=None, gt=0)
    casas_decimais: Optional[int] = Field(default=None, ge=0, le=6)
    eh_unidade_base: Optional[bool] = None
    ativo: Optional[bool] = None


class AgroUomListResponse(BaseModel):
    itens: list[AgroUomResponse]
    total: int
    pagina: int
    tamanho_pagina: int


class AgroUomConversaoResponse(BaseModel):
    id: uuid.UUID
    unidade_origem_id: uuid.UUID
    unidade_destino_id: uuid.UUID
    fator: float
    cultura: Optional[str] = None
    commodity_id: Optional[uuid.UUID] = None
    contexto: Optional[dict[str, Any]] = None
    observacoes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgroUomConversaoCreateRequest(BaseModel):
    unidade_origem_id: uuid.UUID
    unidade_destino_id: uuid.UUID
    fator: float = Field(gt=0)
    cultura: Optional[str] = None
    commodity_id: Optional[uuid.UUID] = None
    contexto: Optional[dict[str, Any]] = None
    observacoes: Optional[str] = None


class AgroUomConversaoUpdateRequest(BaseModel):
    fator: Optional[float] = Field(default=None, gt=0)
    cultura: Optional[str] = None
    commodity_id: Optional[uuid.UUID] = None
    contexto: Optional[dict[str, Any]] = None
    observacoes: Optional[str] = None


class AgroUomConversaoListResponse(BaseModel):
    itens: list[AgroUomConversaoResponse]
    total: int
    pagina: int
    tamanho_pagina: int
