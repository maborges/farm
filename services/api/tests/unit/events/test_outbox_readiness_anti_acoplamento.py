from __future__ import annotations

from pathlib import Path


def _read(*parts: str) -> str:
    project_root = Path(__file__).resolve().parents[5]
    return (project_root.joinpath(*parts)).read_text(encoding="utf-8")


def test_domain_services_do_not_import_notification_dispatcher_directly() -> None:
    files = (
        _read("services/api/campo/router.py"),
        _read("services/api/pecuaria/routers/manejos.py"),
        _read("services/api/pecuaria/services/manejo_sync_service.py"),
    )

    for source in files:
        assert "NotificationDispatcher" not in source


def test_notifications_do_not_import_alert_lifecycle_service() -> None:
    files = (
        _read("services/api/notifications/base.py"),
        _read("services/api/notifications/dispatcher.py"),
        _read("services/api/notifications/adapters.py"),
        _read("services/api/notifications/subscribers.py"),
    )

    for source in files:
        assert "AlertLifecycleService" not in source


def test_alert_engine_does_not_import_notification_dispatcher_directly() -> None:
    files = (
        _read("services/api/alert_engine/dispatcher.py"),
        _read("services/api/alert_engine/generators/base.py"),
        _read("services/api/alert_engine/generators/runner.py"),
        _read("services/api/events/subscribers.py"),
    )

    for source in files:
        assert "NotificationDispatcher" not in source


def test_event_publisher_remains_common_integration_point() -> None:
    helpers_source = _read("services/api/events/helpers.py")
    publisher_source = _read("services/api/events/publisher.py")

    assert "publish_domain_event(" in helpers_source
    assert "EventPublisher(" in publisher_source
    assert "AlertDispatcherService" not in helpers_source
    assert "NotificationDispatcher" not in helpers_source
