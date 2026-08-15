from __future__ import annotations

# ruff: noqa
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PecuariaGeneticaCreate(BaseModel):
    animal_id: int
    brinco: Optional[str] = None
    raca_id: Optional[int] = None
    pai_id: Optional[int] = None
    mae_id: Optional[int] = None
    dep_ganho_peso: Optional[float] = None
    dep_area_olho_lombo: Optional[float] = None
    dep_gordura_subcutanea: Optional[float] = None
    dep_maciez: Optional[float] = None
    matriz: bool = False
    reprodutor: bool = False


class PecuariaGeneticaResponse(BaseModel):
    id: int
    tenant_id: str
    animal_id: int
    brinco: Optional[str]
    raca_id: Optional[int]
    pai_id: Optional[int]
    mae_id: Optional[int]
    dep_ganho_peso: Optional[float]
    dep_area_olho_lombo: Optional[float]
    dep_gordura_subcutanea: Optional[float]
    dep_maciez: Optional[float]
    matriz: bool
    reprodutor: bool
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class PecuariaSugestaoCreate(BaseModel):
    matriz_id: int
    reprodutor_id: int
    dep_esperado: dict | None = None
    score_complementaridade: float = Field(default=0)
    realizado: bool = False
    data_acasalamento: Optional[date] = None


class PecuariaSugestaoResponse(BaseModel):
    id: int
    tenant_id: str
    matriz_id: int
    reprodutor_id: int
    dep_esperado: dict | None
    score_complementaridade: Optional[float]
    realizado: bool
    data_acasalamento: Optional[date]
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class ConfinamentoLoteCreate(BaseModel):
    unidade_produtiva_id: Optional[int] = None
    codigo: str
    safra: Optional[str] = None
    total_animais: int = Field(..., ge=0)
    peso_inicial_kg: Optional[float] = None
    peso_inicial_total_kg: Optional[float] = None
    data_entrada: date
    data_saida_prevista: Optional[date] = None
    data_saida_real: Optional[date] = None
    peso_saida_kg: Optional[float] = None
    ganho_medio_diario: Optional[float] = None
    conversao_alimentar: Optional[float] = None
    status: str = "confinado"
    observacoes: Optional[str] = None


class ConfinamentoLoteEncerrar(BaseModel):
    """OPERATIONS-GAP-01 §21.12: encerramento do lote, único ponto que grava
    peso_saida_kg/ganho_medio_diario — antes inexistente, campo sempre NULL."""
    peso_saida_kg: float = Field(..., gt=0)
    data_saida_real: date
    consumo_total_racao_kg: Optional[float] = Field(None, gt=0)


class ConfinamentoLoteResponse(BaseModel):
    id: int
    tenant_id: str
    unidade_produtiva_id: Optional[int]
    codigo: str
    safra: Optional[str]
    total_animais: Optional[int]
    peso_inicial_kg: Optional[float]
    peso_inicial_total_kg: Optional[float]
    data_entrada: date
    data_saida_prevista: Optional[date]
    data_saida_real: Optional[date]
    peso_saida_kg: Optional[float]
    ganho_medio_diario: Optional[float]
    conversao_alimentar: Optional[float]
    status: str
    observacoes: Optional[str]
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class RacaoTMRCreate(BaseModel):
    nome: str
    codigo: Optional[str] = None
    ingredientes: dict
    proteina_bruta: Optional[float] = None
    ndt: Optional[float] = None
    energia_liquida: Optional[float] = None
    custo_por_tonelada: Optional[float] = None
    ativa: bool = True


class RacaoTMRResponse(BaseModel):
    id: int
    tenant_id: str
    nome: str
    codigo: Optional[str]
    ingredientes: dict | None
    proteina_bruta: Optional[float]
    ndt: Optional[float]
    energia_liquida: Optional[float]
    custo_por_tonelada: Optional[float]
    ativa: bool
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class CochoCreate(BaseModel):
    lote_id: int
    codigo: str
    comprimento_m: Optional[float] = None
    racao_fornecida_kg: Optional[float] = None
    sobra_kg: Optional[float] = None
    consumo_kg: Optional[float] = None
    data: date
    turno: Optional[str] = None


class CochoResponse(BaseModel):
    id: int
    tenant_id: str
    lote_id: int
    codigo: str
    comprimento_m: Optional[float]
    racao_fornecida_kg: Optional[float]
    sobra_kg: Optional[float]
    consumo_kg: Optional[float]
    data: date
    turno: Optional[str]
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class ProducaoLeiteCreate(BaseModel):
    unidade_produtiva_id: UUID
    animal_id: Optional[UUID] = None
    lote_id: Optional[UUID] = None
    data: date
    turno: str = "MANHA"
    volume_litros: float = Field(..., gt=0)
    temperatura_c: Optional[float] = None
    gordura_pct: Optional[float] = None
    proteina_pct: Optional[float] = None
    ccs: Optional[int] = None
    cbt: Optional[int] = None
    lactose_pct: Optional[float] = None
    esd_pct: Optional[float] = None
    destino: Optional[str] = None
    pessoa_destino_id: Optional[UUID] = None
    preco_litro: Optional[float] = None
    valor_total: Optional[float] = None
    observacoes: Optional[str] = None
    dados_extras: Optional[dict] = None


class ProducaoLeiteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID
    animal_id: Optional[UUID]
    lote_id: Optional[UUID]
    data: date
    turno: str
    volume_litros: float
    temperatura_c: Optional[float]
    gordura_pct: Optional[float]
    proteina_pct: Optional[float]
    ccs: Optional[int]
    cbt: Optional[int]
    lactose_pct: Optional[float]
    esd_pct: Optional[float]
    destino: Optional[str]
    pessoa_destino_id: Optional[UUID]
    preco_litro: Optional[float]
    valor_total: Optional[float]
    observacoes: Optional[str]
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class PecuariaGeneticaResumoResponse(BaseModel):
    total_registros: int
    total_matrizes: int
    total_reprodutores: int
    total_sugestoes: int
    total_coberturas: int = 0
    total_diagnosticos_prenhez: int = 0
    total_partos: int = 0
    total_nascimentos: int = 0
    total_desmamas: int = 0
    taxa_prenhez_pct: float = 0
    taxa_natalidade_pct: float = 0
    taxa_desmama_pct: float = 0
    intervalo_medio_partos_dias: float = 0
    peso_nascimento_medio_kg: float = 0
    peso_desmama_medio_kg: float = 0
    idade_media_desmama_dias: float = 0
    crias_por_matriz: float = 0
    perdas_reprodutivas: int = 0


class ConfinamentoResumoResponse(BaseModel):
    total_lotes: int
    total_animais: int
    total_racoes: int
    total_cochos: int
    gmd_medio: float
    conversao_media: float


class ProducaoLeiteResumoResponse(BaseModel):
    total_registros: int
    volume_total_litros: float
    media_volume_litros: float
    media_gordura_pct: float
    media_proteina_pct: float
