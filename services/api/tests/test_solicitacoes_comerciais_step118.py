"""
Step 118 — Testes de solicitações comerciais de IA integradas ao Billing/CRM.
Cobre: criação de SolicitacaoComercial, protocolo gerado, evento logado.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from core.models.solicitacoes_comerciais import SolicitacaoComercial


# ── Model básico ─────────────────────────────────────────────────────────────

def test_solicitacao_comercial_campos():
    s = SolicitacaoComercial(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tipo="CREDITOS_IA",
        origem="ia_creditos_adicionais",
        detalhes={"quantidade": 100},
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert s.status == "ABERTA"
    assert s.tipo == "CREDITOS_IA"
    assert s.detalhes["quantidade"] == 100


# ── Endpoint POST /ia/creditos/solicitar ────────────────────────────────────

@pytest.mark.asyncio
async def test_solicitar_creditos_registra_solicitacao_comercial():
    """Endpoint deve criar IACreditosPacote E SolicitacaoComercial."""
    from ia.router import solicitar_creditos_ia, SolicitarCreditosPayload

    pacote_mock = MagicMock()
    pacote_mock.id = uuid.uuid4()
    pacote_mock.quantidade_creditos = 100
    pacote_mock.status = "ATIVO"

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    added_objects = []
    def capture_add(obj):
        added_objects.append(obj)
    session.add.side_effect = capture_add

    claims = {"sub": str(uuid.uuid4())}
    tenant_id = uuid.uuid4()
    body = SolicitarCreditosPayload(quantidade=100)

    with patch("ia.router.solicitar_creditos", AsyncMock(return_value=pacote_mock)):
        resp = await solicitar_creditos_ia(body, tenant_id, claims, session)

    # Deve ter adicionado SolicitacaoComercial
    solicitacoes = [o for o in added_objects if isinstance(o, SolicitacaoComercial)]
    assert len(solicitacoes) == 1
    sol = solicitacoes[0]
    assert sol.tipo == "CREDITOS_IA"
    assert sol.origem == "ia_creditos_adicionais"
    assert sol.status == "ABERTA"
    assert sol.detalhes["quantidade"] == 100

    # Deve ter protocolo no response
    assert resp.protocolo.startswith("IA-")
    assert len(resp.protocolo) == 11  # "IA-" + 8 chars
    assert resp.quantidade == 100
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_solicitar_creditos_sem_usuario():
    """Claims sem 'sub' → usuario_id=None, sem erro."""
    from ia.router import solicitar_creditos_ia, SolicitarCreditosPayload

    pacote_mock = MagicMock()
    pacote_mock.id = uuid.uuid4()
    pacote_mock.quantidade_creditos = 50
    pacote_mock.status = "ATIVO"

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    added_objects = []
    session.add.side_effect = lambda o: added_objects.append(o)

    with patch("ia.router.solicitar_creditos", AsyncMock(return_value=pacote_mock)):
        resp = await solicitar_creditos_ia(
            SolicitarCreditosPayload(quantidade=50),
            uuid.uuid4(),
            {},  # sem sub
            session,
        )

    solicitacoes = [o for o in added_objects if isinstance(o, SolicitacaoComercial)]
    assert solicitacoes[0].usuario_id is None
    assert resp.protocolo.startswith("IA-")


@pytest.mark.asyncio
async def test_solicitar_creditos_loga_evento():
    """Deve logar upgrade_intention_created."""
    from ia.router import solicitar_creditos_ia, SolicitarCreditosPayload

    pacote_mock = MagicMock()
    pacote_mock.id = uuid.uuid4()
    pacote_mock.quantidade_creditos = 200
    pacote_mock.status = "ATIVO"

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    log_calls = []

    import loguru
    original_bind = loguru.logger.bind

    def mock_bind(**kwargs):
        log_calls.append(kwargs)
        return MagicMock(info=MagicMock())

    with patch("ia.router.solicitar_creditos", AsyncMock(return_value=pacote_mock)), \
         patch("ia.router.logger") as mock_logger:
        mock_bind_instance = MagicMock()
        mock_bind_instance.info = MagicMock()
        mock_logger.bind.return_value = mock_bind_instance

        await solicitar_creditos_ia(
            SolicitarCreditosPayload(quantidade=200),
            uuid.uuid4(),
            {"sub": str(uuid.uuid4())},
            session,
        )

        bind_kwargs = mock_logger.bind.call_args[1]
        assert bind_kwargs["event"] == "upgrade_intention_created"
        assert bind_kwargs["tipo"] == "CREDITOS_IA"
        assert bind_kwargs["quantidade"] == 200
        mock_bind_instance.info.assert_called_once_with("upgrade_intention_created")
