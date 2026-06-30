from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_operational_cost_gateway_remains_official_entrypoint() -> None:
    text = _read("services/api/agricola/custos/operational_cost_service.py")

    assert "class OperationalCostAllocationService" in text
    assert "Camada canônica para apropriação de custos operacionais." in text
    assert "registrar_cost_allocation" in text
    assert "CostAllocation" in text


def test_dre_agricola_v1_remains_official_operational_dre() -> None:
    text = _read("services/api/agricola/dre/service.py")

    assert 'record_analytics_service_call("agricola.dre.v1")' in text
    assert "class DREAgricolaV1Service" in text
    assert 'fonte_oficial="CostAllocation"' in text


def test_rentabilidade_v1_remains_derived_from_dre_agricola_v1() -> None:
    text = _read("services/api/agricola/rentabilidade/service.py")

    assert "class RentabilidadeAgricolaV1Service" in text
    assert "derivada exclusivamente da DRE agrícola v1" in text
    assert "dre_service = DREAgricolaV1Service(self.session, self.tenant_id)" in text


def test_legacy_paths_remain_marked_as_non_canonical() -> None:
    legacy_expectations = {
        "services/api/financeiro/services/lancamento_service.py": [
            "Compatibilidade legada. Não usar como fonte canônica em novos fluxos.",
        ],
        "services/api/agricola/custos/service.py": [
            "Compatibilidade legada. Não usar OperacaoAgricola.custo_total como",
            "fonte canônica em novos fluxos quando CostAllocation estiver disponível.",
        ],
        "services/api/agricola/romaneios/service.py": [
            "Compatibilidade legada. Não usar romaneio como fonte canônica de",
            "receita em novos fluxos; a fonte oficial permanece sendo Receita.",
        ],
        "services/api/pecuaria/services/manejo_service.py": [
            "Compatibilidade legada. Não usar este atalho como fonte canônica",
            "de custo operacional em novos fluxos; preferir CostAllocation.",
            "de receita em novos fluxos; preferir Receita com precedência oficial.",
        ],
        "services/api/operacional/services/estoque_service.py": [
            "Compatibilidade legada. Não usar LancamentoFinanceiro de estoque como",
            "fonte canônica de DRE operacional nova; novos fluxos devem apropriar",
            "custo em CostAllocation pela porta operacional oficial.",
        ],
    }

    for relative_path, snippets in legacy_expectations.items():
        text = _read(relative_path)
        for snippet in snippets:
            assert snippet in text, f"Guardrail ausente em {relative_path}: {snippet}"
