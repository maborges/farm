"""Contratos Pydantic v2 estritos para o Backoffice administrativo do coletor agropecuário."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import (
    AutoPublishPolicyLiteral,
    DomainLiteral,
    EstrategiaColetaLiteral,
    RunStatusLiteral,
    StatusRevisaoLiteral,
    TipoLicencaLiteral,
    TriggerTipoLiteral,
)


class CollectorSourceItem(BaseModel):
    """Projeção administrativa de uma fonte configurada em ``agro_data_sources``."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    domain: DomainLiteral
    slug: str
    nome: str
    sigla: str
    tipo_licenca: TipoLicencaLiteral
    termo_autorizacao_ref: str | None = None
    atribuicao_obrigatoria: str | None = None
    uf_padrao: str
    praca_padrao: str | None = None
    dominios_whitelist: list[str]
    url_principal: str
    url_indice: str | None = None
    estrategia_coleta: EstrategiaColetaLiteral
    config_extrator: dict[str, Any]
    cron_ou_intervalo_seg: int
    auto_publish_policy: AutoPublishPolicyLiteral
    max_variacao_pct: Decimal
    max_defasagem_dias: int
    prioridade_exibicao: int
    ativo: bool
    falhas_consecutivas: int
    ultima_execucao_em: datetime | None = None
    ultimo_sucesso_em: datetime | None = None
    proximo_ciclo_em: datetime | None = None
    pendentes_revisao: int = 0


class CollectorSourcesListResponse(BaseModel):
    """Lista completa de fontes oficiais e parceiros autorizados do coletor."""

    model_config = ConfigDict(extra="forbid")

    sources: list[CollectorSourceItem]
    total: int
    pendentes_quarentena_total: int


class CollectorSourceCreateRequest(BaseModel):
    """Payload validado para cadastrar nova fonte pública ou parceira autorizada."""

    model_config = ConfigDict(extra="forbid")

    domain: DomainLiteral = "MERCADO"
    slug: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=3, max_length=150)
    sigla: str = Field(min_length=2, max_length=40)
    tipo_licenca: TipoLicencaLiteral
    termo_autorizacao_ref: str | None = Field(default=None, max_length=2000)
    atribuicao_obrigatoria: str | None = Field(default=None, max_length=255)
    uf_padrao: str = Field(min_length=2, max_length=2)
    praca_padrao: str | None = Field(default=None, max_length=120)
    dominios_whitelist: list[str] = Field(min_length=1)
    url_principal: str = Field(min_length=8, max_length=1000)
    url_indice: str | None = Field(default=None, max_length=1000)
    estrategia_coleta: EstrategiaColetaLiteral = "GENERICO_PARCEIRO"
    config_extrator: dict[str, Any] = Field(default_factory=dict)
    cron_ou_intervalo_seg: int = Field(default=86400, ge=300, le=2592000)
    auto_publish_policy: AutoPublishPolicyLiteral = "SEMPRE_REVISAO_HUMANA"
    max_variacao_pct: Decimal = Field(default=Decimal("12.00"), gt=0, le=100)
    max_defasagem_dias: int = Field(default=14, ge=1, le=365)
    prioridade_exibicao: int = Field(default=2, ge=1, le=20)
    ativo: bool = True

    @model_validator(mode="after")
    def _validate_compliance(self) -> CollectorSourceCreateRequest:
        if self.tipo_licenca == "PARCEIRO_AUTORIZADO" and not (
            self.termo_autorizacao_ref and self.termo_autorizacao_ref.strip()
        ):
            raise ValueError(
                "termo_autorizacao_ref é obrigatório para fontes PARCEIRO_AUTORIZADO."
            )
        return self


class CollectorSourceUpdateRequest(BaseModel):
    """Payload de atualização parcial de fonte homologada no Backoffice."""

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=3, max_length=150)
    sigla: str | None = Field(default=None, min_length=2, max_length=40)
    tipo_licenca: TipoLicencaLiteral | None = None
    termo_autorizacao_ref: str | None = Field(default=None, max_length=2000)
    atribuicao_obrigatoria: str | None = Field(default=None, max_length=255)
    uf_padrao: str | None = Field(default=None, min_length=2, max_length=2)
    praca_padrao: str | None = Field(default=None, max_length=120)
    dominios_whitelist: list[str] | None = Field(default=None, min_length=1)
    url_principal: str | None = Field(default=None, min_length=8, max_length=1000)
    url_indice: str | None = Field(default=None, max_length=1000)
    estrategia_coleta: EstrategiaColetaLiteral | None = None
    config_extrator: dict[str, Any] | None = None
    cron_ou_intervalo_seg: int | None = Field(default=None, ge=300, le=2592000)
    auto_publish_policy: AutoPublishPolicyLiteral | None = None
    max_variacao_pct: Decimal | None = Field(default=None, gt=0, le=100)
    max_defasagem_dias: int | None = Field(default=None, ge=1, le=365)
    prioridade_exibicao: int | None = Field(default=None, ge=1, le=20)
    ativo: bool | None = None


