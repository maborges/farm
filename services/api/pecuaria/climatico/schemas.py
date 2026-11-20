import math
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _numero_finito(valor: object) -> bool:
    """Verifica se um valor é numérico finito e não booleano."""
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return False
    try:
        return math.isfinite(float(valor))
    except (OverflowError, ValueError):
        return False


def _validar_fonte_url_http(fonte_url: object, campo: str) -> None:
    """Garante protocolo http:// ou https:// quando fonte_url estiver preenchida."""
    if fonte_url is None:
        return
    if not isinstance(fonte_url, str) or (
        fonte_url != "" and not fonte_url.startswith(("https://", "http://"))
    ):
        raise ValueError(f"{campo} deve usar protocolo http:// ou https://")


def _validar_limiares_ith(regras: dict[str, Any]) -> None:
    """Valida presença, tipo e ordenação estrita dos limiares de ITH."""
    chaves = ("nivel_medio", "nivel_alto", "nivel_critico")
    for chave in chaves:
        if not _numero_finito(regras.get(chave)):
            raise ValueError(f"regras_risco.{chave} deve ser numérico e finito")

    medio = float(regras["nivel_medio"])
    alto = float(regras["nivel_alto"])
    critico = float(regras["nivel_critico"])
    if not (0 < medio < alto < critico <= 100):
        raise ValueError("Limiares devem obedecer 0 < nivel_medio < nivel_alto < nivel_critico <= 100")


def _validar_metadados_zoosanitarios(regras: dict[str, Any]) -> None:
    """Valida fontes e bloco opcional de metadados de modelo zoossanitário."""
    _validar_fonte_url_http(regras.get("fonte_url"), "regras_risco.fonte_url")
    metadados = regras.get("metadados")
    if metadados is None:
        return
    if not isinstance(metadados, dict):
        raise ValueError("regras_risco.metadados deve ser um objeto JSON")
    _validar_fonte_url_http(metadados.get("fonte_url"), "regras_risco.metadados.fonte_url")


def validar_regras_zoosanitarias(regras: dict[str, Any]) -> dict[str, Any]:
    """Valida limiares de ITH e URLs de proveniência das regras zoossanitárias.

    Args:
        regras: Dicionário de configuração de risco térmico (ITH).

    Returns:
        O próprio dicionário validado.

    Raises:
        ValueError: Se algum limiar ou URL estiver inválido.
    """
    if not isinstance(regras, dict):
        raise ValueError("regras_risco deve ser um objeto JSON")
    _validar_limiares_ith(regras)
    _validar_metadados_zoosanitarios(regras)
    return regras


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

    @field_validator("regras_risco")
    @classmethod
    def validar_regras(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validar_regras_zoosanitarias(value)


class ModeloZoosanitarioCreate(ModeloZoosanitarioBase):
    pass


class ModeloZoosanitarioUpdate(BaseModel):
    regras_risco: dict[str, Any]

    @field_validator("regras_risco")
    @classmethod
    def validar_regras(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validar_regras_zoosanitarias(value)


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
