"""Contratos Pydantic v2 e constantes canônicas do coletor multi-fonte."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from public_mercado.precos_publicos import METADADOS_CATALOGO
from public_mercado.sidra import UFS

DomainLiteral = Literal["MERCADO", "CLIMA", "INSUMOS", "CONJUNTURA"]
TipoLicencaLiteral = Literal[
    "DADO_PUBLICO_GOV",
    "PARCEIRO_AUTORIZADO",
    "LINK_HOMOLOGADO_APENAS",
]
EstrategiaColetaLiteral = Literal[
    "NIVEL1_DETERMINISTICO",
    "NIVEL2_IA_PDF_HTML",
    "GENERICO_PARCEIRO",
]
AutoPublishPolicyLiteral = Literal["AUTO_SE_GUARDRAILS_OK", "SEMPRE_REVISAO_HUMANA"]
RunStatusLiteral = Literal["SUCESSO", "PARCIAL", "QUARENTENA", "SKIPPED_UNCHANGED", "FALHA"]
TriggerTipoLiteral = Literal["AGENDADO", "MANUAL", "REPROCESSAMENTO"]
StatusRevisaoLiteral = Literal["PENDENTE_REVISAO", "APROVADO", "REJEITADO", "AUTO_APROVADO"]
PeriodicidadeLiteral = Literal["DIARIA", "SEMANAL", "MENSAL"]

CANONICAL_COMMODITY_IDS: frozenset[str] = frozenset(
    str(meta["id"]) for meta in METADADOS_CATALOGO
)
CANONICAL_UNITS_BY_COMMODITY: dict[str, str] = {
    str(meta["id"]): str(meta["defaultUnidade"]) for meta in METADADOS_CATALOGO
}
VALID_UFS: frozenset[str] = frozenset([sigla for sigla, _nome in UFS.values()] + ["BR"])


class FetchResult(BaseModel):
    """Resultado sanitizado e verificado de um download HTTP institucional."""

    model_config = ConfigDict(extra="forbid")

    url_efetiva: str
    http_status: int
    content: bytes = b""
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    sha256: str = ""
    tamanho_bytes: int = 0
    not_modified: bool = False
    filename: str = "payload.bin"


class RawObservation(BaseModel):
    """Observação bruta extraída de um documento ou tabela de origem."""

    model_config = ConfigDict(extra="forbid")

    commodity_id: str
    uf: str = Field(min_length=2, max_length=2)
    praca: str = Field(min_length=1, max_length=120)
    tipo_preco: str = Field(min_length=1, max_length=50)
    periodicidade: PeriodicidadeLiteral
    data_referencia: date
    valor_original: Decimal
    unidade_original: str = Field(min_length=1, max_length=60)
    unidade_destino: str | None = None
    moeda: str = Field(default="BRL", min_length=3, max_length=3)
    trecho_evidencia: str = Field(min_length=1)
    registro_origem: str | None = Field(default=None, max_length=120)
    confianca_extracao: Decimal = Decimal("1.000")
    documento_oficial: str | None = None
    is_media_estadual: bool = False


class ValidatedObservation(BaseModel):
    """Observação após normalização determinística de unidade e guardrails."""

    model_config = ConfigDict(extra="forbid")

    raw: RawObservation
    valor_normalizado: Decimal
    unidade_normalizada: str
    fator_conversao: Decimal
    transformacao_aplicada: str | None = None
    flags_anomalia: list[str] = Field(default_factory=list)
    bloqueado_para_publicacao: bool = False
    variacao_anterior_abs: Decimal | None = None
    variacao_anterior_pct: Decimal | None = None


class CollectorExecutionPayload(BaseModel):
    """Saída padronizada de um coletor após coleta + extração determinística."""

    model_config = ConfigDict(extra="forbid")

    fetch_result: FetchResult
    observations: list[RawObservation] = Field(default_factory=list)
    raw_text_for_evidence: str | None = None
    modelo_ia: str | None = None
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_estimado_usd: Decimal = Decimal("0")


class CollectorRunSummary(BaseModel):
    """Resumo operacional persistido de uma execução do orquestrador."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    source_slug: str
    status: RunStatusLiteral
    skipped_unchanged: bool = False
    total_extraidos: int = 0
    total_publicados: int = 0
    total_quarentena: int = 0
    total_rejeitados: int = 0
    erro_resumo: str | None = None
    sugestao_sentinela: dict[str, Any] | None = None
