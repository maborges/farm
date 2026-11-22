from datetime import datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import UNIDADES_PESO_FIXO, UNIDADES_SEM_PESO_FIXO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_codigo_format(value: str) -> str:
    """Valida e normaliza o código da commodity."""
    if not value or not value.strip():
        raise ValueError("Código é obrigatório")
    if " " in value:
        raise ValueError("Código não pode conter espaços")
    return value.upper().strip()


# ---------------------------------------------------------------------------
# Commodity
# ---------------------------------------------------------------------------

class CommodityCreate(BaseModel):
    nome: str
    codigo: str
    descricao: Optional[str] = None
    tipo: str
    unidade_padrao: str
    peso_unidade: Optional[float] = None
    umidade_padrao_pct: Optional[float] = None
    impureza_padrao_pct: Optional[float] = None
    possui_cotacao: bool = False
    bolsa_referencia: Optional[str] = None
    codigo_bolsa: Optional[str] = None
    ativo: bool = True

    @field_validator("codigo")
    @classmethod
    def codigo_upper(cls, v: str) -> str:
        return _validate_codigo_format(v)

    @model_validator(mode="after")
    def validate_peso_unidade(self):
        if self.unidade_padrao in UNIDADES_PESO_FIXO:
            if self.peso_unidade is None:
                raise ValueError(
                    f"peso_unidade é obrigatório para unidade {self.unidade_padrao}"
                )
        elif self.unidade_padrao in UNIDADES_SEM_PESO_FIXO:
            if self.peso_unidade is not None:
                raise ValueError(
                    f"peso_unidade não deve ser usado com unidade {self.unidade_padrao}"
                )
        return self


class CommodityUpdate(BaseModel):
    nome: Optional[str] = None
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    unidade_padrao: Optional[str] = None
    peso_unidade: Optional[float] = None
    umidade_padrao_pct: Optional[float] = None
    impureza_padrao_pct: Optional[float] = None
    possui_cotacao: Optional[bool] = None
    bolsa_referencia: Optional[str] = None
    codigo_bolsa: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("codigo")
    @classmethod
    def codigo_upper(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_codigo_format(v)
        return v

    @model_validator(mode="after")
    def validate_peso_unidade(self):
        unidade = self.unidade_padrao
        peso = self.peso_unidade
        # Só valida se ambos foram informados
        if unidade is not None and peso is not None:
            if unidade in UNIDADES_SEM_PESO_FIXO:
                raise ValueError(
                    f"peso_unidade não deve ser usado com unidade {unidade}"
                )
        return self


class CommodityResponse(BaseModel):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID]
    sistema: bool = False
    nome: str
    codigo: str
    descricao: Optional[str]
    tipo: str
    unidade_padrao: str
    peso_unidade: Optional[float]
    umidade_padrao_pct: Optional[float]
    impureza_padrao_pct: Optional[float]
    possui_cotacao: bool
    bolsa_referencia: Optional[str]
    codigo_bolsa: Optional[str]
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CommodityClassificacao
# ---------------------------------------------------------------------------

class CommodityClassificacaoCreate(BaseModel):
    classe: str
    descricao: Optional[str] = None
    umidade_max_pct: Optional[float] = None
    impureza_max_pct: Optional[float] = None
    avariados_max_pct: Optional[float] = None
    ardidos_max_pct: Optional[float] = None
    esverdeados_max_pct: Optional[float] = None
    quebrados_max_pct: Optional[float] = None
    desconto_umidade_por_ponto: Optional[float] = None
    desconto_impureza_por_ponto: Optional[float] = None
    parametros_extras: Optional[dict] = None
    ativo: bool = True


class CommodityClassificacaoUpdate(BaseModel):
    classe: Optional[str] = None
    descricao: Optional[str] = None
    umidade_max_pct: Optional[float] = None
    impureza_max_pct: Optional[float] = None
    avariados_max_pct: Optional[float] = None
    ardidos_max_pct: Optional[float] = None
    esverdeados_max_pct: Optional[float] = None
    quebrados_max_pct: Optional[float] = None
    desconto_umidade_por_ponto: Optional[float] = None
    desconto_impureza_por_ponto: Optional[float] = None
    parametros_extras: Optional[dict] = None
    ativo: Optional[bool] = None


class CommodityClassificacaoResponse(BaseModel):
    id: uuid.UUID
    commodity_id: uuid.UUID
    classe: str
    descricao: Optional[str]
    umidade_max_pct: Optional[float]
    impureza_max_pct: Optional[float]
    avariados_max_pct: Optional[float]
    ardidos_max_pct: Optional[float]
    esverdeados_max_pct: Optional[float]
    quebrados_max_pct: Optional[float]
    desconto_umidade_por_ponto: Optional[float]
    desconto_impureza_por_ponto: Optional[float]
    parametros_extras: Optional[dict]
    ativo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CotacaoCommodity
# ---------------------------------------------------------------------------

class CotacaoCommodityCreate(BaseModel):
    data: datetime
    preco: float
    moeda: str = "BRL"
    fonte: Optional[str] = None


