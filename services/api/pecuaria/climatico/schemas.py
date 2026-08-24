from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CondicaoRegra(BaseModel):
    variavel: str = Field(..., description="A variável climática (ex: ITH, temp_max, umidade_rel_pct)")
    operador: str = Field(..., description="Operador lógico (ex: >, <, >=, <=, ==)")
    valor: float = Field(..., description="Valor limite da variável")
    peso: float | None = Field(default=None, description="Peso da condição no cálculo do risco final")


class RegrasRisco(BaseModel):
    condicoes: list[CondicaoRegra] = Field(default_factory=list, description="Lista de condições para determinar o risco")
    nivel_critico: float | None = Field(default=None, description="Limite para risco crítico")
    nivel_alto: float | None = Field(default=None, description="Limite para risco alto")
    nivel_medio: float | None = Field(default=None, description="Limite para risco médio")


class ModeloZoosanitarioBase(BaseModel):
    especie: str = Field(..., description="Espécie animal (ex: Bovino de Leite)")
    tipo_risco: str = Field(..., description="Tipo de risco (ex: Estresse Térmico)")
    regras_risco: dict[str, Any] = Field(..., description="Objeto de regras de risco e pesos")


class ModeloZoosanitarioCreate(ModeloZoosanitarioBase):
    pass


class ModeloZoosanitarioUpdate(BaseModel):
    regras_risco: dict[str, Any]


class ModeloZoosanitarioResponse(ModeloZoosanitarioBase):
    id: UUID
    tenant_id: UUID | None
    is_global: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteligenciaPecuariaResponse(BaseModel):
    especie: str
    tipo_risco: str
    risco_atual: str = Field(..., description="Nível de risco (ex: BAIXO, MEDIO, ALTO, CRITICO)")
    data_analise: datetime
    valor_referencia: float | None = Field(default=None, description="Valor do índice principal calculado (ex: ITH 75)")
    detalhes: list[str] = Field(default_factory=list, description="Alertas ou recomendações geradas pelo motor")
    historico: list[dict[str, float | str | None]] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
    idade_dados_dias: int | None = None
    dados_atualizados: bool = False
    previsao_ith: list[dict[str, Any | None]] = Field(default_factory=list)
    estresse_previsto: dict[str, Any | None] = Field(default_factory=dict)
    chuva_prevista: dict[str, Any | None] = Field(default_factory=dict)
    janela_manejo: dict[str, Any | None] = Field(default_factory=dict)


class RecomendacaoOperacionalResponse(BaseModel):
    unidade_produtiva_id: UUID
    tipo_operacao: str
    status: str
    severidade: str
    motivo: str
    dados_utilizados: dict
    data_referencia: datetime
    fonte: str
    validade_horas: int

    model_config = ConfigDict(from_attributes=True)
