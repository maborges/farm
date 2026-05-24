from __future__ import annotations

from dataclasses import dataclass
from typing import Final


SEVERIDADES_CANONICAS: Final[tuple[str, ...]] = (
    "INFO",
    "ATENCAO",
    "RISCO_OPERACIONAL",
    "RISCO_ECONOMICO",
    "PRIORIDADE_CRITICA",
)

SEVERIDADE_ORDEM: Final[dict[str, int]] = {
    "PRIORIDADE_CRITICA": 0,
    "RISCO_ECONOMICO": 1,
    "RISCO_OPERACIONAL": 2,
    "ATENCAO": 3,
    "INFO": 4,
}

SEVERIDADE_BASE: Final[dict[str, int]] = {
    "INFO": 20,
    "ATENCAO": 50,
    "RISCO_OPERACIONAL": 72,
    "RISCO_ECONOMICO": 88,
    "PRIORIDADE_CRITICA": 100,
}

SEVERIDADE_ALIASES: Final[dict[str, str]] = {
    "WARNING_LEVE": "INFO",
    "WARNING": "ATENCAO",
    "INCONSISTENCIA_MODERADA": "ATENCAO",
    "DANGER": "PRIORIDADE_CRITICA",
    "RISCO_CRITICO": "PRIORIDADE_CRITICA",
}

TIPO_RISCO_ECONOMICO = "ECONOMICO"
TIPO_RISCO_OPERACIONAL = "OPERACIONAL"
TIPO_RISCO_MISTO = "MISTO"
TIPO_RISCO_RECONCILIACAO = "RECONCILIACAO"
TIPO_RISCO_GOVERNANCA = "GOVERNANCA"

TIPO_INCONSISTENCIA_RECONCILIACAO = "RECONCILIACAO_ECONOMICA"
TIPO_INCONSISTENCIA_EFICIENCIA = "EFICIENCIA_OPERACIONAL"
TIPO_INCONSISTENCIA_BENCHMARK = "BENCHMARK"
TIPO_INCONSISTENCIA_PRODUTIVIDADE = "PRODUTIVIDADE"
TIPO_INCONSISTENCIA_GOVERNANCA = "GOVERNANCA"


@dataclass(frozen=True, slots=True)
class TaxonomiaAnalitica:
    codigo: str
    categoria_analitica: str
    tipo_risco: str
    tipo_inconsistencia: str
    classificacao: str
    severidade_padrao: str


