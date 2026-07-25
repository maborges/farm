from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime


# ── Departamento ──────────────────────────────────────────────────────────────

class DepartamentoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    responsavel_nome: Optional[str] = None


class DepartamentoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    responsavel_nome: Optional[str] = None
    ativo: Optional[bool] = None


class DepartamentoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nome: str
    descricao: Optional[str]
    responsavel_nome: Optional[str]
    ativo: bool
    created_at: datetime
    total_colaboradores: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── eSocial ───────────────────────────────────────────────────────────────────

class EsocialEventoCreate(BaseModel):
    colaborador_id: Optional[UUID] = None
    colaborador_nome: Optional[str] = None
    tipo_evento: str
    periodo_apuracao: Optional[str] = None
    xml_enviado: Optional[str] = None


class EsocialEventoUpdate(BaseModel):
    status: Optional[str] = None
    numero_recibo: Optional[str] = None
    codigo_erro: Optional[str] = None
    descricao_erro: Optional[str] = None
    enviado_em: Optional[datetime] = None


class EsocialEventoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    colaborador_id: Optional[UUID]
    colaborador_nome: Optional[str]
    tipo_evento: str
    status: str
    numero_recibo: Optional[str]
    codigo_erro: Optional[str]
    descricao_erro: Optional[str]
    periodo_apuracao: Optional[str]
    enviado_em: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Colaborador ───────────────────────────────────────────────────────────────

class ColaboradorCreate(BaseModel):
    pessoa_id: UUID
    cargo: Optional[str] = None
    tipo_contrato: str = "DIARISTA"
    valor_diaria: Optional[float] = None
    valor_hora: Optional[float] = None
    data_admissao: Optional[date] = None
    unidade_produtiva_id: Optional[UUID] = None
    observacoes: Optional[str] = None


class ColaboradorResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    pessoa_id: UUID
    # Sempre resolvidos a partir de Pessoa/PessoaDocumento — nunca duplicados
    # na tabela rh_colaboradores (ver rh/service.py: obter_dados_exibicao_colaborador).
    nome: Optional[str] = None
    cpf: Optional[str] = None
    cargo: Optional[str] = None
    tipo_contrato: str
    valor_diaria: Optional[float] = None
    valor_hora: Optional[float] = None
    data_admissao: Optional[date] = None
    unidade_produtiva_id: Optional[UUID] = None
    observacoes: Optional[str] = None
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Diária ────────────────────────────────────────────────────────────────────

class DiariaCreate(BaseModel):
    colaborador_id: UUID
    data: date
    horas_trabalhadas: float = 8.0
    atividade: str = "GERAL"
    valor_diaria: float = Field(..., gt=0)
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    observacoes: Optional[str] = None


class DiariaResponse(DiariaCreate):
    id: UUID
    tenant_id: UUID
    status: str
    data_pagamento: Optional[date]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PagarDiariasRequest(BaseModel):
    ids: List[UUID]
    data_pagamento: Optional[date] = None


# ── Empreitada ────────────────────────────────────────────────────────────────

class EmpreitadaCreate(BaseModel):
    colaborador_id: UUID
    descricao: str
    unidade: str = "HECTARE"
    quantidade: float = Field(..., gt=0)
    valor_unitario: float = Field(..., gt=0)
    data_inicio: date
    data_fim: Optional[date] = None
    unidade_produtiva_id: Optional[UUID] = None
    safra_id: Optional[UUID] = None
    observacoes: Optional[str] = None


class EmpreitadaResponse(EmpreitadaCreate):
    id: UUID
    tenant_id: UUID
    valor_total: float
    status: str
    data_pagamento: Optional[date]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConcluirEmpreitadaRequest(BaseModel):
    quantidade_final: Optional[float] = None
    data_fim: Optional[date] = None


# ── Dashboard RH ──────────────────────────────────────────────────────────────

class DashboardRHResponse(BaseModel):
    total_colaboradores_ativos: int
    total_diaristas: int
    total_empreiteiros: int
    gasto_diarias_mes: float
    gasto_empreitadas_mes: float
    total_pendente_diarias: float
    total_pendente_empreitadas: float
    empreitadas_abertas: int


# ── Segurança do Trabalho ────────────────────────────────────────────────────

class ItemSegurancaCreate(BaseModel):
    nome: str
    tipo: str = Field(default="EPI")
    ca_numero: Optional[str] = None
    validade_dias: Optional[int] = None
    fornecedor: Optional[str] = None
    observacoes: Optional[str] = None


class ItemSegurancaResponse(ItemSegurancaCreate):
    id: UUID
    tenant_id: UUID
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntregaSegurancaCreate(BaseModel):
    colaborador_id: UUID
    item_id: UUID
    data_entrega: date
    data_validade: Optional[date] = None
    quantidade: float = 1.0
    unidade_produtiva_id: Optional[UUID] = None
    termo_assinado_url: Optional[str] = None
    observacoes: Optional[str] = None


class EntregaSegurancaResponse(EntregaSegurancaCreate):
    id: UUID
    tenant_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentoSSTCreate(BaseModel):
    colaborador_id: Optional[UUID] = None
    tipo: str
    numero: Optional[str] = None
    data_emissao: date
    data_vencimento: Optional[date] = None
    arquivo_url: Optional[str] = None
    observacoes: Optional[str] = None


class DocumentoSSTResponse(DocumentoSSTCreate):
    id: UUID
    tenant_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumoSegurancaResponse(BaseModel):
    total_itens_ativos: int
    total_entregas_ativas: int
    total_documentos_ativos: int
    documentos_vencendo_30d: int
    documentos_vencidos: int
