from __future__ import annotations

from pathlib import Path


def test_domain_services_do_not_import_alert_engine_internals() -> None:
    project_root = Path(__file__).resolve().parents[5]
    files = (
        project_root / "services/api/campo/router.py",
        project_root / "services/api/pecuaria/routers/manejos.py",
        project_root / "services/api/pecuaria/services/manejo_sync_service.py",
    )
    forbidden = (
        "AlertDispatcherService",
        "dispatch_alert_event",
        "AlertGeneratorRegistry",
        "AlertGeneratorRunner",
        "CampoAlertGenerator",
        "PecuariaAlertGenerator",
    )
    allowed = ("DomainEvent", "publish_domain_event", "publish_domain_event_safe")

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert any(token in source for token in allowed)
        assert all(token not in source for token in forbidden)
