"""Step 133 — Testes: lembretes automáticos de follow-up comercial."""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch, call

from automacoes.followup_worker import (
    TIPO_FOLLOWUP,
    JANELA_HORAS,
    COOLDOWN_HORAS,
    _ja_notificado,
    process_followups,
    _enviar_email_followup,
)
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from notificacoes.models import Notificacao


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_sol(
    followup_em: datetime,
    status: str = "ABERTA",
    responsavel_id: uuid.UUID | None = None,
) -> MagicMock:
    sol = MagicMock(spec=SolicitacaoComercial)
    sol.id = uuid.uuid4()
    sol.tenant_id = uuid.uuid4()
    sol.status = status
    sol.responsavel_usuario_id = responsavel_id or uuid.uuid4()
    sol.proximo_followup_em = followup_em
    sol.valor_estimado = Decimal("100.00")
    return sol


def _make_session(solicitacoes: list, notif_existente=None, tenant_nome="Fazenda Teste"):
    session = MagicMock()

    # scalars().all() retorna a lista de solicitações
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = solicitacoes

    # _ja_notificado: execute retorna notif_existente
    cooldown_result = MagicMock()
    cooldown_result.scalar_one_or_none.return_value = notif_existente

    session.execute = AsyncMock(side_effect=[exec_result, cooldown_result])
    session.add = MagicMock()
    session.commit = AsyncMock()

    tenant_mock = MagicMock()
    tenant_mock.nome = tenant_nome
    session.get = AsyncMock(return_value=tenant_mock)

    return session


# ── constantes ────────────────────────────────────────────────────────────────

def test_tipo_followup():
    assert TIPO_FOLLOWUP == "FOLLOWUP_COMERCIAL"


def test_janela_e_cooldown():
    assert JANELA_HORAS == 1
    assert COOLDOWN_HORAS == 24


# ── _ja_notificado ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ja_notificado_true():
    session = MagicMock()
    notif = MagicMock(spec=Notificacao)
    result = MagicMock()
    result.scalar_one_or_none.return_value = notif
    session.execute = AsyncMock(return_value=result)

    assert await _ja_notificado(session, uuid.uuid4(), uuid.uuid4(), "WARNING") is True


@pytest.mark.asyncio
async def test_ja_notificado_false():
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    assert await _ja_notificado(session, uuid.uuid4(), uuid.uuid4(), "WARNING") is False


# ── process_followups ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sem_followups_retorna_zero():
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=exec_result)

    total = await process_followups(session)
    assert total == 0
    session.commit.assert_not_called() if hasattr(session, 'commit') else None


@pytest.mark.asyncio
async def test_followup_dentro_da_janela_gera_warning():
    now = datetime.now(timezone.utc)
    followup_em = now + timedelta(minutes=30)  # dentro da janela de 1h
    sol = _make_sol(followup_em)

    session = MagicMock()
    exec_sol = MagicMock()
    exec_sol.scalars.return_value.all.return_value = [sol]
    exec_cooldown = MagicMock()
    exec_cooldown.scalar_one_or_none.return_value = None  # sem cooldown

    session.execute = AsyncMock(side_effect=[exec_sol, exec_cooldown])
    session.add = MagicMock()
    session.commit = AsyncMock()

    tenant_mock = MagicMock()
    tenant_mock.nome = "Fazenda Teste"
    session.get = AsyncMock(return_value=tenant_mock)

    total = await process_followups(session)

    assert total == 1
    session.add.assert_called_once()
    notif_adicionada = session.add.call_args[0][0]
    assert isinstance(notif_adicionada, Notificacao)
    assert notif_adicionada.nivel == "WARNING"
    assert notif_adicionada.tipo == TIPO_FOLLOWUP
    assert notif_adicionada.origem == "followup"
    assert notif_adicionada.origem_id == str(sol.id)


@pytest.mark.asyncio
async def test_followup_atrasado_gera_danger():
    now = datetime.now(timezone.utc)
    followup_em = now - timedelta(hours=2)  # atrasado
    sol = _make_sol(followup_em)

    session = MagicMock()
    exec_sol = MagicMock()
    exec_sol.scalars.return_value.all.return_value = [sol]
    exec_cooldown = MagicMock()
    exec_cooldown.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(side_effect=[exec_sol, exec_cooldown])
    session.add = MagicMock()
    session.commit = AsyncMock()

    tenant_mock = MagicMock()
    tenant_mock.nome = "Fazenda X"
    admin_mock = MagicMock()
    admin_mock.email = "resp@example.com"
    session.get = AsyncMock(side_effect=[tenant_mock, admin_mock])

    with patch("automacoes.followup_worker._enviar_email_followup", new_callable=AsyncMock) as mock_email:
        total = await process_followups(session)

    assert total == 1
    notif_adicionada = session.add.call_args[0][0]
    assert notif_adicionada.nivel == "DANGER"
    mock_email.assert_called_once()


@pytest.mark.asyncio
async def test_followup_concluido_nao_buscado():
    """Solicitações CONCLUIDAS são filtradas na query — simular lista vazia."""
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=exec_result)

    total = await process_followups(session)
    assert total == 0


@pytest.mark.asyncio
async def test_nao_duplica_com_cooldown():
    now = datetime.now(timezone.utc)
    followup_em = now + timedelta(minutes=10)
    sol = _make_sol(followup_em)

    session = MagicMock()
    exec_sol = MagicMock()
    exec_sol.scalars.return_value.all.return_value = [sol]
    exec_cooldown = MagicMock()
    exec_cooldown.scalar_one_or_none.return_value = MagicMock()  # já existe

    session.execute = AsyncMock(side_effect=[exec_sol, exec_cooldown])
    session.add = MagicMock()
    session.commit = AsyncMock()

    total = await process_followups(session)
    assert total == 0
    session.add.assert_not_called()


# ── _enviar_email_followup ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_email_enviado_quando_admin_tem_email():
    session = MagicMock()
    admin_mock = MagicMock()
    admin_mock.email = "admin@example.com"
    session.get = AsyncMock(return_value=admin_mock)

    with patch("notificacoes.email_service.enviar_email", new_callable=AsyncMock):
        with patch("asyncio.create_task") as mock_task:
            await _enviar_email_followup(session, uuid.uuid4(), "Fazenda Y", "msg de teste")
            mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_email_nao_enviado_sem_admin():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    with patch("notificacoes.email_service.enviar_email", new_callable=AsyncMock):
        with patch("asyncio.create_task") as mock_task:
            await _enviar_email_followup(session, uuid.uuid4(), "Fazenda Z", "msg")
            mock_task.assert_not_called()


# ── worker integração ─────────────────────────────────────────────────────────

def test_run_followup_check_importavel():
    from automacoes.worker import run_followup_check
    assert callable(run_followup_check)


def test_process_followups_importavel():
    from automacoes.followup_worker import process_followups
    assert callable(process_followups)