ANALYTIC_CODE_REGISTRY: Final[dict[str, TaxonomiaAnalitica]] = {
    "MARGEM_ABAIXO_MEDIA_TENANT": TaxonomiaAnalitica(
        codigo="MARGEM_ABAIXO_MEDIA_TENANT",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_ECONOMICO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "CUSTO_HECTARE_ACIMA_MEDIA": TaxonomiaAnalitica(
        codigo="CUSTO_HECTARE_ACIMA_MEDIA",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_ECONOMICO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "RESULTADO_SAFRA_ABAIXO_BENCHMARK": TaxonomiaAnalitica(
        codigo="RESULTADO_SAFRA_ABAIXO_BENCHMARK",
        categoria_analitica="BENCHMARK",
        tipo_risco=TIPO_RISCO_ECONOMICO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_BENCHMARK,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "JORNADA_BAIXA_PRODUTIVIDADE": TaxonomiaAnalitica(
        codigo="JORNADA_BAIXA_PRODUTIVIDADE",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_OPERACIONAL,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_PRODUTIVIDADE,
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "RESULTADO_OPERACIONAL_NEGATIVO": TaxonomiaAnalitica(
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_ECONOMICO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "RECEITA_LIQUIDA_HA_ABAIXO_MEDIA": TaxonomiaAnalitica(
        codigo="RECEITA_LIQUIDA_HA_ABAIXO_MEDIA",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_ECONOMICO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "PRODUCTION_UNIT_BAIXA_EFICIENCIA": TaxonomiaAnalitica(
        codigo="PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_MISTO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_EFICIENCIA,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "EQUIPAMENTO_CUSTO_ELEVADO": TaxonomiaAnalitica(
        codigo="EQUIPAMENTO_CUSTO_ELEVADO",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_OPERACIONAL,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_EFICIENCIA,
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "OPERACAO_CUSTO_FORA_CURVA": TaxonomiaAnalitica(
        codigo="OPERACAO_CUSTO_FORA_CURVA",
        categoria_analitica="DIAGNOSTICO",
        tipo_risco=TIPO_RISCO_OPERACIONAL,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_EFICIENCIA,
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "RECORRENCIA_WARNING_ECONOMICO": TaxonomiaAnalitica(
        codigo="RECORRENCIA_WARNING_ECONOMICO",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "RECORRENCIA_INCONSISTENCIA_OPERACIONAL": TaxonomiaAnalitica(
        codigo="RECORRENCIA_INCONSISTENCIA_OPERACIONAL",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_GOVERNANCA,
        classificacao="OPERACIONAL",
        severidade_padrao="RISCO_OPERACIONAL",
    ),
}


def normalizar_severidade(severidade: str | None) -> str:
    if not severidade:
        return "INFO"
    return SEVERIDADE_ALIASES.get(severidade.upper(), severidade.upper())


def severidade_ordem(severidade: str | None) -> int:
    return SEVERIDADE_ORDEM.get(normalizar_severidade(severidade), 99)


def severidade_base(severidade: str | None) -> int:
    return SEVERIDADE_BASE.get(normalizar_severidade(severidade), 20)


def obter_taxonomia(codigo: str) -> TaxonomiaAnalitica | None:
    return ANALYTIC_CODE_REGISTRY.get(codigo.upper())


def classificar_codigo(codigo: str) -> str:
    taxonomia = obter_taxonomia(codigo)
    if taxonomia is not None:
        return taxonomia.classificacao

    normalizado = codigo.upper()
    economic_keywords = (
        "CUSTO",
        "ALLOCATION",
        "RECONCILI",
        "DRE",
        "MARGEM",
        "RESULTADO",
        "LANCAMENTO",
        "VALOR",
    )
    if any(keyword in normalizado for keyword in economic_keywords):
        return "ECONOMICO"

    operational_keywords = (
        "OPERACAO",
        "JORNADA",
        "APONTAMENTO",
        "WORKFLOW",
        "TAREFA",
        "FROTA",
        "CHECKLIST",
        "FENOLOG",
        "EXECUCAO",
        "MONITOR",
    )
    if any(keyword in normalizado for keyword in operational_keywords):
        return "OPERACIONAL"

    return "INFO"


def categoria_analitica(codigo: str) -> str:
    taxonomia = obter_taxonomia(codigo)
    if taxonomia is not None:
        return taxonomia.categoria_analitica
    return "DESCONHECIDA"


def tipo_risco(codigo: str) -> str:
    taxonomia = obter_taxonomia(codigo)
    if taxonomia is not None:
        return taxonomia.tipo_risco
    return TIPO_RISCO_OPERACIONAL if classificar_codigo(codigo) == "OPERACIONAL" else TIPO_RISCO_ECONOMICO


def tipo_inconsistencia(codigo: str) -> str:
    taxonomia = obter_taxonomia(codigo)
    if taxonomia is not None:
        return taxonomia.tipo_inconsistencia
    return "GERAL"


def codigos_analiticos_registrados() -> set[str]:
    return set(ANALYTIC_CODE_REGISTRY)


def severidade_compatibilidade_prioridade_warning(severidade: str) -> str:
    if severidade == "RISCO_ECONOMICO":
        return "RISCO_ECONOMICO"
    if severidade in {"RISCO_OPERACIONAL", "INCONSISTENCIA_MODERADA"}:
        return "RISCO_OPERACIONAL"
    return "INFO"
