from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from typing import Optional, Literal, Any


TipoEventoCaderno = Literal[
    "PLANTIO",
    "PULVERIZACAO",
    "APLICACAO",
    "IRRIGACAO",
    "COLHEITA",
    "INSPECAO",
    "OCORRENCIA",
    "MANUTENCAO",
    "ABASTECIMENTO",
    "EXECUCAO_OPERACIONAL",
    "MONITORAMENTO",
    "VISITA_TECNICA",
    "EPI_ENTREGA",
    "OBSERVACAO",
    "CLIMA",
    "SOLO",
]

OrigemEventoCaderno = Literal[
    "OPERACAO_AGRICOLA",
    "WEB_MANUAL",
    "PWA_OFFLINE",
    "IMPORTACAO",
    "SISTEMA",
]

OrigemTecnicaCaderno = Literal[
    "OPERACAO_AUTO",
    "MANUAL_DIGITAL",
    "SYNC_PWA",
    "IMPORTACAO",
    "SISTEMA",
]

StatusEventoCaderno = Literal[
    "RASCUNHO",
    "PENDENTE_SINCRONIZACAO",
    "SINCRONIZADO",
    "PENDENTE_APROVACAO",
    "APROVADO",
    "REJEITADO",
    "CONSOLIDADO",
    "CANCELADO",
]


# ─── Fotos ────────────────────────────────────────────────────────────────────

class FotoResponse(BaseModel):
    id: UUID
    url: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_captura: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Entradas ─────────────────────────────────────────────────────────────────

class EntradaCreate(BaseModel):
    safra_id: UUID
    talhao_id: UUID
    tipo: str
    tipo_evento: Optional[TipoEventoCaderno] = None
    descricao: str
    data_registro: date
    origem_evento: Optional[OrigemEventoCaderno] = None
    origem_id: Optional[str] = None
    origem_tecnica: Optional[OrigemTecnicaCaderno] = None
    status_evento: Optional[StatusEventoCaderno] = None
    nivel_severidade: Optional[str] = None
    recomendacao: Optional[str] = None
    numero_receituario: Optional[str] = None
    digitalizacao_retroativa: bool = False
    justificativa_retroativa: Optional[str] = None


class EntradaUpdate(BaseModel):
    descricao: Optional[str] = None
    tipo_evento: Optional[TipoEventoCaderno] = None
    nivel_severidade: Optional[str] = None
    recomendacao: Optional[str] = None
    numero_receituario: Optional[str] = None
    status_evento: Optional[StatusEventoCaderno] = None


class ReprocessarEntradaRequest(BaseModel):
    motivo: str = Field(..., min_length=5, max_length=500)
    dados_corrigidos: dict[str, Any] = Field(default_factory=dict)


class EntradaDeleteRequest(BaseModel):
    motivo_exclusao: str = Field(..., min_length=10)


