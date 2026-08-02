from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal, Optional, List
from datetime import datetime
import uuid

CategoriaOrcamento = Literal[
    "SEMENTE", "FERTILIZANTE", "DEFENSIVO", "MATERIAL", "MAQUINARIO",
    "COMBUSTIVEL", "MAO_DE_OBRA", "SERVICO", "SEGURO", "OUTROS",
]

OrigemItemOrcamento = Literal["PRODUTO", "MAQUINA", "PESSOA", "SERVICO", "MANUAL"]


# ── Itens do Orçamento ────────────────────────────────────────────────────────

class ItemOrcamentoCreate(BaseModel):
    cultivo_id: Optional[uuid.UUID] = None
    production_unit_id: Optional[uuid.UUID] = None
    categoria: CategoriaOrcamento
    descricao: str = Field(..., min_length=2, max_length=200)
    quantidade: float = Field(..., gt=0)
    unidade: str = Field(..., min_length=1, max_length=20)
    unidade_medida_id: Optional[uuid.UUID] = None
    origem_tipo: OrigemItemOrcamento = "MANUAL"
    origem_id: Optional[uuid.UUID] = None
    custo_unitario: Optional[float] = Field(None, gt=0)
    custo_unitario_ajustado: Optional[float] = Field(None, gt=0)
    ordem: int = Field(0, ge=0)
    observacoes: Optional[str] = None

    @model_validator(mode="after")
    def validar_origem(self) -> "ItemOrcamentoCreate":
        if self.origem_tipo == "MANUAL":
            if self.custo_unitario is None:
                raise ValueError("custo_unitario é obrigatório quando origem_tipo=MANUAL")
        elif self.origem_id is None:
            raise ValueError("origem_id é obrigatório quando origem_tipo != MANUAL")
        return self


class ItemOrcamentoUpdate(BaseModel):
    cultivo_id: Optional[uuid.UUID] = None
    production_unit_id: Optional[uuid.UUID] = None
    categoria: Optional[CategoriaOrcamento] = None
    descricao: Optional[str] = Field(None, min_length=2, max_length=200)
    quantidade: Optional[float] = Field(None, gt=0)
    unidade: Optional[str] = Field(None, min_length=1, max_length=20)
    unidade_medida_id: Optional[uuid.UUID] = None
    custo_unitario: Optional[float] = Field(None, gt=0)
    custo_unitario_ajustado: Optional[float] = Field(None, gt=0)
    ordem: Optional[int] = Field(None, ge=0)
    observacoes: Optional[str] = None


class ItemOrcamentoResponse(BaseModel):
    id: uuid.UUID
    safra_id: uuid.UUID
    cultivo_id: Optional[uuid.UUID]
    production_unit_id: Optional[uuid.UUID]
    categoria: str
    descricao: str
    quantidade: float
    unidade: str
    unidade_medida_id: Optional[uuid.UUID]
    origem_tipo: str
    origem_id: Optional[uuid.UUID]
    custo_unitario: float
    custo_unitario_snapshot: Optional[float]
    custo_unitario_ajustado: Optional[float]
    custo_unitario_efetivo: float
    snapshot_data: Optional[dict]
    capturado_em: Optional[datetime]
    custo_total: float
    ordem: int
    observacoes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Orçamento Completo ────────────────────────────────────────────────────────

class CustoCategoria(BaseModel):
    """Custo agrupado por categoria dentro do orçamento."""
    categoria: str
    custo_total: float
    custo_por_ha: float
    percentual: float


class OrcamentoPrevisto(BaseModel):
    custo_total: float
    custo_por_ha: float
    receita_esperada: float          # produtividade_meta × preco_venda × area
    receita_por_ha: float
    margem_bruta: float
    ponto_equilibrio_sc_ha: Optional[float]  # custo_por_ha / preco_venda
    por_categoria: List[CustoCategoria]


class OrcamentoRealizado(BaseModel):
    custo_operacoes: float           # de OperacaoAgricola.custo_total
    custo_rateios: float             # de fin_rateios (despesas financeiras)
    custo_total: float
    custo_por_ha: float
    por_categoria: List[CustoCategoria]


class DesvioOrcamento(BaseModel):
    custo_desvio_valor: float        # realizado - previsto
    custo_desvio_pct: float          # % sobre o previsto
    status: str                      # DENTRO | ACIMA | SEM_ORCAMENTO


class OrcamentoSafraResponse(BaseModel):
    safra_id: uuid.UUID
    cultura: str
    ano_safra: str
    area_ha: float
    status_safra: str
    previsto: Optional[OrcamentoPrevisto]
    realizado: OrcamentoRealizado
    desvio: Optional[DesvioOrcamento]
    itens: List[ItemOrcamentoResponse]


# ── Campanhas (visão geral) ───────────────────────────────────────────────────

class SafraKPI(BaseModel):
    safra_id: uuid.UUID
    talhao_id: Optional[uuid.UUID] = None
    cultura: str
    ano_safra: str
    area_ha: float
    status: str
    custo_previsto_ha: Optional[float]
    custo_realizado_ha: Optional[float]
    desvio_custo_pct: Optional[float]
    produtividade_meta_sc_ha: Optional[float]
    produtividade_real_sc_ha: Optional[float]
    desvio_prod_pct: Optional[float]
    receita_esperada: Optional[float]


class CampanhasResponse(BaseModel):
    ano_safra: Optional[str]
    total_area_ha: float
    total_custo_previsto: float
    total_custo_realizado: float
    safras: List[SafraKPI]