class CollectorDryRunObservationItem(BaseModel):
    """Prévia de observação extraída durante Testar Coleta (Dry-Run)."""

    model_config = ConfigDict(extra="forbid")

    commodity_id: str
    uf: str
    praca: str
    data_referencia: date
    valor_normalizado: Decimal
    unidade_normalizada: str
    trecho_evidencia: str
    flags_anomalia: list[str]
    bloqueado_para_publicacao: bool


class CollectorDryRunResponse(BaseModel):
    """Resultado do teste de coleta sem gravação em banco ou publicação pública."""

    model_config = ConfigDict(extra="forbid")

    source_slug: str
    url_efetiva: str
    sha256_bruto: str
    modelo_ia: str | None = None
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_estimado_usd: Decimal = Decimal("0")
    total_extraidos: int
    itens: list[CollectorDryRunObservationItem]


class CollectorRunItem(BaseModel):
    """Execução histórica registrada com telemetria HTTP, IA e sugestão do Sentinela."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    source_id: uuid.UUID
    source_slug: str
    source_sigla: str
    status: RunStatusLiteral
    trigger_tipo: TriggerTipoLiteral
    executado_por: str | None = None
    url_efetiva: str | None = None
    http_status: int | None = None
    sha256_bruto: str | None = None
    tamanho_bytes: int | None = None
    skipped_unchanged: bool
    modelo_ia: str | None = None
    tokens_entrada: int
    tokens_saida: int
    custo_estimado_usd: Decimal
    total_extraidos: int
    total_publicados: int
    total_quarentena: int
    total_rejeitados: int
    erro_resumo: str | None = None
    sugestao_sentinela: dict[str, Any] | None = None
    has_artifact: bool = False
    artifact_expurgado: bool = False
    iniciado_em: datetime
    finalizado_em: datetime | None = None


class CollectorRunsListResponse(BaseModel):
    """Lista de execuções recentes do coletor."""

    model_config = ConfigDict(extra="forbid")

    runs: list[CollectorRunItem]
    total: int


class CollectorApplySentinelRequest(BaseModel):
    """Solicitação auditada para aplicar a nova URL sugerida pelo Agente Sentinela."""

    model_config = ConfigDict(extra="forbid")

    justificativa: str = Field(min_length=5, max_length=500)


class CollectorStagingItem(BaseModel):
    """Item em fila de revisão/quarentena com evidência literal e último preço publicado."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    run_id: uuid.UUID
    source_id: uuid.UUID
    source_slug: str
    source_sigla: str
    commodity_id: str
    uf: str
    praca: str
    tipo_preco: str
    periodicidade: str
    data_referencia: date
    valor_normalizado: Decimal
    moeda: str
    unidade_normalizada: str
    valor_original: Decimal
    unidade_original: str
    fator_conversao: Decimal
    transformacao_aplicada: str | None = None
    trecho_evidencia: str
    registro_origem: str | None = None
    confianca_extracao: Decimal
    flags_anomalia: list[str]
    status_revisao: StatusRevisaoLiteral
    ultimo_valor_ativo: Decimal | None = None
    variacao_contra_ativo_pct: Decimal | None = None
    revisado_em: datetime | None = None
    justificativa_revisao: str | None = None
    created_at: datetime


class CollectorStagingListResponse(BaseModel):
    """Fila de quarentena e revisão humana de observações extraídas."""

    model_config = ConfigDict(extra="forbid")

    items: list[CollectorStagingItem]
    total: int
    pendentes_total: int


class CollectorStagingReviewRequest(BaseModel):
    """Justificativa para aprovar ou rejeitar observação auditada (preço imutável)."""

    model_config = ConfigDict(extra="forbid")

    justificativa: str = Field(min_length=5, max_length=500)


class CollectorBulkReviewRequest(BaseModel):
    """Aprovação ou rejeição em lote na fila de quarentena."""

    model_config = ConfigDict(extra="forbid")

    staging_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    acao: Literal["APROVAR", "REJEITAR"]
    justificativa: str = Field(min_length=5, max_length=500)


class CollectorBulkReviewResponse(BaseModel):
    """Resultado consolidado de revisão em lote."""

    model_config = ConfigDict(extra="forbid")

    processados: int
    aprovados: int
    rejeitados: int
