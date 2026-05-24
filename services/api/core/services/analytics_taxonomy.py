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
TIPO_RISCO_BENCHMARK = "BENCHMARK"

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
    "TAREFA_CONCLUIDA_SEM_OPERACAO": TaxonomiaAnalitica(
        codigo="TAREFA_CONCLUIDA_SEM_OPERACAO",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="TAREFA",
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "OPERACAO_REALIZADA_SEM_EXECUCAO": TaxonomiaAnalitica(
        codigo="OPERACAO_REALIZADA_SEM_EXECUCAO",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="OPERACAO",
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "OPERACAO_COM_CUSTO_SEM_ALLOCATION": TaxonomiaAnalitica(
        codigo="OPERACAO_COM_CUSTO_SEM_ALLOCATION",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_EFICIENCIA,
        classificacao="OPERACIONAL",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "APONTAMENTO_COM_CUSTO_SEM_CONTEXTO": TaxonomiaAnalitica(
        codigo="APONTAMENTO_COM_CUSTO_SEM_CONTEXTO",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="APONTAMENTO",
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE": TaxonomiaAnalitica(
        codigo="PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="COMPRAS",
        classificacao="OPERACIONAL",
        severidade_padrao="PRIORIDADE_CRITICA",
    ),
    "DESPESA_AUTOMATICA_SEM_ORIGEM": TaxonomiaAnalitica(
        codigo="DESPESA_AUTOMATICA_SEM_ORIGEM",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="DESPESA",
        classificacao="OPERACIONAL",
        severidade_padrao="ATENCAO",
    ),
    "ALLOCATION_POTENCIALMENTE_DUPLICADA": TaxonomiaAnalitica(
        codigo="ALLOCATION_POTENCIALMENTE_DUPLICADA",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="PRIORIDADE_CRITICA",
    ),
    "CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO": TaxonomiaAnalitica(
        codigo="CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "COST_ALLOCATION_SEM_ORIGEM_RASTREAVEL": TaxonomiaAnalitica(
        codigo="COST_ALLOCATION_SEM_ORIGEM_RASTREAVEL",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia=TIPO_INCONSISTENCIA_RECONCILIACAO,
        classificacao="ECONOMICO",
        severidade_padrao="ATENCAO",
    ),
    "DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM": TaxonomiaAnalitica(
        codigo="DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia="DESPESA",
        classificacao="ECONOMICO",
        severidade_padrao="PRIORIDADE_CRITICA",
    ),
    "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION": TaxonomiaAnalitica(
        codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia="ESTOQUE",
        classificacao="ECONOMICO",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO": TaxonomiaAnalitica(
        codigo="DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO",
        categoria_analitica="RECONCILIACAO",
        tipo_risco=TIPO_RISCO_RECONCILIACAO,
        tipo_inconsistencia="ECONOMICO",
        classificacao="ECONOMICO",
        severidade_padrao="RISCO_ECONOMICO",
    ),
    "DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL": TaxonomiaAnalitica(
        codigo="DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL",
        categoria_analitica="GOVERNANCA",
        tipo_risco=TIPO_RISCO_GOVERNANCA,
        tipo_inconsistencia="COMPRAS",
        classificacao="OPERACIONAL",
        severidade_padrao="PRIORIDADE_CRITICA",
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


def classificar_tipo_relatorio(codigo: str) -> str:
    normalizado = codigo.upper()
    if normalizado.startswith("TAREFA_"):
        return "TAREFA"
    if normalizado.startswith("OPERACAO_"):
        return "OPERACAO"
    if normalizado.startswith("APONTAMENTO_"):
        return "APONTAMENTO"
    if normalizado.startswith("PEDIDO_") or normalizado.startswith("DEVOLUCAO_"):
        return "COMPRAS"
    if normalizado.startswith("DESPESA_"):
        return "DESPESA"
    if normalizado.startswith("ALLOCATION_") or normalizado.startswith("COST_ALLOCATION_"):
        return "COST_ALLOCATION"
    if normalizado.startswith("MOVIMENTO_") or normalizado.startswith("ESTOQUE_"):
        return "ESTOQUE"
    if normalizado.startswith("DIVERGENCIA_") or normalizado.startswith("CUSTO_"):
        return "ECONOMICO"
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
