from __future__ import annotations

from core.services.analytics_taxonomy import (
    ANALYTIC_CODE_REGISTRY,
    classificar_tipo_relatorio,
    classificar_codigo,
    codigos_analiticos_registrados,
    normalizar_severidade,
    severidade_base,
    severidade_compatibilidade_prioridade_warning,
    severidade_ordem,
)


def test_normalizar_severidade_aliases_canonicamente():
    assert normalizar_severidade("warning_leve") == "INFO"
    assert normalizar_severidade("INCONSISTENCIA_MODERADA") == "ATENCAO"
    assert normalizar_severidade("RISCO_CRITICO") == "PRIORIDADE_CRITICA"
    assert normalizar_severidade("atencao") == "ATENCAO"


def test_registry_classifica_codigos_conhecidos_e_fallback():
    assert "RESULTADO_SAFRA_ABAIXO_BENCHMARK" in codigos_analiticos_registrados()
    assert ANALYTIC_CODE_REGISTRY["RESULTADO_SAFRA_ABAIXO_BENCHMARK"].categoria_analitica == "BENCHMARK"
    assert ANALYTIC_CODE_REGISTRY["RECORRENCIA_INCONSISTENCIA_OPERACIONAL"].tipo_risco == "GOVERNANCA"
    assert classificar_codigo("OPERACAO_CUSTO_FORA_CURVA") == "OPERACIONAL"
    assert classificar_codigo("ALGUM_CODIGO_DESCONHECIDO") == "INFO"
    assert classificar_tipo_relatorio("MOVIMENTO_COM_CUSTO_SEM_ALLOCATION") == "ESTOQUE"
    assert classificar_tipo_relatorio("DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM") == "DESPESA"


def test_severidade_order_e_base_sao_canonicas():
    assert severidade_ordem("PRIORIDADE_CRITICA") < severidade_ordem("RISCO_ECONOMICO") < severidade_ordem("INFO")
    assert severidade_base("PRIORIDADE_CRITICA") > severidade_base("RISCO_ECONOMICO") > severidade_base("INFO")


def test_compatibilidade_de_warning_de_prioridade_preservada():
    assert severidade_compatibilidade_prioridade_warning("WARNING_LEVE") == "INFO"
    assert severidade_compatibilidade_prioridade_warning("INCONSISTENCIA_MODERADA") == "RISCO_OPERACIONAL"
