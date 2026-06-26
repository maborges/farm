from __future__ import annotations

import asyncio
import uuid

import pytest

from notifications import (
    EmailNotificationAdapter,
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)


class FakeSMTP:
    instances: list[FakeSMTP] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_calls: list[tuple[str, str]] = []
        self.sent_messages: list[tuple[object, object]] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def send_message(self, message: object, to_addrs: object = None) -> dict[str, str]:
        self.sent_messages.append((message, to_addrs))
        return {}


def _event(
    *,
    recipients: list[str] | None = None,
    recipient_email: str | None = "recipient@example.com",
) -> NotificationEvent:
    metadata: dict[str, object] = {"event_type": "alerts.created"}
    if recipients is not None:
        metadata["resolved_recipients"] = recipients
    return NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient_email,
        subject="Subject",
        message="Message",
        source_type="ALERT_CREATED",
        source_id="1",
        metadata=metadata,
    )


def test_email_adapter_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "false")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    result = asyncio.run(EmailNotificationAdapter().send(_event()))

    assert result.status == NotificationStatus.SKIPPED
    assert result.skipped is True
    assert result.error == "email_disabled"
    assert FakeSMTP.instances == []


def test_email_adapter_fails_when_config_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    result = asyncio.run(EmailNotificationAdapter().send(_event()))

    assert result.status == NotificationStatus.FAILED
    assert result.failed is True
    assert result.error == "smtp_host_missing"
    assert FakeSMTP.instances == []


@pytest.mark.asyncio
async def test_email_adapter_monta_mensagem_com_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "AgroSaaS")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    event = _event(recipients=["user@example.com"])
    result = await EmailNotificationAdapter().send(event)

    assert result.status == NotificationStatus.DELIVERED
    assert result.provider_message_id is not None
    smtp = FakeSMTP.instances[0]
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 587
    assert smtp.started_tls is False
    message, recipients = smtp.sent_messages[0]
    assert recipients == ["user@example.com"]
    assert "alerts.created" in str(message)
    assert "Tenant:" in message.get_content()
    assert "resolved_recipients" in message.get_content()


@pytest.mark.asyncio
async def test_email_adapter_usa_tls_e_autenticacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    result = await EmailNotificationAdapter().send(_event(recipients=["user@example.com"]))

    assert result.status == NotificationStatus.DELIVERED
    smtp = FakeSMTP.instances[0]
    assert smtp.started_tls is True
    assert smtp.login_calls == [("user", "pass")]


@pytest.mark.asyncio
async def test_email_adapter_skips_without_recipients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)
    FakeSMTP.instances.clear()

    result = await EmailNotificationAdapter().send(
        _event(recipients=[], recipient_email=None)
    )

    assert result.status == NotificationStatus.SKIPPED
    assert result.error == "no_recipients"
    assert FakeSMTP.instances == []
