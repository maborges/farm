"""Step 124 — Testes: exportação CSV da auditoria de créditos de IA"""
import csv
import io
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from core.routers.backoffice_ia_auditoria import (
    _build_filtros,
    _row_to_item,
    _CSV_COLUNAS,
    exportar_auditoria_csv,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_solicitacao(
    status_pagamento: str = "PAGO",
    quantidade: int = 100,
    valor: float = 10.0,
    custo: float = 3.5,
    margem: float = 6.5,
    pct: float = 65.0,
):
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = "CONCLUIDA"
    sol.status_pagamento = status_pagamento
    sol.valor_estimado = Decimal(str(valor))
    sol.created_at = datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc)
    sol.detalhes = {
        "quantidade": quantidade,
        "valor_total": str(valor),
        "custo_estimado": str(custo),
        "margem_estimada": str(margem),
        "margem_percentual": str(pct),
    }
    return sol


# ── _build_filtros ────────────────────────────────────────────────────────────

def test_build_filtros_sem_parametros():
    filtros = _build_filtros(None, None, None)
    assert len(filtros) == 1  # só tipo == CREDITOS_IA


def test_build_filtros_com_status():
    filtros = _build_filtros("PAGO", None, None)
    assert len(filtros) == 2


def test_build_filtros_com_datas():
    from datetime import date
    filtros = _build_filtros(None, date(2026, 1, 1), date(2026, 12, 31))
    assert len(filtros) == 3


# ── _row_to_item ──────────────────────────────────────────────────────────────

def test_row_to_item_extrai_campos():
    sol = _make_solicitacao("PAGO", 100, 10.0, 3.5, 6.5, 65.0)
    item = _row_to_item(sol)
    assert item.quantidade_creditos == 100
    assert item.valor_total == 10.0
    assert item.custo_estimado == 3.5
    assert item.margem_percentual == 65.0
    assert item.status_pagamento == "PAGO"


# ── CSV colunas ───────────────────────────────────────────────────────────────

def test_csv_colunas_completas():
    esperadas = {
        "solicitacao_id", "tenant_id", "quantidade_creditos",
        "valor_total", "custo_estimado", "margem_estimada",
        "margem_percentual", "status_pagamento", "created_at",
    }
    assert set(_CSV_COLUNAS) == esperadas


def test_csv_gerado_corretamente():
    """Simula a geração do CSV com um item e verifica cabeçalho e valores."""
    sol = _make_solicitacao("PAGO", 200, 20.0, 7.0, 13.0, 65.0)
    item = _row_to_item(sol)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUNAS, extrasaction="ignore")
    writer.writeheader()
    writer.writerow({
        "solicitacao_id": item.solicitacao_id,
        "tenant_id": item.tenant_id,
        "quantidade_creditos": item.quantidade_creditos,
        "valor_total": f"{item.valor_total:.2f}",
        "custo_estimado": f"{item.custo_estimado:.2f}",
        "margem_estimada": f"{item.margem_estimada:.2f}",
        "margem_percentual": f"{item.margem_percentual:.2f}",
        "status_pagamento": item.status_pagamento,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })
    output.seek(0)
    reader = csv.DictReader(output)
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["quantidade_creditos"] == "200"
    assert rows[0]["valor_total"] == "20.00"
    assert rows[0]["status_pagamento"] == "PAGO"


# ── permissão ─────────────────────────────────────────────────────────────────

def test_router_exportar_csv_tem_permissao():
    from core.routers.backoffice_ia_auditoria import router
    assert len(router.dependencies) > 0
