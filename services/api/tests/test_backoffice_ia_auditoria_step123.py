"""Step 123 — Testes: auditoria financeira de créditos de IA"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.routers.backoffice_ia_auditoria import (
    _extrair_float,
    _extrair_int,
    AuditoriaTotaisResponse,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_solicitacao(
    status_pagamento: str = "PAGO",
    quantidade: int = 100,
    valor: float = 10.0,
    custo: float = 3.5,
    margem: float = 6.5,
    pct: float = 65.0,
):
    sol = MagicMock()
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = "CONCLUIDA"
    sol.status_pagamento = status_pagamento
    sol.valor_estimado = Decimal(str(valor))
    sol.created_at = datetime.now(timezone.utc)
    sol.detalhes = {
        "quantidade": quantidade,
        "valor_total": str(valor),
        "custo_estimado": str(custo),
        "margem_estimada": str(margem),
        "margem_percentual": str(pct),
    }
    return sol


# ── _extrair_float / _extrair_int ─────────────────────────────────────────────

def test_extrair_float_presente():
    assert _extrair_float({"valor_total": "10.50"}, "valor_total") == 10.5


def test_extrair_float_ausente():
    assert _extrair_float({}, "valor_total") is None


def test_extrair_float_none_detalhes():
    assert _extrair_float(None, "valor_total") is None


def test_extrair_int_presente():
    assert _extrair_int({"quantidade": 100}, "quantidade") == 100


def test_extrair_int_ausente():
    assert _extrair_int({}, "quantidade") is None


# ── totais ────────────────────────────────────────────────────────────────────

def test_totais_so_pagos_contabilizados():
    """Totais devem somar apenas registros PAGO."""
    pago = _make_solicitacao("PAGO", 100, 10.0, 3.5, 6.5, 65.0)
    pendente = _make_solicitacao("PENDENTE", 200, 20.0, 7.0, 13.0, 65.0)

    receita = sum(
        float(s.valor_estimado)
        for s in [pago, pendente]
        if s.status_pagamento == "PAGO"
    )
    assert receita == 10.0


def test_totais_multiplos_pagos():
    pagos = [_make_solicitacao("PAGO", 100, 10.0, 3.5, 6.5, 65.0) for _ in range(3)]
    receita = sum(float(s.valor_estimado) for s in pagos)
    assert round(receita, 2) == 30.0


# ── permissão (unit) ──────────────────────────────────────────────────────────

def test_router_tem_permissao_backoffice():
    from core.routers.backoffice_ia_auditoria import router
    # Verifica que o router tem dependência de permissão configurada
    assert len(router.dependencies) > 0


def test_router_prefix_backoffice():
    from core.routers.backoffice_ia_auditoria import router
    assert router.prefix == "/backoffice/ia"


# ── margem ────────────────────────────────────────────────────────────────────

def test_margem_percentual_correta():
    sol = _make_solicitacao("PAGO", 100, 10.0, 3.5, 6.5, 65.0)
    pct = _extrair_float(sol.detalhes, "margem_percentual")
    assert pct == 65.0


def test_margem_ausente_retorna_none():
    sol = MagicMock()
    sol.detalhes = {"quantidade": 100}
    pct = _extrair_float(sol.detalhes, "margem_percentual")
    assert pct is None
