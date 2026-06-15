"""
Schemas Pydantic — Hedge MVP (EXECUTION-HEDGE-01)

Validações de negócio:
- quantidade > 0 sempre.
- preco > 0 sempre.
- status restrito ao conjunto de valores válidos.
- tipo_posicao restrito a COMPRA | VENDA.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, ConfigDict, Field


# ==============================================================================
# ContratoFuturo
# ==============================================================================

class ContratoFuturoCreate(BaseModel):
    """Schema de criação de contrato futuro."""

    safra_id: Optional[uuid.UUID] = None
    commodity_id: Optional[uuid.UUID] = None
    commodity: str
    mercado: Optional[str] = None
    codigo_contrato: Optional[str] = None
    mes_vencimento: Optional[str] = None
    tipo_posicao: Literal["COMPRA", "VENDA"] = "VENDA"
    quantidade: float
    unidade: Optional[str] = "sc"
    preco_contratado: Optional[float] = None

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, value: float) -> float:
        """Garante que a quantidade seja estritamente positiva."""
        if value <= 0:
            raise ValueError("quantidade deve ser positiva")
        return value

    @field_validator("preco_contratado")
    @classmethod
    def preco_positivo(cls, value: float | None) -> float | None:
        """Garante que o preço contratado, se informado, seja positivo."""
        if value is not None and value <= 0:
            raise ValueError("preco_contratado deve ser positivo")
        return value


class ContratoFuturoResponse(BaseModel):
    """Schema de resposta de contrato futuro."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    commodity_id: Optional[uuid.UUID] = None
    commodity: str
    mercado: Optional[str] = None
    codigo_contrato: Optional[str] = None
    mes_vencimento: Optional[str] = None
    tipo_posicao: str
    quantidade: float
    unidade: Optional[str] = None
    preco_contratado: Optional[float] = None
    status: str
    data_liquidacao: Optional[date] = None
    preco_liquidacao: Optional[float] = None
    resultado: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# HedgeRegistro
# ==============================================================================

class HedgeRegistroCreate(BaseModel):
    """Schema de criação de registro de operação de hedge."""

    contrato_futuro_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    tipo: Literal["ABERTURA", "ROLAGEM", "ENCERRAMENTO", "AJUSTE"] = "ABERTURA"
    quantidade: float
    preco: float
    data_operacao: date
    base: Optional[float] = None
    resultado_papel: Optional[float] = None
    resultado_fisico: Optional[float] = None
    resultado_liquido: Optional[float] = None
    observacoes: Optional[str] = None

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, value: float) -> float:
        """Garante que a quantidade seja estritamente positiva."""
        if value <= 0:
            raise ValueError("quantidade deve ser positiva")
        return value

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, value: float) -> float:
        """Garante que o preço da operação seja estritamente positivo."""
        if value <= 0:
            raise ValueError("preco deve ser positivo")
        return value


class HedgeRegistroResponse(BaseModel):
    """Schema de resposta de operação de hedge."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    contrato_futuro_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    tipo: str
    quantidade: float
    preco: float
    data_operacao: date
    base: Optional[float] = None
    resultado_papel: Optional[float] = None
    resultado_fisico: Optional[float] = None
    resultado_liquido: Optional[float] = None
    observacoes: Optional[str] = None
    created_at: datetime


# ==============================================================================
# Reprocessamento MtM
# ==============================================================================

class ReprocessarMtMRequest(BaseModel):
    """Payload para reprocessamento retroativo de Snapshots MtM."""
    data_inicio: date
    data_fim: date
    safra_id: Optional[uuid.UUID] = None
    commodity_id: Optional[uuid.UUID] = None
    contrato_futuro_id: Optional[uuid.UUID] = None
    motivo: str = Field(..., min_length=10, description="Justificativa do reprocessamento")


class ReprocessarMtMResponse(BaseModel):
    """Retorno sumarizado do reprocessamento."""
    processados: int
    criados: int
    atualizados: int
    ignorados_sem_preco: int
    erros: int
    periodo_dias: int
    filtros_aplicados: dict
# ==============================================================================
# HedgePosicao (projeção calculada — sem tabela)
# ==============================================================================

class HedgePosicaoResponse(BaseModel):
    """Projeção calculada da posição de hedge por safra/commodity.

    NÃO é persistida — calculada a cada requisição a partir dos registros.
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    commodity: Optional[str] = None
    total_contratos_abertos: int
    quantidade_total_hedgeada: float
    preco_medio_ponderado: Optional[float] = None
    unidade: str = "sc"


