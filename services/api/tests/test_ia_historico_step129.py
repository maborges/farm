"""Step 129 — Testes: histórico comercial da solicitação de IA"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from core.models.solicitacoes_historico import SolicitacaoHistorico
from core.routers.backoffice_ia_auditoria import (
    HistoricoItemResponse,
    _registrar_historico,
    router,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial


def _make_sol(status: str = "ABERTA") -> MagicMock:
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = status
    sol.observacao_comercial = None
    sol.responsavel_usuario_id = None
    return sol


# ── model ─────────────────────────────────────────────────────────────────────

def test_historico_model_campos():
    assert hasattr(SolicitacaoHistorico, "id")
    assert hasattr(SolicitacaoHistorico, "solicitacao_id")
    assert hasattr(SolicitacaoHistorico, "tenant_id")
    assert hasattr(SolicitacaoHistorico, "tipo_evento")
    assert hasattr(SolicitacaoHistorico, "valor_anterior")
    assert hasattr(SolicitacaoHistorico, "valor_novo")
    assert hasattr(SolicitacaoHistorico, "observacao")
    assert hasattr(SolicitacaoHistorico, "created_at")


def test_historico_tablename():
    assert SolicitacaoHistorico.__tablename__ == "billing_solicitacoes_comerciais_historico"


# ── HistoricoItemResponse ─────────────────────────────────────────────────────

def test_historico_item_response_status():
    h = HistoricoItemResponse(
        id=str(uuid.uuid4()),
        tipo_evento="STATUS_ALTERADO",
        valor_anterior="ABERTA",
        valor_novo="EM_ANALISE",
        created_at=datetime.now(timezone.utc),
    )
    assert h.tipo_evento == "STATUS_ALTERADO"
    assert h.valor_anterior == "ABERTA"
    assert h.valor_novo == "EM_ANALISE"


def test_historico_item_response_responsavel():
    uid = str(uuid.uuid4())
    h = HistoricoItemResponse(
        id=str(uuid.uuid4()),
        tipo_evento="RESPONSAVEL_ALTERADO",
        valor_anterior=None,
        valor_novo=uid,
        created_at=datetime.now(timezone.utc),
    )
    assert h.tipo_evento == "RESPONSAVEL_ALTERADO"
    assert h.valor_novo == uid


def test_historico_item_response_observacao():
    h = HistoricoItemResponse(
        id=str(uuid.uuid4()),
        tipo_evento="OBSERVACAO_ALTERADA",
        valor_anterior="obs antiga",
        valor_novo="obs nova",
        created_at=datetime.now(timezone.utc),
    )
    assert h.tipo_evento == "OBSERVACAO_ALTERADA"


def test_historico_campos_opcionais_none():
    h = HistoricoItemResponse(
        id=str(uuid.uuid4()),
        tipo_evento="STATUS_ALTERADO",
        created_at=datetime.now(timezone.utc),
    )
    assert h.valor_anterior is None
    assert h.valor_novo is None
    assert h.observacao is None


# ── _registrar_historico ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registrar_historico_adiciona_na_session():
    sol = _make_sol()
    session = MagicMock()
    session.add = MagicMock()

    await _registrar_historico(session, sol, "STATUS_ALTERADO", "ABERTA", "CONCLUIDA")

    session.add.assert_called_once()
    hist_obj = session.add.call_args[0][0]
    assert isinstance(hist_obj, SolicitacaoHistorico)
    assert hist_obj.tipo_evento == "STATUS_ALTERADO"
    assert hist_obj.valor_anterior == "ABERTA"
    assert hist_obj.valor_novo == "CONCLUIDA"
    assert hist_obj.solicitacao_id == sol.id
    assert hist_obj.tenant_id == sol.tenant_id


@pytest.mark.asyncio
async def test_registrar_historico_responsavel():
    sol = _make_sol()
    uid = str(uuid.uuid4())
    session = MagicMock()
    session.add = MagicMock()

    await _registrar_historico(session, sol, "RESPONSAVEL_ALTERADO", None, uid)

    hist_obj = session.add.call_args[0][0]
    assert hist_obj.tipo_evento == "RESPONSAVEL_ALTERADO"
    assert hist_obj.valor_anterior is None
    assert hist_obj.valor_novo == uid


# ── router ────────────────────────────────────────────────────────────────────

def test_rota_historico_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/historico" in paths


def test_router_tem_permissao():
    assert len(router.dependencies) > 0
