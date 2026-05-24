from __future__ import annotations

import uuid

import pytest

from agricola.alertas.service import AlertasAgricolasService
from agricola.benchmark.service import BenchmarkAgricolaV1Service
from agricola.dre.schemas import DREWarning
from core.services.analytics_request_cache import build_dre_kpi_cache_key


def test_cache_key_normaliza_severidade_de_warning():
    dre = type(
        "FakeDRE",
        (),
        {
            "tenant_id": uuid.uuid4(),
            "safra_id": uuid.uuid4(),
            "production_unit_id": None,
            "unidade_produtiva_id": None,
            "data_inicio": None,
            "data_fim": None,
        },
    )()
    warning_legacy = DREWarning(
        codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
        titulo="x",
        severidade="INCONSISTENCIA_MODERADA",
        mensagem="x",
        origem="dre",
    )
    warning_canonico = DREWarning(
        codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
        titulo="x",
        severidade="ATENCAO",
        mensagem="x",
        origem="dre",
    )

    key_legacy = build_dre_kpi_cache_key(dre, area_total_ha=10.0, warnings=[warning_legacy])
    key_canonico = build_dre_kpi_cache_key(dre, area_total_ha=10.0, warnings=[warning_canonico])
    assert key_legacy == key_canonico


def test_benchmark_dedupe_warnings_normaliza_aliases():
    warnings = [
        DREWarning(
            codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
            titulo="x",
            severidade="INCONSISTENCIA_MODERADA",
            mensagem="x",
            origem="benchmark",
        ),
        DREWarning(
            codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
            titulo="x",
            severidade="ATENCAO",
            mensagem="x",
            origem="benchmark",
        ),
    ]

    deduped = BenchmarkAgricolaV1Service._dedupe_warnings(warnings)
    assert len(deduped) == 1
    assert deduped[0].codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION"


def test_governanca_enforcement_aceita_alias_canonico(monkeypatch: pytest.MonkeyPatch):
    import agricola.alertas.service as alertas_service

    monkeypatch.setattr(alertas_service, "WORKFLOW_ENFORCEMENT_MODE", alertas_service.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL)
    svc = AlertasAgricolasService(None, uuid.uuid4())

    assert svc.deve_bloquear_severidade("RISCO_CRITICO")
    assert svc.deve_bloquear_severidade("PRIORIDADE_CRITICA")
    assert not svc.deve_bloquear_severidade("ATENCAO")


def test_classificar_tipo_relatorio_governanca_preservado():
    svc = AlertasAgricolasService(None, uuid.uuid4())
    assert svc._classificar_tipo_relatorio("MOVIMENTO_COM_CUSTO_SEM_ALLOCATION") == "ESTOQUE"
    assert svc._classificar_tipo_relatorio("ALLOCATION_POTENCIALMENTE_DUPLICADA") == "COST_ALLOCATION"
