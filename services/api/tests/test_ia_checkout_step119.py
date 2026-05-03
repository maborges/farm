"""Step 119 — Testes: checkout de créditos de IA"""
import pytest
from decimal import Decimal
from ia.router import _calcular_valor, _gerar_link_pagamento


def test_calcular_valor_100_creditos():
    assert _calcular_valor(100) == Decimal("10.00")


def test_calcular_valor_200_creditos():
    assert _calcular_valor(200) == Decimal("18.00")


def test_calcular_valor_500_creditos():
    assert _calcular_valor(500) == Decimal("40.00")


def test_calcular_valor_1000_creditos():
    assert _calcular_valor(1000) == Decimal("70.00")


def test_calcular_valor_50_creditos():
    assert _calcular_valor(50) == Decimal("5.00")


def test_gerar_link_pagamento_contem_protocolo():
    link = _gerar_link_pagamento("IA-ABCD1234", 100, Decimal("10.00"))
    assert "wa.me" in link
    assert "IA-ABCD1234" in link


def test_gerar_link_pagamento_contem_quantidade():
    link = _gerar_link_pagamento("IA-XYZ", 500, Decimal("40.00"))
    assert "500" in link


def test_gerar_link_pagamento_contem_valor():
    link = _gerar_link_pagamento("IA-XYZ", 100, Decimal("10.00"))
    assert "10" in link
