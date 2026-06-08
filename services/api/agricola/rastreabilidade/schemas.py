from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date

class LoteRastreabilidadeBase(BaseModel):
    codigo_lote: str
    safra_id: UUID
    talhao_id: UUID
    produto: str
    variedade: Optional[str] = None
    quantidade_total: float
    unidade: str = "KG"
    certificacoes: List[str] = []
    observacoes: Optional[str] = None

class LoteRastreabilidadeCreate(LoteRastreabilidadeBase):
    pass

class LoteRastreabilidadeResponse(LoteRastreabilidadeBase):
    id: UUID
    data_geracao: datetime
    qr_code_url: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CertificacaoBase(BaseModel):
    unidade_produtiva_id: UUID
    nome: str
    extensao: Optional[str] = None
    data_emissao: date
    data_validade: date
    orgao_certificador: Optional[str] = None
    numero_registro: Optional[str] = None
    link_documento: Optional[str] = None

class CertificacaoCreate(CertificacaoBase):
    pass

class CertificacaoResponse(CertificacaoBase):
    id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoteComercialCreate(BaseModel):
    comercializacao_id: UUID
    codigo_lote: str
    peso_liquido_kg: float
    quantidade_volumes: int
    produto_colhido_id: Optional[UUID] = None
    lote_beneficiamento_id: Optional[UUID] = None


class LoteComercialResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    comercializacao_id: UUID
    produto_colhido_id: Optional[UUID] = None
    lote_beneficiamento_id: Optional[UUID] = None
    codigo_lote: str
    qr_code_token: str
    peso_liquido_kg: float
    quantidade_volumes: int
    status: str
    snapshot_json: Optional[dict] = None
    snapshot_hash: Optional[str] = None
    snapshot_gerado_em: Optional[datetime] = None
    assinado_por_usuario_id: Optional[UUID] = None
    assinado_em: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