# ==============================================================================
# HedgeExposicao (serviço de cálculo — sem tabela)
# ==============================================================================

# Classificações canônicas de risco de cobertura
CLASSIFICACAO_DESCOBERTO = "DESCOBERTO"
CLASSIFICACAO_EQUILIBRADO = "EQUILIBRADO"
CLASSIFICACAO_SOBREPROTEGIDO = "SOBREPROTEGIDO"

LIMITE_COBERTURA_MINIMO = 70.0   # abaixo → DESCOBERTO
LIMITE_COBERTURA_MAXIMO = 110.0  # acima → SOBREPROTEGIDO


class HedgeExposicaoResponse(BaseModel):
    """Resultado do cálculo completo de exposição física e financeira.

    Fórmula:
        exposicao_bruta      = Σ (produtividade_meta_sc_ha × area_ha) + estoque_fisico
        compromissos_fisicos = Σ comercializacoes confirmadas/entregues/finalizadas
        exposicao_fisica_liq = exposicao_bruta - compromissos_fisicos
        protecao_financeira  = Σ contratos futuros ABERTOS (hedge)
        exposicao_aberta     = exposicao_fisica_liq - protecao_financeira
        percentual_cobertura = protecao_financeira / exposicao_fisica_liq × 100
        hedge_ratio          = percentual_cobertura / 100
        classificacao_risco  = DESCOBERTO (<70%) | EQUILIBRADO (70–110%) | SOBREPROTEGIDO (>110%)
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    commodity: Optional[str] = None

    # Componentes da Exposição Física Bruta
    producao_estimada_sc: float
    estoque_fisico_sc: float = 0.0
    exposicao_bruta_sc: float = 0.0

    # Compromissos e Proteção
    ja_vendido_sc: float          # alias: compromissos_fisicos
    ja_hedgeado_sc: float         # alias: protecao_financeira

    # Resultados Calculados
    exposicao_liquida_sc: float   # exposicao_bruta - compromissos_fisicos
    exposicao_aberta_sc: float = 0.0  # exposicao_liquida - protecao_financeira
    percentual_cobertura: float
    hedge_ratio: float = 0.0

    # Classificação de Risco
    classificacao_risco: str = CLASSIFICACAO_DESCOBERTO


class ExposicaoConsolidadaItemResponse(BaseModel):
    """Item de exposição consolidada por safra e/ou commodity."""

    model_config = ConfigDict(from_attributes=True)

    safra_id: Optional[uuid.UUID] = None
    ano_safra: Optional[str] = None
    commodity: Optional[str] = None
    exposicao_bruta_sc: float
    ja_vendido_sc: float
    ja_hedgeado_sc: float
    exposicao_aberta_sc: float
    percentual_cobertura: float
    classificacao_risco: str


class ExposicaoConsolidadaResponse(BaseModel):
    """Visão consolidada multi-safra e multi-commodity da exposição comercial."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    total_exposicao_bruta_sc: float
    total_compromissos_sc: float
    total_protecao_sc: float
    total_exposicao_aberta_sc: float
    percentual_cobertura_global: float
    classificacao_risco_global: str
    por_safra_commodity: list[ExposicaoConsolidadaItemResponse]


class ExposicaoHistoricoItem(BaseModel):
    """Ponto da série temporal de cobertura baseado em snapshots MTM."""

    model_config = ConfigDict(from_attributes=True)

    data_referencia: str
    quantidade_aberta_sc: float
    pnl_nao_realizado: float
    preco_medio_mercado: Optional[float] = None


# ==============================================================================
# HedgePositionSnapshot (MtM)
# ==============================================================================

class HedgePositionSnapshotResponse(BaseModel):
    """Schema de resposta para Snapshot de Posição (Mark-to-Market)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    contrato_futuro_id: uuid.UUID
    safra_id: Optional[uuid.UUID] = None
    commodity_id: Optional[uuid.UUID] = None
    data_referencia: date
    quantidade_aberta: float
    preco_contratado: float
    preco_mercado: float
    moeda: str
    unidade: str
    mtm_valor: float
    pnl_nao_realizado: float
    fonte_preco: Optional[str] = None
    calculado_em: datetime
    created_at: datetime

