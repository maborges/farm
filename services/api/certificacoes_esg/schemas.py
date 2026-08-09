from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from certificacoes_esg.models import (
    PrioridadePlanoAcao,
    SeveridadeNaoConformidade,
    StatusPassaporte,
    StatusRelatorioESG,
    StatusNaoConformidade,
    StatusPlanoAcao,
    TipoEvidencia,
    TipoEventoPassaporte,
)

FONTES_OFICIAIS_PROIBIDAS = {
    "CAR",
    "MATRICULA",
    "CCIR",
    "ITR",
    "NIRF",
    "SIGEF",
    "AREA_OPERACIONAL",
}


class StatusIntegridade(str, Enum):
    VALIDA = "VALIDA"
    INVALIDA = "INVALIDA"


class IntegridadeResponse(BaseModel):
    integridade: StatusIntegridade
    algoritmo: str | None = None
    hash: str | None = None
    versao: int | None = None
    publicado_em: datetime | None = None


class EvidenciaCertificacaoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programa_id: uuid.UUID
    checklist_id: uuid.UUID | None = None
    criterio_id: uuid.UUID | None = None
    avaliacao_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    tipo_evidencia: TipoEvidencia
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    origem_tipo: str = Field(..., min_length=1, max_length=80)
    origem_id: uuid.UUID
    arquivo_url: str | None = Field(default=None, max_length=2048)
    arquivo_hash: str | None = Field(default=None, max_length=128)
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)
    publico: bool = False

    @model_validator(mode="after")
    def validar_snapshot_origem(self) -> "EvidenciaCertificacaoCreate":
        origem_normalizada = self.origem_tipo.strip().upper()
        if origem_normalizada in FONTES_OFICIAIS_PROIBIDAS:
            raise ValueError("origem_tipo não pode apontar para fonte oficial territorial/fundiária.")
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        if self.arquivo_url is not None and not self.arquivo_hash:
            raise ValueError("arquivo_hash é obrigatório quando arquivo_url existir.")
        return self


class EvidenciaCertificacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    programa_id: uuid.UUID
    checklist_id: uuid.UUID | None = None
    criterio_id: uuid.UUID | None = None
    avaliacao_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    tipo_evidencia: TipoEvidencia
    titulo: str
    descricao: str
    origem_tipo: str
    origem_id: uuid.UUID
    arquivo_url: str | None = None
    arquivo_hash: str | None = None
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = None
    publico: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class NaoConformidadeCertificacaoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programa_id: uuid.UUID
    checklist_id: uuid.UUID | None = None
    criterio_id: uuid.UUID | None = None
    avaliacao_id: uuid.UUID | None = None
    evidencia_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    severidade: SeveridadeNaoConformidade
    status: StatusNaoConformidade = StatusNaoConformidade.ABERTA
    detectada_em: datetime | None = None
    prazo_correcao: datetime | None = None
    resolvida_em: datetime | None = None

    @model_validator(mode="after")
    def validar_datas(self) -> "NaoConformidadeCertificacaoCreate":
        if self.detectada_em and self.prazo_correcao and self.prazo_correcao < self.detectada_em:
            raise ValueError("prazo_correcao deve ser maior ou igual a detectada_em.")
        if self.detectada_em and self.resolvida_em and self.resolvida_em < self.detectada_em:
            raise ValueError("resolvida_em deve ser maior ou igual a detectada_em.")
        return self


class NaoConformidadeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusNaoConformidade
    resolvida_em: datetime | None = None
    prazo_correcao: datetime | None = None


class NaoConformidadeCertificacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    programa_id: uuid.UUID
    checklist_id: uuid.UUID | None = None
    criterio_id: uuid.UUID | None = None
    avaliacao_id: uuid.UUID | None = None
    evidencia_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str
    descricao: str
    severidade: SeveridadeNaoConformidade
    status: StatusNaoConformidade
    detectada_em: datetime
    prazo_correcao: datetime | None = None
    resolvida_em: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PlanoAcaoCertificacaoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programa_id: uuid.UUID
    nao_conformidade_id: uuid.UUID | None = None
    evidencia_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    prioridade: PrioridadePlanoAcao
    status: StatusPlanoAcao = StatusPlanoAcao.PENDENTE
    prazo: datetime | None = None
    concluido_em: datetime | None = None


class PlanoAcaoStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusPlanoAcao
    concluido_em: datetime | None = None


class PlanoAcaoCertificacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    programa_id: uuid.UUID
    nao_conformidade_id: uuid.UUID | None = None
    evidencia_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    titulo: str
    descricao: str
    prioridade: PrioridadePlanoAcao
    status: StatusPlanoAcao
    prazo: datetime
    concluido_em: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RelatorioESGCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str = Field(..., min_length=1, max_length=200)
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    status: StatusRelatorioESG = StatusRelatorioESG.RASCUNHO
    versao: int = 1
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)
    publico: bool = False
    publicado_em: datetime | None = None
    cancelado_em: datetime | None = None

    @model_validator(mode="after")
    def validar_relatorio(self) -> "RelatorioESGCreate":
        if self.periodo_inicio and self.periodo_fim and self.periodo_fim < self.periodo_inicio:
            raise ValueError("periodo_fim deve ser maior ou igual a periodo_inicio.")
        if self.versao < 1:
            raise ValueError("versao deve ser maior ou igual a 1.")
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        if self.status == StatusRelatorioESG.PUBLICADO:
            if self.publicado_em is None:
                raise ValueError("publicado_em é obrigatório quando status for PUBLICADO.")
        if self.status == StatusRelatorioESG.CANCELADO and self.cancelado_em is None:
            raise ValueError("cancelado_em é obrigatório quando status for CANCELADO.")
        return self


class RelatorioESGUpdateStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusRelatorioESG
    publicado_em: datetime | None = None
    cancelado_em: datetime | None = None
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validar_snapshot(self) -> "RelatorioESGUpdateStatus":
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        return self


class RelatorioESGResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    programa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str
    periodo_inicio: datetime | None = None
    periodo_fim: datetime | None = None
    status: StatusRelatorioESG
    versao: int
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = None
    publico: bool
    publicado_em: datetime | None = None
    cancelado_em: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RelatorioESGIndicadorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relatorio_id: uuid.UUID
    evidencia_id: uuid.UUID | None = None
    nome: str = Field(..., min_length=1, max_length=200)
    categoria: str | None = Field(default=None, max_length=120)
    valor: Decimal | None = None
    unidade: str | None = Field(default=None, max_length=40)
    score: Decimal | None = None
    metodologia: str | None = None

    @model_validator(mode="after")
    def validar_numeros(self) -> "RelatorioESGIndicadorCreate":
        if self.valor is not None and self.valor < 0:
            raise ValueError("valor deve ser maior ou igual a 0.")
        if self.score is not None and self.score < 0:
            raise ValueError("score deve ser maior ou igual a 0.")
        return self


class RelatorioESGIndicadorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    relatorio_id: uuid.UUID
    evidencia_id: uuid.UUID | None = None
    nome: str
    categoria: str | None = None
    valor: Decimal | None = None
    unidade: str | None = None
    score: Decimal | None = None
    metodologia: str | None = None
    created_at: datetime
    updated_at: datetime


class RelatorioESGEvidenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relatorio_id: uuid.UUID
    evidencia_id: uuid.UUID


class RelatorioESGEvidenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    relatorio_id: uuid.UUID
    evidencia_id: uuid.UUID
    created_at: datetime


class PassaporteRastreabilidadeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    lote_rastreabilidade_id: uuid.UUID | None = None
    caderno_lote_comercial_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str = Field(..., min_length=1, max_length=200)
    status: StatusPassaporte = StatusPassaporte.RASCUNHO
    versao: int = 1
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)
    publico: bool = False
    publicado_em: datetime | None = None
    revogado_em: datetime | None = None

    @model_validator(mode="after")
    def validar_passaporte(self) -> "PassaporteRastreabilidadeCreate":
        if self.versao < 1:
            raise ValueError("versao deve ser maior ou igual a 1.")
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        if self.status == StatusPassaporte.PUBLICADO:
            if self.publicado_em is None:
                raise ValueError("publicado_em é obrigatório quando status for PUBLICADO.")
        if self.status == StatusPassaporte.REVOGADO and self.revogado_em is None:
            raise ValueError("revogado_em é obrigatório quando status for REVOGADO.")
        return self


class PassaporteRastreabilidadeUpdateStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StatusPassaporte
    publicado_em: datetime | None = None
    revogado_em: datetime | None = None
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)
    publico: bool | None = None
    public_token: uuid.UUID | None = None
    publicado_publicamente_em: datetime | None = None

    @model_validator(mode="after")
    def validar_snapshot(self) -> "PassaporteRastreabilidadeUpdateStatus":
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        return self


class PassaporteRastreabilidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    programa_id: uuid.UUID | None = None
    propriedade_id: uuid.UUID | None = None
    imovel_rural_id: uuid.UUID | None = None
    propriedade_imovel_id: uuid.UUID | None = None
    lote_rastreabilidade_id: uuid.UUID | None = None
    caderno_lote_comercial_id: uuid.UUID | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    titulo: str
    status: StatusPassaporte
    versao: int
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = None
    publico: bool
    public_token: uuid.UUID | None = None
    publicado_em: datetime | None = None
    publicado_publicamente_em: datetime | None = None
    revogado_em: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PassaportePublicoResponse(BaseModel):
    """
    Schema estrito para o endpoint público.
    Não vaza `tenant_id`, referências geográficas ou de usuários.
    """
    model_config = ConfigDict(from_attributes=True)

    public_token: uuid.UUID
    titulo: str
    status: StatusPassaporte
    versao: int
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = None
    publicado_publicamente_em: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def sanitize_snapshot(self) -> "PassaportePublicoResponse":
        if self.snapshot_json:
            sensitive_keys = {
                "tenant_id", "user_id", "created_by", "responsavel_pessoa_id",
                "car", "ccir", "itr", "nirf", "sigef", "matricula"
            }
            # Criamos uma cópia limpa do snapshot
            sanitized = {}
            for k, v in self.snapshot_json.items():
                if not any(sk in k.lower() for sk in sensitive_keys):
                    sanitized[k] = v
            self.snapshot_json = sanitized
        return self



class PassaporteRastreabilidadeEventoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passaporte_id: uuid.UUID
    tipo_evento: TipoEventoPassaporte
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    ocorrido_em: datetime
    origem_tipo: str = Field(..., min_length=1, max_length=80)
    origem_id: uuid.UUID
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validar_snapshot(self) -> "PassaporteRastreabilidadeEventoCreate":
        if self.snapshot_json is not None and not self.snapshot_hash:
            raise ValueError("snapshot_hash é obrigatório quando snapshot_json existir.")
        return self


class PassaporteRastreabilidadeEventoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    passaporte_id: uuid.UUID
    tipo_evento: TipoEventoPassaporte
    titulo: str
    descricao: str
    ocorrido_em: datetime
    origem_tipo: str
    origem_id: uuid.UUID
    snapshot_json: dict[str, Any] | None = None
    snapshot_hash: str | None = None
    created_at: datetime


class PassaporteRastreabilidadeEvidenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passaporte_id: uuid.UUID
    evidencia_id: uuid.UUID


class PassaporteRastreabilidadeEvidenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    passaporte_id: uuid.UUID
    evidencia_id: uuid.UUID
    created_at: datetime
