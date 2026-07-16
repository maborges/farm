"""
EXEC-37 — Testes de guardrail: Auto-vínculo Fundiário (UnidadeProdutiva → ImovelRural)
Foi descontinuado.

O objetivo deste guardrail é certificar que tentativas de injeção de atributos
fundiários via UnidadeProdutiva falhem e não criem ImovelRural.
"""

import pytest
import uuid
from decimal import Decimal
from pydantic import ValidationError

from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate


@pytest.fixture
def base_dados():
    return {
        "nome": "Fazenda Guardrail",
        "tipo_propriedade": "fazenda",
        "area_total_ha": Decimal("150.0"),
        "municipio": "Testolândia",
        "uf": "SP",
    }


def test_guardrail_up_nao_aceita_campos_fundiarios(base_dados):
    """
    Tentar inicializar UnidadeProdutivaCreate com campos fundiários deve falhar
    ou os campos devem ser ignorados.
    """
    payload_invalido = {
        **base_dados,
        "codigo_car": "SP12345",
        "nirf": "1112223",
        "numero_matricula": "9999",
        "ccir": "44444",
        "sigef_codigo": "SIGEF99"
    }

    try:
        up = UnidadeProdutivaCreate(**payload_invalido)
        dump = up.model_dump()
        assert "codigo_car" not in dump, "Vazamento de codigo_car"
        assert "nirf" not in dump, "Vazamento de nirf"
        assert "ccir" not in dump, "Vazamento de ccir"
        assert "numero_matricula" not in dump, "Vazamento de numero_matricula"
        assert "sigef_codigo" not in dump, "Vazamento de sigef_codigo"
    except ValidationError:
        pass
