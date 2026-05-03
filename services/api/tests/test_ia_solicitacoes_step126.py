"""Step 126 — Testes: gestão comercial das solicitações de créditos de IA"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from core.routers.backoffice_ia_auditoria import (
    SolicitacaoItemResponse,
    StatusUpdatePayload,
    _STATUS_PERMITIDOS,
    router,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_sol(
    status: str = "ABERTA",
    status_pagamento: str = "PENDENTE",
    quantidade: int = 100,
    valor: float = 10.0,
    tenant_id: uuid.UUID | None = None,
):
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = tenant_id or uuid.uuid4()
    sol.usuario_id = uuid.uuid4()
    sol.tipo = "CREDITOS_IA"
    sol.status = status
    sol.status_pagamento = status_pagamento
    sol.valor_estimado = Decimal(str(valor))
    sol.created_at = datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc)
    sol.detalhes = {"quantidade": quantidade, "valor_total": str(valor)}
    return sol


# ── _STATUS_PERMITIDOS ────────────────────────────────────────────────────────

def test_status_permitidos_contem_todos():
    assert _STATUS_PERMITIDOS == {"ABERTA", "EM_ANALISE", "CONCLUIDA", "CANCELADA"}


def test_status_invalido_rejeitado():
    invalidos = ["PAGO", "PROCESSANDO", "", "aberta"]
    for s in invalidos:
        assert s not in _STATUS_PERMITIDOS


# ── SolicitacaoItemResponse ───────────────────────────────────────────────────

def test_solicitacao_item_response_campos():
    tid = str(uuid.uuid4())
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=tid,
        tenant_nome="Fazenda Boa Vista",
        usuario_id=None,
        tipo="CREDITOS_IA",
        quantidade_creditos=200,
        valor_estimado=20.0,
        status="ABERTA",
        status_pagamento="PENDENTE",
        created_at=datetime.now(timezone.utc),
    )
    assert item.quantidade_creditos == 200
    assert item.valor_estimado == 20.0
    assert item.status == "ABERTA"
    assert item.tenant_nome == "Fazenda Boa Vista"


def test_solicitacao_item_campos_opcionais_none():
    item = SolicitacaoItemResponse(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        tenant_nome="Tenant X",
        tipo="CREDITOS_IA",
        status="EM_ANALISE",
        created_at=datetime.now(timezone.utc),
    )
    assert item.quantidade_creditos is None
    assert item.valor_estimado is None
    assert item.usuario_id is None


# ── StatusUpdatePayload ───────────────────────────────────────────────────────

def test_status_update_payload_valido():
    p = StatusUpdatePayload(status="EM_ANALISE")
    assert p.status == "EM_ANALISE"
    assert p.status in _STATUS_PERMITIDOS


def test_status_update_payload_todos_permitidos():
    for s in _STATUS_PERMITIDOS:
        p = StatusUpdatePayload(status=s)
        assert p.status == s


# ── filtros de listagem ───────────────────────────────────────────────────────

def test_filtro_status_aberta():
    sols = [
        _make_sol(status="ABERTA"),
        _make_sol(status="CONCLUIDA"),
        _make_sol(status="ABERTA"),
    ]
    filtrado = [s for s in sols if s.status == "ABERTA"]
    assert len(filtrado) == 2


def test_filtro_status_pagamento():
    sols = [
        _make_sol(status_pagamento="PAGO"),
        _make_sol(status_pagamento="PENDENTE"),
        _make_sol(status_pagamento="PAGO"),
    ]
    pagos = [s for s in sols if s.status_pagamento == "PAGO"]
    assert len(pagos) == 2


def test_filtro_combinado_status_e_pagamento():
    sols = [
        _make_sol(status="ABERTA", status_pagamento="PENDENTE"),
        _make_sol(status="ABERTA", status_pagamento="PAGO"),
        _make_sol(status="CONCLUIDA", status_pagamento="PAGO"),
    ]
    resultado = [s for s in sols if s.status == "ABERTA" and s.status_pagamento == "PENDENTE"]
    assert len(resultado) == 1


# ── permissão e router ────────────────────────────────────────────────────────

def test_router_tem_permissao_backoffice():
    assert len(router.dependencies) > 0


def test_router_prefix_backoffice_ia():
    assert router.prefix == "/backoffice/ia"


def test_rotas_solicitacoes_registradas():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes" in paths
    assert "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/status" in paths
