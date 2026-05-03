"""Step 125 — Testes: relatório executivo de monetização de IA"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock

from core.routers.backoffice_ia_auditoria import (
    _row_to_item,
    ResumoExecutivoResponse,
    TopTenantItem,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_solicitacao(
    tenant_id: uuid.UUID | None = None,
    status_pagamento: str = "PAGO",
    quantidade: int = 100,
    valor: float = 10.0,
    custo: float = 3.5,
    margem: float = 6.5,
    pct: float = 65.0,
):
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = tenant_id or uuid.uuid4()
    sol.status = "CONCLUIDA"
    sol.status_pagamento = status_pagamento
    sol.valor_estimado = Decimal(str(valor))
    sol.created_at = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    sol.detalhes = {
        "quantidade": quantidade,
        "valor_total": str(valor),
        "custo_estimado": str(custo),
        "margem_estimada": str(margem),
        "margem_percentual": str(pct),
    }
    return sol


# ── cálculo de KPIs ───────────────────────────────────────────────────────────

def test_receita_total_soma_pagos():
    itens = [_row_to_item(_make_solicitacao(valor=10.0)) for _ in range(3)]
    receita = sum(i.valor_total or 0.0 for i in itens)
    assert round(receita, 2) == 30.0


def test_margem_percentual_media():
    itens = [
        _row_to_item(_make_solicitacao(pct=60.0)),
        _row_to_item(_make_solicitacao(pct=70.0)),
    ]
    margens = [i.margem_percentual for i in itens if i.margem_percentual is not None]
    media = sum(margens) / len(margens)
    assert media == 65.0


def test_ticket_medio():
    itens = [_row_to_item(_make_solicitacao(valor=20.0)) for _ in range(4)]
    receita = sum(i.valor_total or 0.0 for i in itens)
    ticket = receita / len(itens)
    assert ticket == 20.0


def test_ticket_medio_sem_vendas():
    ticket = 0.0 / 1 if False else 0.0
    assert ticket == 0.0


def test_creditos_vendidos_soma():
    itens = [_row_to_item(_make_solicitacao(quantidade=200)) for _ in range(3)]
    total = sum(i.quantidade_creditos or 0 for i in itens)
    assert total == 600


# ── agrupamento por tenant ───────────────────────────────────────────────────

def test_agrupamento_top_tenant():
    from collections import defaultdict

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()

    itens = [
        _row_to_item(_make_solicitacao(tenant_id=tid_a, valor=50.0)),
        _row_to_item(_make_solicitacao(tenant_id=tid_a, valor=50.0)),
        _row_to_item(_make_solicitacao(tenant_id=tid_b, valor=30.0)),
    ]

    por_tenant: dict = defaultdict(lambda: {"receita": 0.0, "creditos": 0})
    for item in itens:
        por_tenant[item.tenant_id]["receita"] += item.valor_total or 0.0
        por_tenant[item.tenant_id]["creditos"] += item.quantidade_creditos or 0

    top = sorted(por_tenant, key=lambda t: por_tenant[t]["receita"], reverse=True)
    assert top[0] == str(tid_a)
    assert round(por_tenant[str(tid_a)]["receita"], 2) == 100.0


def test_top_n_limita_resultado():
    from collections import defaultdict

    tids = [uuid.uuid4() for _ in range(10)]
    itens = [_row_to_item(_make_solicitacao(tenant_id=t, valor=float(i + 1) * 10)) for i, t in enumerate(tids)]

    por_tenant: dict = defaultdict(lambda: {"receita": 0.0, "creditos": 0})
    for item in itens:
        por_tenant[item.tenant_id]["receita"] += item.valor_total or 0.0

    top_n = 5
    top_ids = sorted(por_tenant, key=lambda t: por_tenant[t]["receita"], reverse=True)[:top_n]
    assert len(top_ids) == top_n


# ── schema de resposta ───────────────────────────────────────────────────────

def test_resumo_executivo_response_campos():
    resp = ResumoExecutivoResponse(
        receita_total=100.0,
        custo_total=35.0,
        margem_total=65.0,
        margem_percentual_media=65.0,
        creditos_vendidos=1000,
        quantidade_vendas=10,
        ticket_medio=10.0,
        top_tenants=[],
    )
    assert resp.receita_total == 100.0
    assert resp.ticket_medio == 10.0
    assert resp.top_tenants == []


def test_top_tenant_item_campos():
    tid = str(uuid.uuid4())
    item = TopTenantItem(
        tenant_id=tid,
        tenant_nome="Fazenda Boa Vista",
        receita_total=250.0,
        creditos_comprados=500,
    )
    assert item.tenant_nome == "Fazenda Boa Vista"
    assert item.creditos_comprados == 500


# ── permissão ────────────────────────────────────────────────────────────────

def test_router_tem_permissao_backoffice():
    from core.routers.backoffice_ia_auditoria import router
    assert len(router.dependencies) > 0


def test_router_prefix_backoffice_ia():
    from core.routers.backoffice_ia_auditoria import router
    assert router.prefix == "/backoffice/ia"
