from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on", "sim"}


@dataclass(slots=True, frozen=True)
class NotificationConfig:
    """Runtime configuration for notification adapters."""

    email_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_use_tls: bool
    smtp_timeout_seconds: int

    @property
    def has_smtp_auth(self) -> bool:
        return bool(self.smtp_username and self.smtp_password)

    @property
    def is_email_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_port and self.smtp_from_email)


def load_notification_config() -> NotificationConfig:
    """Load notification settings from process environment."""

    return NotificationConfig(
        email_enabled=_env_bool("NOTIFICATIONS_EMAIL_ENABLED", "false"),
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "0")),
        smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_from_email=os.getenv("SMTP_FROM_EMAIL", "").strip(),
        smtp_from_name=os.getenv("SMTP_FROM_NAME", "AgroSaaS").strip(),
        smtp_use_tls=_env_bool("SMTP_USE_TLS", "true"),
        smtp_timeout_seconds=int(os.getenv("SMTP_TIMEOUT_SECONDS", "10")),
    )
