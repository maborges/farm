from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from notificacoes.schemas import NotificacaoCreate
from notificacoes.service import NotificacaoService


@pytest.mark.asyncio
async def test_rls_message_update_uses_scoped_database_function():
    session = AsyncMock()
    session.info = {"rls_dev_restricted_route": True}
    result = Mock()
    result.scalar_one.return_value = True
    session.execute.return_value = result
    service = NotificacaoService(session, uuid4())
    notification_id = uuid4()

    updated = await service._persistir_mensagem_gerada(notification_id, "Mensagem IA")

    assert updated is True
    statement = session.execute.await_args.args[0]
    assert "farms.update_notification_message" in str(statement)
    assert session.execute.await_args.args[1] == {
        "notification_id": notification_id,
        "message": "Mensagem IA",
    }
    session.get.assert_not_awaited()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rls_message_update_does_not_fallback_when_function_fails():
    session = AsyncMock()
    session.info = {"rls_dev_restricted_route": True}
    session.execute.side_effect = RuntimeError("function unavailable")
    service = NotificacaoService(session, uuid4())

    with pytest.raises(RuntimeError, match="function unavailable"):
        await service._persistir_mensagem_gerada(uuid4(), "Mensagem IA")

    session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_rls_email_fanout_uses_tenant_scoped_function(monkeypatch):
    recipient_rows = Mock()
    recipient_rows.scalars.return_value.all.return_value = ["tenant-user@example.test"]
    session = AsyncMock()
    session.info = {"rls_dev_restricted_route": True}
    session.execute.return_value = recipient_rows
    service = NotificacaoService(session, uuid4())
    sent = []

    async def send_email(email, subject, message):
        sent.append((email, subject, message))

    monkeypatch.setattr("notificacoes.email_service.enviar_email", send_email)
    notification = SimpleNamespace(id=uuid4(), titulo="Alerta", nivel="DANGER")

    await service._enviar_emails_por_preferencia(notification, "OPORTUNIDADE", "Mensagem")

    statement = session.execute.await_args.args[0]
    assert "farms.notification_recipient_emails" in str(statement)
    assert session.execute.await_args.args[1] == {"notification_id": notification.id}
    assert sent == [(
        "tenant-user@example.test",
        "DeepFarms — Alerta Inteligente: Alerta",
        "Mensagem",
    )]


@pytest.mark.asyncio
async def test_restricted_background_task_propagates_authenticated_context(monkeypatch):
    import asyncio

    from core import database
    from notificacoes.service import manager

    tenant_id, user_id = uuid4(), uuid4()
    notification = SimpleNamespace(
        id=uuid4(), tenant_id=tenant_id, tipo="ALERTA", titulo="Alerta",
        mensagem="Original", nivel="WARNING", created_at=datetime(2026, 1, 1),
    )
    request_session = AsyncMock()
    request_session.info = {
        "rls_dev_restricted_route": True,
        "tenant_id": tenant_id,
        "user_id": user_id,
    }
    cooldown_result = Mock()
    cooldown_result.scalar_one_or_none.return_value = None
    request_session.execute.return_value = cooldown_result
    service = NotificacaoService(request_session, tenant_id)
    service.create = AsyncMock(return_value=notification)

    background = AsyncMock()
    background.info = {}
    background.__aenter__.return_value = background
    seen_context = []
    spawned = []

    async def generated_message(self, data):
        seen_context.append(dict(self.session.info))
        return data.mensagem

    async def no_push(*args, **kwargs):
        return None

    def restricted_factory():
        return background

    def legacy_factory():
        raise AssertionError("restricted notification task used the legacy pool")

    monkeypatch.setattr(database, "rls_dev_async_session_maker", restricted_factory)
    monkeypatch.setattr(database, "async_session_maker", legacy_factory)
    monkeypatch.setattr(NotificacaoService, "gerar_mensagem_ia", generated_message)
    monkeypatch.setattr(manager, "push", no_push)
    monkeypatch.setattr(asyncio, "create_task", lambda coroutine: spawned.append(coroutine))

    await service.criar_e_push(NotificacaoCreate(
        tipo="ALERTA", titulo="Alerta", mensagem="Original", nivel="WARNING"
    ))
    assert len(spawned) == 1
    await spawned.pop()

    assert seen_context == [{
        "rls_dev_restricted_route": True,
        "tenant_id": tenant_id,
        "user_id": user_id,
    }]
    request_session.commit.assert_awaited_once()
