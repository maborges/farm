"""Testes do espelhamento de OperationalAlert em Notificacao (ponte alert_engine → sino).

Antes, alert_engine/ só gravava em `operational_alerts`, visível só no card-resumo
do dashboard (GET /alerts/summary) — nunca chegava ao sino do usuário via WS.
AlertLifecycleService.create_or_update_alert agora espelha em Notificacao ao
criar um alerta novo (não em updates de alerta já ativo), usando uma sessão
própria (não a do chamador) para não quebrar o SAVEPOINT do scheduler.
"""
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from alert_engine.service import AlertLifecycleService


def _alert(source_type: str = "AGRICULTURA_OPERACAO_ATRASADA", source_id: str | None = None) -> MagicMock:
    alert = MagicMock()
    alert.id = uuid.uuid4()
    alert.title = "Operação atrasada"
    alert.message = "5 dias de atraso"
    alert.severity = "CRITICAL"
    alert.source_type = source_type
    alert.source_id = source_id or str(uuid.uuid4())
    alert.dedupe_key = f"agricultura:operacao_atrasada:{alert.source_id}"
    alert.domain = "AGRICULTURE"
    return alert


def _fake_async_session_maker():
    @asynccontextmanager
    async def _maker():
        yield AsyncMock()
    return _maker


@pytest.mark.asyncio
async def test_notificar_usuarios_cria_notificacao_com_nivel_mapeado():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = AlertLifecycleService(session, tenant_id)
    alert = _alert()

    with patch("core.database.async_session_maker", _fake_async_session_maker()), \
         patch("notificacoes.service.NotificacaoService") as MockNotifSvc:
        MockNotifSvc.return_value.criar_sem_duplicar = AsyncMock()
        await svc._notificar_usuarios(alert)

    dados = MockNotifSvc.return_value.criar_sem_duplicar.call_args.args[0]
    assert dados.tipo == "AGRICULTURA_OPERACAO_ATRASADA"
    assert dados.nivel == "DANGER"  # CRITICAL -> DANGER
    assert dados.origem == "alert_engine"
    assert dados.origem_id == alert.source_id


@pytest.mark.asyncio
async def test_notificar_usuarios_agricultura_operacao_atrasada_ganha_acao_adiar():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = AlertLifecycleService(session, tenant_id)
    alert = _alert(source_type="AGRICULTURA_OPERACAO_ATRASADA")

    with patch("core.database.async_session_maker", _fake_async_session_maker()), \
         patch("notificacoes.service.NotificacaoService") as MockNotifSvc:
        MockNotifSvc.return_value.criar_sem_duplicar = AsyncMock()
        await svc._notificar_usuarios(alert)

    dados = MockNotifSvc.return_value.criar_sem_duplicar.call_args.args[0]
    acoes = dados.meta["acoes"]
    assert len(acoes) == 1
    assert acoes[0]["endpoint"] == f"/operacoes/{alert.source_id}"
    nova_data = date.fromisoformat(acoes[0]["body"]["data_prevista"])
    assert nova_data == date.today() + timedelta(days=3)


@pytest.mark.asyncio
async def test_notificar_usuarios_tipo_sem_mapeamento_nao_ganha_acoes():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = AlertLifecycleService(session, tenant_id)
    alert = _alert(source_type="ALGUM_OUTRO_ALERTA_QUALQUER")

    with patch("core.database.async_session_maker", _fake_async_session_maker()), \
         patch("notificacoes.service.NotificacaoService") as MockNotifSvc:
        MockNotifSvc.return_value.criar_sem_duplicar = AsyncMock()
        await svc._notificar_usuarios(alert)

    dados = MockNotifSvc.return_value.criar_sem_duplicar.call_args.args[0]
    assert "acoes" not in dados.meta


@pytest.mark.asyncio
async def test_notificar_usuarios_falha_isolada_nao_propaga():
    """Falha ao criar Notificacao não deve impedir o fluxo principal do alert_engine."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    svc = AlertLifecycleService(session, tenant_id)
    alert = _alert()

    with patch("core.database.async_session_maker", _fake_async_session_maker()), \
         patch("notificacoes.service.NotificacaoService") as MockNotifSvc:
        MockNotifSvc.return_value.criar_sem_duplicar = AsyncMock(side_effect=RuntimeError("db down"))
        await svc._notificar_usuarios(alert)  # não deve levantar


@pytest.mark.asyncio
async def test_notificar_usuarios_nao_usa_sessao_do_chamador():
    """Regressão: usar self.session quebrava o SAVEPOINT do scheduler (ResourceClosedError)."""
    tenant_id = uuid.uuid4()
    session_do_chamador = AsyncMock()
    svc = AlertLifecycleService(session_do_chamador, tenant_id)
    alert = _alert()

    with patch("core.database.async_session_maker", _fake_async_session_maker()) as mock_maker, \
         patch("notificacoes.service.NotificacaoService") as MockNotifSvc:
        MockNotifSvc.return_value.criar_sem_duplicar = AsyncMock()
        await svc._notificar_usuarios(alert)

    # A sessão passada ao NotificacaoService não deve ser a do chamador.
    session_usada = MockNotifSvc.call_args.args[0]
    assert session_usada is not session_do_chamador
    session_do_chamador.commit.assert_not_called()
