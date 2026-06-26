from __future__ import annotations

import uuid

import pytest

from notifications import (
    EmailNotificationAdapter,
    LogNotificationAdapter,
    NoopNotificationAdapter,
    NotificationAdapterRegistry,
    NotificationChannel,
    NotificationDeduplicationStore,
    NotificationDispatcher,
    NotificationEvent,
    NotificationPolicy,
    NotificationPolicyRegistry,
    NotificationPolicyResult,
    NotificationPolicyService,
    NotificationPreferences,
    NotificationSilenceWindow,
    NotificationStatus,
)


class EmailOnlyPolicy(NotificationPolicy):
    event_type = "notifications.email.only"

    def evaluate(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPolicyResult:
        return NotificationPolicyResult(
            allowed=True,
            tenant_id=event.tenant_id,
            event_type="notifications.email.only",
            priority="NORMAL",
            channels=["EMAIL"],
            recipients=["recipient@example.com"],
            dedupe_key=None,
            silence_window_applied=False,
        )


class LogEmailNoopPolicy(NotificationPolicy):
    event_type = "notifications.log.email.noop"

    def evaluate(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPolicyResult:
        return NotificationPolicyResult(
            allowed=True,
            tenant_id=event.tenant_id,
            event_type="notifications.log.email.noop",
            priority="NORMAL",
            channels=["LOG", "EMAIL", "NOOP"],
            recipients=["recipient@example.com"],
            dedupe_key=None,
            silence_window_applied=False,
        )


class LogOnlyPolicy(NotificationPolicy):
    event_type = "notifications.log.only"

    def evaluate(
        self,
        event: NotificationEvent,
        preferences: NotificationPreferences | None = None,
    ) -> NotificationPolicyResult:
        return NotificationPolicyResult(
            allowed=True,
            tenant_id=event.tenant_id,
            event_type="notifications.log.only",
            priority="NORMAL",
            channels=["LOG"],
            recipients=[],
            dedupe_key=None,
            silence_window_applied=False,
        )


class FakeSMTP:
    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        return None

    def send_message(self, message: object, to_addrs: object = None) -> dict[str, str]:
        return {}


class FailingSMTP(FakeSMTP):
    def send_message(self, message: object, to_addrs: object = None) -> dict[str, str]:
        raise RuntimeError("smtp failure")


def _event(event_type: str) -> NotificationEvent:
    return NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.LOG,
        subject="Subject",
        message="Message",
        source_type="ALERT_CREATED",
        source_id="1",
        metadata={"event_type": event_type},
    )


@pytest.mark.asyncio
async def test_dispatcher_calls_email_adapter_when_policy_resolves_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)

    email_calls: list[NotificationEvent] = []
    original_send = EmailNotificationAdapter.send

    async def tracked_send(
        self: EmailNotificationAdapter,
        event: NotificationEvent,
    ) -> object:
        email_calls.append(event)
        return await original_send(self, event)

    monkeypatch.setattr(EmailNotificationAdapter, "send", tracked_send)

    registry = NotificationAdapterRegistry()
    registry.register(LogNotificationAdapter)
    registry.register(NoopNotificationAdapter)
    registry.register(EmailNotificationAdapter)
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(EmailOnlyPolicy())
    dispatcher = NotificationDispatcher(
        registry=registry,
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(),
        ),
    )

    result = await dispatcher.dispatch(_event("notifications.email.only"))

    assert result.status == NotificationStatus.DELIVERED
    assert email_calls
    assert result.channel == NotificationChannel.EMAIL
    assert result.metadata["policy"]["channels"] == ["EMAIL"]


@pytest.mark.asyncio
async def test_dispatcher_does_not_call_email_when_policy_is_log_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)

    email_calls: list[NotificationEvent] = []
    original_send = EmailNotificationAdapter.send

    async def tracked_send(
        self: EmailNotificationAdapter,
        event: NotificationEvent,
    ) -> object:
        email_calls.append(event)
        return await original_send(self, event)

    monkeypatch.setattr(EmailNotificationAdapter, "send", tracked_send)

    registry = NotificationAdapterRegistry()
    registry.register(LogNotificationAdapter)
    registry.register(NoopNotificationAdapter)
    registry.register(EmailNotificationAdapter)
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(LogOnlyPolicy())
    dispatcher = NotificationDispatcher(
        registry=registry,
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(),
        ),
    )

    result = await dispatcher.dispatch(_event("notifications.log.only"))

    assert result.status == NotificationStatus.DELIVERED
    assert email_calls == []
    assert result.channel == NotificationChannel.LOG


@pytest.mark.asyncio
async def test_dispatcher_continues_when_email_adapter_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FailingSMTP)

    registry = NotificationAdapterRegistry()
    registry.register(LogNotificationAdapter)
    registry.register(NoopNotificationAdapter)
    registry.register(EmailNotificationAdapter)
    policy_registry = NotificationPolicyRegistry()
    policy_registry.register(LogEmailNoopPolicy())
    dispatcher = NotificationDispatcher(
        registry=registry,
        policy_service=NotificationPolicyService(
            registry=policy_registry,
            deduplication_store=NotificationDeduplicationStore(),
            silence_window=NotificationSilenceWindow(),
        ),
    )

    result = await dispatcher.dispatch(_event("notifications.log.email.noop"))

    assert result.status == NotificationStatus.DELIVERED
    assert result.metadata["deliveries"][0]["channel"] == "LOG"
    assert result.metadata["deliveries"][1]["channel"] == "EMAIL"
    assert result.metadata["deliveries"][1]["failed"] is True
    assert result.metadata["deliveries"][2]["channel"] == "NOOP"


@pytest.mark.asyncio
async def test_email_event_without_recipients_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFICATIONS_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("notifications.email_adapter.smtplib.SMTP", FakeSMTP)

    event = NotificationEvent(
        tenant_id=uuid.uuid4(),
        channel=NotificationChannel.EMAIL,
        subject="Subject",
        message="Message",
        source_type="ALERT_CREATED",
        source_id="1",
        metadata={"event_type": "notifications.email.only"},
    )

    result = await EmailNotificationAdapter().send(event)

    assert result.status == NotificationStatus.SKIPPED
    assert result.error == "no_recipients"
