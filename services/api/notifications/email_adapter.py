from __future__ import annotations

import json
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from time import perf_counter

from loguru import logger

from .base import (
    NotificationAdapter,
    NotificationChannel,
    NotificationDeliveryResult,
    NotificationEvent,
    NotificationStatus,
)
from .notification_config import NotificationConfig, load_notification_config
from .registry import register_notification_adapter


@register_notification_adapter
class EmailNotificationAdapter(NotificationAdapter):
    """SMTP adapter for operational email notifications."""

    adapter_name = "email"
    supported_channels = (NotificationChannel.EMAIL,)

    async def send(self, event: NotificationEvent) -> NotificationDeliveryResult:
        """Send a notification email using SMTP when enabled and configured."""

        start = perf_counter()
        config = load_notification_config()
        if not config.email_enabled:
            return self._skipped(event, "email_disabled", config, start)
        recipients = self._resolve_recipients(event)
        if not recipients:
            return self._skipped(event, "no_recipients", config, start)
        validation_error = self._validate_config(config)
        if validation_error is not None:
            return self._failed(event, validation_error, config, start)
        try:
            message = self._build_message(event, recipients, config)
            self._send_message(config, recipients, message)
            return self._delivered(event, recipients, message, config, start)
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.bind(
                component="notification_email_adapter",
                notification_id=str(event.notification_id),
                tenant_id=str(event.tenant_id),
                event_type=event.metadata.get("event_type"),
                error_type=exc.__class__.__name__,
            ).exception("notification_email_delivery_failed")
            return self._failed(event, exc, config, start)

    def _send_message(
        self,
        config: NotificationConfig,
        recipients: list[str],
        message: EmailMessage,
    ) -> None:
        with smtplib.SMTP(
            host=config.smtp_host,
            port=config.smtp_port,
            timeout=config.smtp_timeout_seconds,
        ) as client:
            if config.smtp_use_tls:
                client.starttls()
            if config.has_smtp_auth:
                client.login(config.smtp_username, config.smtp_password)
            client.send_message(message, to_addrs=recipients)

    def _build_message(
        self,
        event: NotificationEvent,
        recipients: list[str],
        config: NotificationConfig,
    ) -> EmailMessage:
        message = EmailMessage()
        event_type = str(event.metadata.get("event_type", event.source_type))
        message["Subject"] = f"[DeepFarms] {event_type}"
        message["From"] = f"{config.smtp_from_name} <{config.smtp_from_email}>"
        message["To"] = ", ".join(recipients)
        message["Message-ID"] = make_msgid(domain=config.smtp_from_email.split("@")[-1])
        message["Date"] = format_datetime(datetime.now(timezone.utc))  # noqa: UP017
        message.set_content(self._build_body(event))
        return message

    def _build_body(self, event: NotificationEvent) -> str:
        payload = json.dumps(
            event.metadata,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        event_type = str(event.metadata.get("event_type", event.source_type))
        return (
            "DeepFarms Notification\n\n"
            f"Tipo: {event_type}\n"
            f"Prioridade: {event.priority.value}\n"
            f"Tenant: {event.tenant_id}\n"
            f"Ocorrido em: {event.created_at.isoformat()}\n\n"
            "Payload:\n"
            f"{payload}\n\n"
            "Observação:\n"
            "Esta é uma notificação operacional gerada automaticamente.\n"
        )

    def _resolve_recipients(self, event: NotificationEvent) -> list[str]:
        metadata_recipients = event.metadata.get("resolved_recipients")
        resolved: list[str] = []
        if isinstance(metadata_recipients, list):
            for value in metadata_recipients:
                recipient = str(value).strip()
                if "@" in recipient:
                    resolved.append(recipient)
        if resolved:
            return resolved
        if event.recipient_email and "@" in event.recipient_email:
            return [event.recipient_email.strip()]
        return []

    @staticmethod
    def _validate_config(config: NotificationConfig) -> str | None:
        if not config.smtp_host:
            return "smtp_host_missing"
        if config.smtp_port <= 0:
            return "smtp_port_invalid"
        if not config.smtp_from_email:
            return "smtp_from_email_missing"
        return None

    def _skipped(
        self,
        event: NotificationEvent,
        reason: str,
        config: NotificationConfig,
        start: float,
    ) -> NotificationDeliveryResult:
        logger.bind(
            component="notification_email_adapter",
            notification_id=str(event.notification_id),
            tenant_id=str(event.tenant_id),
            event_type=event.metadata.get("event_type"),
            reason=reason,
            email_enabled=config.email_enabled,
        ).info("notification_email_skipped")
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SKIPPED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            skipped=True,
            error=reason,
            duration_ms=int((perf_counter() - start) * 1000),
            metadata={
                "adapter_name": self.adapter_name,
                "reason": reason,
                "email_enabled": config.email_enabled,
            },
        )

    def _failed(
        self,
        event: NotificationEvent,
        error: Exception | str,
        config: NotificationConfig,
        start: float,
    ) -> NotificationDeliveryResult:
        error_message = error if isinstance(error, str) else f"{error.__class__.__name__}: {error}"
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.FAILED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            failed=True,
            error=error_message,
            duration_ms=int((perf_counter() - start) * 1000),
            metadata={
                "adapter_name": self.adapter_name,
                "email_enabled": config.email_enabled,
                "smtp_host": config.smtp_host,
                "smtp_port": config.smtp_port,
            },
        )

    def _delivered(
        self,
        event: NotificationEvent,
        recipients: list[str],
        message: EmailMessage,
        config: NotificationConfig,
        start: float,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            notification_id=event.notification_id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.DELIVERED,
            priority=event.priority,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            delivered=True,
            duration_ms=int((perf_counter() - start) * 1000),
            provider_message_id=str(message["Message-ID"]),
            metadata={
                "adapter_name": self.adapter_name,
                "email_enabled": config.email_enabled,
                "smtp_host": config.smtp_host,
                "smtp_port": config.smtp_port,
                "recipients": recipients,
                "subject": message["Subject"],
            },
        )
