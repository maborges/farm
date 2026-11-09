from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime

class PlanoAssinaturaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    descricao_marketing: Optional[str] = None
    modulos_inclusos: List[str] = ["CORE"]
    limite_usuarios_minimo: int = 1
    limite_usuarios_maximo: Optional[int] = None
    limite_hectares: Optional[float] = None
    max_fazendas: int = 1
    max_categorias_plano: int = 200
    plan_tier: str = "ENTERPRISE"
    preco_mensal: float = 0.0
    preco_anual: float = 0.0
    destaque: bool = False
    ordem: int = 0
    ativo: bool = True
    is_default: bool = False
    disponivel_site: bool = False
    disponivel_crm: bool = True

class PlanoAssinaturaCreate(PlanoAssinaturaBase):
    pass

class PlanoAssinaturaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    descricao_marketing: Optional[str] = None
    modulos_inclusos: Optional[List[str]] = None
    limite_usuarios_minimo: Optional[int] = None
    limite_usuarios_maximo: Optional[int] = None
    limite_hectares: Optional[float] = None
    max_fazendas: Optional[int] = None
    max_categorias_plano: Optional[int] = None
    plan_tier: Optional[str] = None
    preco_mensal: Optional[float] = None
    preco_anual: Optional[float] = None
    destaque: Optional[bool] = None
    ordem: Optional[int] = None
    ativo: Optional[bool] = None
    is_default: Optional[bool] = None
    disponivel_site: Optional[bool] = None
    disponivel_crm: Optional[bool] = None

class PlanoAssinaturaResponse(PlanoAssinaturaBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LandingPlanoResponse(BaseModel):
    """Dados comerciais publicados no catálogo público da landing page."""

    id: uuid.UUID
    nome: str
    descricao: Optional[str] = None
    descricao_marketing: Optional[str] = None
    modulos_inclusos: List[str] = []
    limite_usuarios_minimo: int = 1
    limite_usuarios_maximo: Optional[int] = None
    limite_hectares: Optional[float] = None
    max_fazendas: int = 1
    preco_mensal: float = 0.0
    preco_anual: float = 0.0
    plan_tier: str = "ENTERPRISE"
    tem_trial: bool = True
    dias_trial: int = 15
    is_free: bool = False
    destaque: bool = False
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class SimulacaoOrcamentoPublicoRequest(BaseModel):
    """Payload para simulação pública de pacote, licenças simultâneas e Hectares Equivalentes."""

    area_total_ha: float = 100.0
    area_ambiental_ha: float = 0.0
    vocacao_predominante: str = "GRAOS"
    cabecas_pecuaria: int = 0
    quantidade_usuarios: int = 1
    dispositivos_campo: int = 0
    plano_id: Optional[uuid.UUID] = None
    talhoes_culturas: Optional[List[dict]] = None

class FaturaResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_nome: Optional[str] = None
    plano_nome: Optional[str] = None
    valor: float
    data_vencimento: datetime
    status: str
    url_comprovante: Optional[str] = None
    data_envio_comprovante: Optional[datetime] = None
    justificativa_rejeicao: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewInvoiceRequest(BaseModel):
    aprovado: bool
    justificativa: Optional[str] = None
