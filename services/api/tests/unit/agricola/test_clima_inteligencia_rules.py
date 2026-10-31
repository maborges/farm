from datetime import date

import pytest

from agricola.climatico.models import RegistroClima
from agricola.climatico.service import ClimaService


def test_risco_fitossanitario_nao_calcula_com_variavel_ausente() -> None:
    regras = {"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 10, "peso": 1}]}
    assert ClimaService._avaliar_modelo(regras, {"umidade_rel_pct": 90}) is None


def test_risco_fitossanitario_rejeita_peso_invalido() -> None:
    regras = {"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 20, "peso": 0}]}
    with pytest.raises(ValueError, match="peso"):
        ClimaService._avaliar_modelo(regras, {"temp_media_c": 25})


def test_risco_fitossanitario_classificacao_tem_limites() -> None:
    regras = {"nivel_critico_pct": 80, "nivel_alto_pct": 60, "nivel_medio_pct": 35}
    assert ClimaService._classificar_nivel(100, regras) == "critico"
    assert ClimaService._classificar_nivel(59, regras) == "medio"
    assert ClimaService._classificar_nivel(0, regras) == "baixo"


def test_balanco_hidrico_exige_evapotranspiracao_observada() -> None:
    registro = RegistroClima(
        tenant_id="00000000-0000-0000-0000-000000000001",
        unidade_produtiva_id="00000000-0000-0000-0000-000000000002",
        data_registro=date.today(),
        precipitacao_mm=10,
        evapotranspiracao_mm=None,
        fonte="TEST",
    )
    assert ClimaService._calcular_balanco_hidrico([registro]) == []
