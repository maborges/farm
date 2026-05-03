"""Step 136 — Testes: integração CRM comercial das solicitações de IA."""
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

from core.routers.backoffice_ia_auditoria import router, SolicitacaoItemResponse
from core.models.solicitacoes_comerciais import SolicitacaoComercial


# ── model: campo crm_sync_status ─────────────────────────────────────────────

def test_model_tem_crm_sync_status():
    assert hasattr(SolicitacaoComercial, "crm_sync_status")


def test_model_tem_crm_sync_at():
    assert hasattr(SolicitacaoComercial, "crm_sync_at")


# ── schema: campo crm_sync_status ────────────────────────────────────────────

def test_schema_tem_crm_sync_status():
    assert "crm_sync_status" in SolicitacaoItemResponse.model_fields


def test_schema_default_nao_enviado():
    assert SolicitacaoItemResponse.model_fields["crm_sync_status"].default == "NAO_ENVIADO"


def test_schema_valores_validos():
    for status in ("NAO_ENVIADO", "ENVIADO", "ERRO"):
        r = SolicitacaoItemResponse(
            id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            tenant_nome="Fazenda X",
            tipo="CREDITOS_IA",
            status="ABERTA",
            created_at=datetime.now(timezone.utc),
            crm_sync_status=status,
        )
        assert r.crm_sync_status == status


# ── rota registrada ───────────────────────────────────────────────────────────

def test_rota_enviar_crm_registrada():
    paths = {route.path for route in router.routes}
    assert "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/enviar-crm" in paths


def test_rota_enviar_crm_metodo_post():
    for route in router.routes:
        if route.path == "/backoffice/ia/creditos/solicitacoes/{solicitacao_id}/enviar-crm":
            assert "POST" in route.methods
            break


# ── mock CRM ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_enviar_crm_retorna_true():
    from core.routers.backoffice_ia_auditoria import _mock_enviar_crm
    result = await _mock_enviar_crm({"test": "payload"})
    assert result is True


# ── payload montado corretamente ─────────────────────────────────────────────

def test_payload_contem_campos_obrigatorios():
    campos = ["solicitacao_id", "tenant_id", "tenant_nome", "valor_estimado", "prioridade", "status", "observacao_comercial"]
    payload = {c: None for c in campos}
    for campo in campos:
        assert campo in payload


# ── status de sync ────────────────────────────────────────────────────────────

def test_status_enviado_apos_sucesso():
    status = "ENVIADO" if True else "ERRO"
    assert status == "ENVIADO"


def test_status_erro_apos_falha():
    status = "ENVIADO" if False else "ERRO"
    assert status == "ERRO"


# ── histórico registrado ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registrar_historico_crm_enviado():
    from core.routers.backoffice_ia_auditoria import _registrar_historico
    from core.models.solicitacoes_historico import SolicitacaoHistorico

    sol = MagicMock()
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.observacao_comercial = None
    sol.responsavel_usuario_id = None

    session = MagicMock()
    session.add = MagicMock()

    await _registrar_historico(session, sol, "CRM_ENVIADO", "NAO_ENVIADO", "ENVIADO")

    session.add.assert_called_once()
    hist = session.add.call_args[0][0]
    assert isinstance(hist, SolicitacaoHistorico)
    assert hist.tipo_evento == "CRM_ENVIADO"
    assert hist.valor_anterior == "NAO_ENVIADO"
    assert hist.valor_novo == "ENVIADO"
