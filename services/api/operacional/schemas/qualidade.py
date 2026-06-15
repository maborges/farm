from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Literal

# --- Protocolos ---
class QualidadeCriterioBase(BaseModel):
    nome: str
    tipo_dado: Literal["NUMERIC", "ENUM", "BOOLEAN"]
    unidade: Optional[str] = None
    min_aceitavel: Optional[float] = None
    max_aceitavel: Optional[float] = None
    valor_padrao: Optional[float] = None
    regra_ajuste_json: Optional[dict] = None

class QualidadeCriterioCreate(QualidadeCriterioBase):
    pass

class QualidadeCriterioResponse(QualidadeCriterioBase):
    id: UUID
    protocolo_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualidadeProtocoloBase(BaseModel):
    nome: str
    commodity_id: Optional[UUID] = None
    ativo: bool = True

class QualidadeProtocoloCreate(QualidadeProtocoloBase):
    criterios: List[QualidadeCriterioCreate] = Field(default_factory=list)

class QualidadeProtocoloResponse(QualidadeProtocoloBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    criterios: List[QualidadeCriterioResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Laudos e Resultados ---
class QualidadeResultadoBase(BaseModel):
    criterio_id: UUID
    valor_numerico: Optional[float] = None
    valor_texto: Optional[str] = None

class QualidadeResultadoCreate(QualidadeResultadoBase):
    pass

class QualidadeResultadoResponse(QualidadeResultadoBase):
    id: UUID
    laudo_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualidadeAjusteBase(BaseModel):
    tipo: Literal["DISCOUNT_WEIGHT", "DISCOUNT_FINANCIAL", "PREMIUM_FINANCIAL", "REJECTION"]
    valor_numerico: float
    valor_unidade: Optional[str] = None
    motivo: str
    metadata_json: Optional[dict] = None

class QualidadeAjusteResponse(QualidadeAjusteBase):
    id: UUID
    laudo_id: UUID
    criterio_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
class QualidadeLaudoBase(BaseModel):
    unidade_produtiva_id: Optional[UUID] = None
    protocolo_id: UUID
    romaneio_id: Optional[UUID] = None
    avaliador_id: Optional[UUID] = None
    status: Literal["RASCUNHO", "CONCLUIDO", "APROVADO", "REJEITADO"] = "RASCUNHO"

class QualidadeLaudoStatusUpdate(BaseModel):
    status: Literal["APROVADO", "REJEITADO"]
    avaliador_id: Optional[UUID] = None

class QualidadeLaudoCreate(QualidadeLaudoBase):
    resultados: List[QualidadeResultadoCreate] = Field(default_factory=list)

class QualidadeLaudoResponse(QualidadeLaudoBase):
    id: UUID
    tenant_id: UUID
    data_avaliacao: datetime
    created_at: datetime
    updated_at: datetime
    resultados: List[QualidadeResultadoResponse] = Field(default_factory=list)
    ajustes: List[QualidadeAjusteResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class QualidadeRomaneioIntegrationResponse(BaseModel):
    romaneio_id: UUID
    laudo_id: UUID
    peso_liquido_padrao_kg: float | None = None
    peso_liquido_kg: float | None = None
    peso_desconto_qualidade_kg: float
    peso_liquido_comercial_kg: float | None = None
    status_qualidade: str | None = None
    ajustes_aplicados: int
