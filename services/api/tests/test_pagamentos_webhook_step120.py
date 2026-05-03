"""Step 120 — Testes: webhook de pagamento e ativação de créditos de IA"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from pagamentos.webhook_router import _ativar_creditos, _validar_secret
from fastapi import HTTPException


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_solicitacao(
    solicitacao_id: uuid.UUID,
    tenant_id: uuid.UUID,
    status_pagamento: str = "PENDENTE",
    tipo: str = "CREDITOS_IA",
    quantidade: int = 100,
):
    sol = MagicMock()
    sol.id = solicitacao_id
    sol.tenant_id = tenant_id
    sol.tipo = tipo
    sol.status_pagamento = status_pagamento
    sol.status = "ABERTA"
    sol.detalhes = {"quantidade": quantidade}
    sol.updated_at = datetime.now(timezone.utc)
    return sol


def _mock_session(solicitacao):
    session = AsyncMock()
    session.get = AsyncMock(return_value=solicitacao)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    # Suporte a context manager (async with async_session_maker())
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, session


# ── testes de _validar_secret ─────────────────────────────────────────────

def test_validar_secret_sem_configuracao_passa():
    """Sem secret configurado (dev), qualquer header é aceito."""
    with patch("pagamentos.webhook_router.settings") as mock_settings:
        mock_settings.pagamentos_webhook_secret = ""
        _validar_secret("qualquer-coisa")  # não deve levantar


def test_validar_secret_correto_passa():
    with patch("pagamentos.webhook_router.settings") as mock_settings:
        mock_settings.pagamentos_webhook_secret = "meu-secret"
        _validar_secret("meu-secret")  # não deve levantar


def test_validar_secret_incorreto_rejeita():
    with patch("pagamentos.webhook_router.settings") as mock_settings:
        mock_settings.pagamentos_webhook_secret = "meu-secret"
        with pytest.raises(HTTPException) as exc:
            _validar_secret("errado")
        assert exc.value.status_code == 401


# ── testes de _ativar_creditos ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ativar_creditos_cria_pacote():
    """Pagamento PAID cria pacote de créditos e marca solicitação como PAGO."""
    sol_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    solicitacao = _make_solicitacao(sol_id, tenant_id, status_pagamento="PENDENTE")
    cm, session = _mock_session(solicitacao)

    with patch("pagamentos.webhook_router.async_session_maker", return_value=cm):
        await _ativar_creditos(sol_id)

    session.add.assert_called_once()
    pacote_criado = session.add.call_args[0][0]
    assert pacote_criado.quantidade_creditos == 100
    assert pacote_criado.origem == "PAGAMENTO"
    assert pacote_criado.status == "ATIVO"
    assert pacote_criado.tenant_id == tenant_id
    assert solicitacao.status_pagamento == "PAGO"
    assert solicitacao.status == "CONCLUIDA"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ativar_creditos_idempotente():
    """Webhook duplicado (já PAGO) não cria novo pacote."""
    sol_id = uuid.uuid4()
    solicitacao = _make_solicitacao(sol_id, uuid.uuid4(), status_pagamento="PAGO")
    cm, session = _mock_session(solicitacao)

    with patch("pagamentos.webhook_router.async_session_maker", return_value=cm):
        await _ativar_creditos(sol_id)

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ativar_creditos_tipo_invalido_ignorado():
    """Solicitação com tipo diferente de CREDITOS_IA é ignorada."""
    sol_id = uuid.uuid4()
    solicitacao = _make_solicitacao(sol_id, uuid.uuid4(), tipo="UPGRADE_PLANO")
    cm, session = _mock_session(solicitacao)

    with patch("pagamentos.webhook_router.async_session_maker", return_value=cm):
        await _ativar_creditos(sol_id)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_ativar_creditos_sem_quantidade_ignorado():
    """Solicitação sem quantidade nos detalhes não cria pacote."""
    sol_id = uuid.uuid4()
    solicitacao = _make_solicitacao(sol_id, uuid.uuid4(), quantidade=0)
    cm, session = _mock_session(solicitacao)

    with patch("pagamentos.webhook_router.async_session_maker", return_value=cm):
        await _ativar_creditos(sol_id)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_ativar_creditos_solicitacao_nao_encontrada():
    """Solicitação inexistente não levanta exceção — apenas loga."""
    sol_id = uuid.uuid4()
    cm, session = _mock_session(None)

    with patch("pagamentos.webhook_router.async_session_maker", return_value=cm):
        await _ativar_creditos(sol_id)  # não deve levantar

    session.add.assert_not_called()