class EntradaResponse(BaseModel):
    id: UUID
    safra_id: UUID
    talhao_id: UUID
    tipo: str
    tipo_evento: Optional[str] = None
    descricao: str
    data_registro: date
    usuario_id: UUID
    operacao_id: Optional[UUID] = None
    origem_evento: Optional[str] = None
    origem_id: Optional[str] = None
    origem_tecnica: Optional[str] = None
    status_evento: Optional[str] = None
    status_evento_atualizado_em: Optional[datetime] = Field(default=None, validation_alias="updated_at")
    nivel_severidade: Optional[str] = None
    recomendacao: Optional[str] = None
    numero_receituario: Optional[str] = None
    excluida: bool
    motivo_exclusao: Optional[str] = None
    digitalizacao_retroativa: bool
    retifica_evento_id: Optional[UUID] = None
    retificado_por_evento_id: Optional[UUID] = None
    motivo_retificacao: Optional[str] = None
    retificado_em: Optional[datetime] = None
    retificado_por_usuario_id: Optional[UUID] = None
    fotos: list[FotoResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Visita Técnica ───────────────────────────────────────────────────────────

class VisitaTecnicaCreate(BaseModel):
    safra_id: UUID
    talhao_id: UUID
    nome_rt: str
    crea: str
    data_visita: date
    observacoes: Optional[str] = None
    recomendacoes: Optional[str] = None
    constatacoes: list[dict] = []


class VisitaTecnicaResponse(BaseModel):
    id: UUID
    safra_id: UUID
    talhao_id: UUID
    nome_rt: str
    crea: str
    data_visita: date
    observacoes: Optional[str] = None
    recomendacoes: Optional[str] = None
    constatacoes: list[dict] = []
    assinado: bool
    data_assinatura: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssinarVisitaRequest(BaseModel):
    nome_rt: str
    crea: str


# ─── EPI Entrega ──────────────────────────────────────────────────────────────

class EPIEntregaCreate(BaseModel):
    nome_trabalhador: str
    trabalhador_id: Optional[UUID] = None
    epi_tipo: str
    quantidade: int = 1
    data_entrega: date
    validade: Optional[date] = None
    operacao_id: Optional[UUID] = None


class EPIEntregaResponse(BaseModel):
    id: UUID
    nome_trabalhador: str
    epi_tipo: str
    quantidade: int
    data_entrega: date
    validade: Optional[date] = None
    assinatura_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Exportação ───────────────────────────────────────────────────────────────

ModeloCertificacao = Literal["padrao", "globalgap", "organico", "mapa"]


class ExportacaoCreate(BaseModel):
    safra_id: UUID
    talhao_id: Optional[UUID] = None
    modelo: ModeloCertificacao = "padrao"  # padrao | globalgap | organico | mapa
    modelo_certificacao: Optional[str] = None  # legado — mapeado internamente
    modo_exportacao: Optional[Literal["OFICIAL", "AUDITORIA"]] = "OFICIAL"
    assinado_por: Optional[str] = None
    crea_rt: Optional[str] = None


class ExportacaoResponse(BaseModel):
    id: UUID
    safra_id: UUID
    url_pdf: str
    data_geracao: datetime
    modo_exportacao: str
    hash_documental: Optional[str] = None
    assinatura_hash: Optional[str] = None
    responsavel_tecnico_id: Optional[UUID] = None
    responsavel_tecnico_nome: Optional[str] = None
    responsavel_tecnico_crea: Optional[str] = None
    assinado_por: Optional[str] = None
    crea_rt: Optional[str] = None
    crea_validade: Optional[date] = None
    assinado_em: Optional[datetime] = None
    assinatura_origem: Optional[str] = None
    observacao_assinatura: Optional[str] = None
    modelo_certificacao: str

    model_config = {"from_attributes": True}


class AssinarExportacaoRequest(BaseModel):
    safra_id: Optional[UUID] = None
    responsavel_tecnico_id: Optional[UUID] = None
    responsavel_tecnico_nome: Optional[str] = Field(default=None, min_length=3, max_length=200)
    assinado_por: Optional[str] = Field(default=None, min_length=3, max_length=200)
    crea_rt: Optional[str] = Field(default=None, min_length=4, max_length=30)
    crea_validade: Optional[date] = None  # Data de validade do CREA
    observacao: Optional[str] = Field(default=None, max_length=500)


# ─── Timeline (agregada) ──────────────────────────────────────────────────────

class TimelineItem(BaseModel):
    id: UUID
    tipo: str
    tipo_evento: Optional[str] = None
    subtipo: Optional[str] = None  # para diferenciar entrada manual de operação auto
    descricao: str
    data_registro: date
    talhao_id: UUID
    origem_evento: Optional[str] = None
    origem_id: Optional[str] = None
    origem_tecnica: Optional[str] = None
    status_evento: Optional[str] = None
    status_evento_atualizado_em: Optional[datetime] = None
    pendente_aprovacao: bool = False
    aprovado: bool = False
    consolidado: bool = False
    rejeitado: bool = False
    nivel_severidade: Optional[str] = None
    fotos_count: int = 0
    excluida: bool = False
    origem: str  # "caderno" | "operacao" | "visita"
    retifica_evento_id: Optional[UUID] = None
    retificado_por_evento_id: Optional[UUID] = None
    motivo_retificacao: Optional[str] = None
    retificado_em: Optional[datetime] = None
    retificado_por_usuario_id: Optional[UUID] = None
    versao_vigente: bool = False
    retificado: bool = False
    retificador: bool = False


class EvidenciaOfflinePayload(BaseModel):
    tipo: str
    url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_captura: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventoCadernoOfflinePayload(BaseModel):
    local_id: str
    tenant_id: UUID
    safra_id: UUID
    talhao_id: UUID
    tipo_evento: TipoEventoCaderno
    status: StatusEventoCaderno = "PENDENTE_SINCRONIZACAO"
    client_created_at: datetime
    device_id: str
    origem_evento: OrigemEventoCaderno = "PWA_OFFLINE"
    origem_tecnica: OrigemTecnicaCaderno = "SYNC_PWA"
    evidencias: list[EvidenciaOfflinePayload] = Field(default_factory=list)
    payload_operacional: dict[str, Any] = Field(default_factory=dict)


class StatusEventoUpdateRequest(BaseModel):
    status_evento: StatusEventoCaderno
    justificativa: Optional[str] = None


class StatusEventoHistoricoResponse(BaseModel):
    id: UUID
    caderno_entrada_id: UUID
    status_anterior: Optional[str] = None
    status_novo: str
    usuario_id: Optional[UUID] = None
    justificativa: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
