from typing import Literal, Optional
from pydantic import BaseModel, Field


class TmaCalculoInput(BaseModel):
    """Parâmetros para composição da Taxa Mínima de Atratividade (TMA)."""

    percentual_capital_proprio: float = Field(50.0, ge=0, le=100)
    custo_oportunidade_proprio_aa: float = Field(11.25, ge=0)
    percentual_financiamento: float = Field(50.0, ge=0, le=100)
    taxa_financiamento_aa: float = Field(8.5, ge=0)
    premio_risco_agro_aa: float = Field(2.0, ge=0)


class TmaCalculoOutput(BaseModel):
    """Resultado detalhado da composição da TMA anual."""

    tma_calculada_aa: float
    custo_ponderado_capital_aa: float
    premio_risco_agro_aa: float
    detalhamento: str


class ProjetoInvestimentoInput(BaseModel):
    """Dados de entrada de um projeto de investimento rural (CapEx)."""

    id: str = Field(..., min_length=1, max_length=64)
    nome: str = Field(..., min_length=2, max_length=150)
    categoria: Literal[
        "IRRIGACAO",
        "ARMAZENAGEM",
        "MAQUINARIO",
        "EXPANSAO_AREA",
        "PECUARIA",
        "OUTROS",
    ] = "OUTROS"
    investimento_inicial: float = Field(..., gt=0)
    tma_aa: float = Field(..., ge=0)
    prazo_maximo_aceitavel_anos: float = Field(..., gt=0)
    fluxos_caixa_anuais: list[float] = Field(..., min_length=1)
    valor_residual_final: float = Field(0.0, ge=0)


class FluxoAnoDetalheOutput(BaseModel):
    """Detalhamento ano a ano dos fluxos de caixa simples e descontados."""

    ano: int
    fluxo_nominal: float
    fator_desconto: float
    fluxo_descontado: float
    saldo_acumulado_simples: float
    saldo_acumulado_descontado: float


class ProjetoViabilidadeOutput(BaseModel):
    """Indicadores completos de viabilidade financeira de um projeto."""

    id: str
    nome: str
    categoria: str
    investimento_inicial: float
    tma_aa: float
    prazo_maximo_aceitavel_anos: float
    vpl: float
    tir_aa: Optional[float] = None
    tirm_aa: Optional[float] = None
    margem_seguranca_tir_pp: Optional[float] = None
    payback_simples_anos: Optional[float] = None
    payback_descontado_anos: Optional[float] = None
    indice_lucratividade: float
    fluxo_nao_convencional: bool
    decisao_vpl: Literal["ACEITAR", "REJEITAR", "INDIFERENTE"]
    decisao_tir: Literal["ACEITAR", "REJEITAR", "INDIFERENTE", "INCONCLUSIVO"]
    decisao_payback: Literal["ACEITAR", "REJEITAR"]
    veredito_final: Literal["VIAVEL", "INVIAVEL", "ATENCAO_LIQUIDEZ"]
    resumo_executivo: str
    evolucao_anual: list[FluxoAnoDetalheOutput]


class ComparativoViabilidadeInput(BaseModel):
    """Payload para simulação individual ou comparativa de projetos agro."""

    tma_composicao: Optional[TmaCalculoInput] = None
    projetos: list[ProjetoInvestimentoInput] = Field(..., min_length=1)


class ComparativoViabilidadeOutput(BaseModel):
    """Resultado consolidado comparando todos os projetos lado a lado."""

    tma_calculada: Optional[TmaCalculoOutput] = None
    resultados: list[ProjetoViabilidadeOutput]
    projeto_recomendado_id: Optional[str] = None
    justificativa_comparativa: str


class TemplateProjetoAgroOutput(BaseModel):
    """Modelo pré-configurado com cenários clássicos de investimento no agronegócio."""

    id: str
    nome: str
    categoria: str
    descricao: str
    investimento_inicial: float
    tma_sugerida_aa: float
    prazo_maximo_aceitavel_anos: float
    fluxos_caixa_anuais: list[float]
    valor_residual_final: float


class PrecoEquilibrioTmaInput(BaseModel):
    """Parâmetros da safra para cálculo do preço de equilíbrio econômico (TMA / VPL = 0)."""

    custo_total_safra: float = Field(..., gt=0)
    producao_estimada_sc: float = Field(..., gt=0)
    tma_aa: float = Field(12.0, ge=0, le=200)
    prazo_ciclo_meses: float = Field(8.0, gt=0, le=60)
    preco_mercado_atual_sc: float = Field(..., gt=0)
    taxa_cambio_base: float = Field(5.8, gt=0)
    percentual_ja_travado: float = Field(0.0, ge=0, le=100)


class CenarioSensibilidadeCambio(BaseModel):
    """Cenário de sensibilidade cambial aplicado ao preço e ao VPL da safra."""

    cenario: str
    taxa_cambio: float
    preco_estimado_sc: float
    vpl_safra: float
    supera_tma: bool


class PrecoEquilibrioTmaOutput(BaseModel):
    """Resultado do equilíbrio contábil vs. TMA, VPL da safra e recomendação de Hedge."""

    preco_equilibrio_contabil_sc: float
    preco_equilibrio_tma_sc: float
    premio_custo_capital_sc: float
    fator_capitalizacao_tma: float
    vpl_safra_atual: float
    margem_sobre_tma_sc: float
    acao_hedge_recomendada: Literal["TRAVAR_MARGEM", "ATENCAO_TMA", "DEFESA_CAIXA"]
    mensagem_recomendacao: str
    sensibilidade_cambio: list[CenarioSensibilidadeCambio]
