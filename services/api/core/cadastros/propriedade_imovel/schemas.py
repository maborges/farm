from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import TipoVinculoPropriedadeImovel


class PropriedadeResumo(BaseModel):
    """Resumo enxuto da Propriedade para resposta do vínculo."""

    id: uuid.UUID
    nome: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ImovelRuralResumo(BaseModel):
    """Resumo enxuto do Imóvel Rural para resposta do vínculo."""

    id: uuid.UUID
    nome: str
    municipio: str
    uf: str

    model_config = ConfigDict(from_attributes=True)


class PropriedadeImovelBase(BaseModel):
    """Campos compartilhados do vínculo canônico."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    propriedade_id: uuid.UUID
    imovel_rural_id: uuid.UUID
    tipo_vinculo: TipoVinculoPropriedadeImovel
    ativo: bool = True
    data_inicio: date
    data_fim: Optional[date] = None
    origem_documental: str = Field(..., min_length=1)
    observacoes: Optional[str] = None
    area_vinculada: Optional[Decimal] = None
    percentual_vinculado: Optional[Decimal] = None
    vinculo_principal: bool = False
    origem_referencia: Optional[str] = None
    status_documental: Optional[str] = None

    @field_validator("origem_documental", "origem_referencia", "observacoes")
    @classmethod
    def _normalizar_texto(cls, value: Optional[str]) -> Optional[str]:
        """Remove espaços vazios e bloqueia strings em branco."""
        if value is None:
            return None
        texto = value.strip()
        if not texto:
            raise ValueError("Campo textual não pode ser vazio.")
        return texto

    @field_validator("area_vinculada")
    @classmethod
    def _validar_area(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        """Garante área não negativa."""
        if value is not None and value < 0:
            raise ValueError("area_vinculada não pode ser negativa.")
        return value

    @field_validator("percentual_vinculado")
    @classmethod
    def _validar_percentual(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        """Garante percentual entre 0 e 100."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("percentual_vinculado deve estar entre 0 e 100.")
        return value

    @model_validator(mode="after")
    def _validar_datas(self):
        """Garante que data_fim não seja anterior à data_inicio."""
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser maior ou igual a data_inicio.")
        return self


class PropriedadeImovelCreate(PropriedadeImovelBase):
    """Payload de criação do vínculo."""


class PropriedadeImovelUpdate(BaseModel):
    """Payload parcial de atualização do vínculo."""

    propriedade_id: Optional[uuid.UUID] = None
    imovel_rural_id: Optional[uuid.UUID] = None
    tipo_vinculo: Optional[TipoVinculoPropriedadeImovel] = None
    ativo: Optional[bool] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    origem_documental: Optional[str] = None
    observacoes: Optional[str] = None
    area_vinculada: Optional[Decimal] = None
    percentual_vinculado: Optional[Decimal] = None
    vinculo_principal: Optional[bool] = None
    origem_referencia: Optional[str] = None
    status_documental: Optional[str] = None

    @field_validator("origem_documental", "origem_referencia", "observacoes")
    @classmethod
    def _normalizar_texto(cls, value: Optional[str]) -> Optional[str]:
        """Remove espaços vazios e bloqueia strings em branco."""
        if value is None:
            return None
        texto = value.strip()
        if not texto:
            raise ValueError("Campo textual não pode ser vazio.")
        return texto

    @field_validator("area_vinculada")
    @classmethod
    def _validar_area(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        """Garante área não negativa."""
        if value is not None and value < 0:
            raise ValueError("area_vinculada não pode ser negativa.")
        return value

    @field_validator("percentual_vinculado")
    @classmethod
    def _validar_percentual(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        """Garante percentual entre 0 e 100."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("percentual_vinculado deve estar entre 0 e 100.")
        return value

    @model_validator(mode="after")
    def _validar_datas(self):
        """Garante que data_fim não seja anterior à data_inicio quando ambos forem enviados."""
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser maior ou igual a data_inicio.")
        return self


class PropriedadeImovelRead(PropriedadeImovelBase):
    """Representação completa do vínculo para leitura."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    propriedade: Optional[PropriedadeResumo] = None
    imovel_rural: Optional[ImovelRuralResumo] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class PropriedadeImovelList(PropriedadeImovelRead):
    """Schema de listagem do vínculo."""