class CotacaoCommodityUpdate(BaseModel):
    data: Optional[datetime] = None
    preco: Optional[float] = None
    moeda: Optional[str] = None
    fonte: Optional[str] = None


class CotacaoCommodityResponse(BaseModel):
    id: uuid.UUID
    commodity_id: uuid.UUID
    data: datetime
    preco: float
    moeda: str
    fonte: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Commodity com detalhes (classificacoes + ultima cotacao)
# ---------------------------------------------------------------------------

class CommodityDetalhadaResponse(CommodityResponse):
    classificacoes: list[CommodityClassificacaoResponse] = []
    ultima_cotacao: Optional[CotacaoCommodityResponse] = None


# ---------------------------------------------------------------------------
# Cotações Regionais (Hierarquia Fazenda > Tenant/Grupo > Referência DERAL)
# ---------------------------------------------------------------------------

class CotacaoRegionalUpsertRequest(BaseModel):
    """Payload para salvar cotação regional por fazenda ou grupo/tenant."""

    model_config = ConfigDict(extra="forbid")

    valor: float = Field(gt=0, allow_inf_nan=False)
    data_referencia: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    praca: str = Field(min_length=2, max_length=120)
    fonte: Optional[str] = Field(default=None, max_length=120)
    escopo: Literal["TENANT", "FAZENDA"] = "TENANT"
    unidade_produtiva_id: Optional[uuid.UUID] = None
    observacoes: Optional[str] = Field(default=None, max_length=300)
    modo_consolidacao: Literal["FONTE_SELECIONADA", "MEDIA_FONTES"] = "FONTE_SELECIONADA"

    @model_validator(mode="after")
    def validar_escopo_fazenda(self) -> "CotacaoRegionalUpsertRequest":
        """Exige unidade_produtiva_id quando o escopo for FAZENDA."""
        if self.escopo == "FAZENDA" and self.unidade_produtiva_id is None:
            raise ValueError("unidade_produtiva_id é obrigatório para escopo FAZENDA")
        return self


class CotacaoRegionalHistoricoItem(BaseModel):
    """Registro histórico de alteração de cotação regional na fazenda ou grupo."""

    valor: float
    data_referencia: str
    praca: str
    fonte: str
    escopo: Literal["FAZENDA", "TENANT"]
    registrado_em: str


class PracaDeralResumoItem(BaseModel):
    """Cotação de um Núcleo Regional oficial do DERAL/SEAB-PR."""

    praca: str
    valor: float
    registro_original: str


class FonteComparadaRegionalItem(BaseModel):
    """Fonte individual comparada para uma commodity na região da fazenda/tenant."""

    escopo: Literal[
        "FAZENDA",
        "TENANT",
        "OFICIAL_UF",
        "PARCEIRO_UF",
        "DERAL_NUCLEO",
        "DERAL_MEDIA",
    ]
    fonte: str
    praca: str
    valor: float
    data_referencia: Optional[str] = None
    diferenca_para_media_pct: Optional[float] = None


class CotacaoRegionalItemResponse(BaseModel):
    """Referência consolidada (Fazenda > Tenant > Oficial UF > Parceiro UF > DERAL)."""

    codigo: str
    commodity_id_publico: str
    nome: str
    unidade: str
    origem_efetiva: Literal[
        "FAZENDA",
        "TENANT",
        "OFICIAL_UF",
        "PARCEIRO_UF",
        "DERAL",
        "INDISPONIVEL",
    ]
    modo_consolidacao: Literal["FONTE_SELECIONADA", "MEDIA_FONTES"] = "FONTE_SELECIONADA"
    valor_efetivo: Optional[float] = None
    data_referencia_efetiva: Optional[str] = None
    praca_efetiva: Optional[str] = None
    fonte_efetiva: Optional[str] = None
    valor_fazenda: Optional[float] = None
    data_fazenda: Optional[str] = None
    praca_fazenda: Optional[str] = None
    fonte_fazenda: Optional[str] = None
    valor_tenant: Optional[float] = None
    data_tenant: Optional[str] = None
    praca_tenant: Optional[str] = None
    fonte_tenant: Optional[str] = None
    valor_deral: Optional[float] = None
    data_deral: Optional[str] = None
    praca_deral: Optional[str] = None
    variacao_semanal_deral_pct: Optional[float] = None
    diferenca_deral_brl: Optional[float] = None
    diferenca_deral_pct: Optional[float] = None
    valor_minimo_regional_deral: Optional[float] = None
    praca_minimo_regional_deral: Optional[str] = None
    valor_maximo_regional_deral: Optional[float] = None
    praca_maximo_regional_deral: Optional[str] = None
    total_fontes_ativas: int = 0
    valor_minimo_fontes: Optional[float] = None
    valor_medio_fontes: Optional[float] = None
    valor_maximo_fontes: Optional[float] = None
    dispersao_fontes_pct: Optional[float] = None
    fontes_comparadas: list[FonteComparadaRegionalItem] = []
    pracas_deral_disponiveis: list[PracaDeralResumoItem] = []
    historico_recente: list[CotacaoRegionalHistoricoItem] = []
