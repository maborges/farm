from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PropriedadeVisaoResumo(BaseModel):
    id: uuid.UUID
    nome: str
    ativo: bool
    cpf_cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AreaOperacionalResumo(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    tipo: str
    nome: str
    codigo: Optional[str] = None
    area_hectares: Optional[Decimal] = None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ExploracaoRuralResumo(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    propriedade_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    natureza: str
    data_inicio: date
    data_fim: Optional[date] = None
    numero_contrato: Optional[str] = None
    valor_anual: Optional[Decimal] = None
    percentual_producao: Optional[Decimal] = None
    area_explorada_ha: Optional[Decimal] = None
    ativo: bool
    observacoes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CartorioResumo(BaseModel):
    id: uuid.UUID
    nome: str
    comarca: str
    uf: str

    model_config = ConfigDict(from_attributes=True)


class DocumentoFundiarioResumo(BaseModel):
    id: uuid.UUID
    tipo: str
    descricao: Optional[str] = None
    numero_documento: Optional[str] = None
    status: str
    versao: int
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    restrito: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatriculaFundiariaResumo(BaseModel):
    id: uuid.UUID
    numero_matricula: str
    cartorio_nome: Optional[str] = None
    area_matricula_ha: Optional[Decimal] = None
    data_transmissao: Optional[date] = None
    tipo_transmissao: Optional[str] = None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ImovelFundiarioResumo(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    municipio: str
    uf: str
    area_total_ha: Decimal
    area_app_ha: Optional[Decimal] = None
    area_rl_ha: Optional[Decimal] = None
    nirf: Optional[str] = None
    car_numero: Optional[str] = None
    ccir_numero: Optional[str] = None
    numero_matricula: Optional[str] = None
    cartorio: Optional[CartorioResumo] = None
    documentos_resumo: list[DocumentoFundiarioResumo] = Field(default_factory=list)
    matriculas_resumo: list[MatriculaFundiariaResumo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VinculoTerritorialResumo(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tipo_vinculo: str
    ativo: bool
    data_inicio: date
    data_fim: Optional[date] = None
    area_vinculada: Optional[Decimal] = None
    percentual_vinculado: Optional[Decimal] = None
    vinculo_principal: bool
    origem_documental: str
    origem_referencia: Optional[str] = None
    status_documental: Optional[str] = None
    propriedade: Optional[PropriedadeVisaoResumo] = None
    imovel_rural: Optional[ImovelFundiarioResumo] = None

    model_config = ConfigDict(from_attributes=True)


class VisaoTerritorialRead(BaseModel):
    propriedade: PropriedadeVisaoResumo
    areas_operacionais: list[AreaOperacionalResumo] = Field(default_factory=list)
    exploracoes_rurais: list[ExploracaoRuralResumo] = Field(default_factory=list)
    imoveis_rurais: list[ImovelFundiarioResumo] = Field(default_factory=list)
    vinculos: list[VinculoTerritorialResumo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VisaoFundiariaRead(BaseModel):
    imovel_rural: ImovelFundiarioResumo
    propriedades_vinculadas: list[PropriedadeVisaoResumo] = Field(default_factory=list)
    vinculos: list[VinculoTerritorialResumo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

