from __future__ import annotations

from pathlib import Path


def _read(*parts: str) -> str:
    project_root = Path(__file__).resolve().parents[5]
    return (project_root.joinpath(*parts)).read_text(encoding="utf-8")


def test_recommendations_do_not_import_alert_engine_or_notifications() -> None:
    files = (
        _read("services/api/recommendations/enums.py"),
        _read("services/api/recommendations/schemas.py"),
        _read("services/api/recommendations/models.py"),
        _read("services/api/recommendations/provider.py"),
        _read("services/api/recommendations/registry.py"),
        _read("services/api/recommendations/engine.py"),
        _read("services/api/recommendations/runner.py"),
        _read("services/api/recommendations/scheduler.py"),
        _read("services/api/recommendations/lifecycle_service.py"),
        _read("services/api/recommendations/metrics_service.py"),
        _read("services/api/recommendations/query_service.py"),
        _read("services/api/recommendations/router.py"),
        _read("services/api/recommendations/providers/__init__.py"),
        _read("services/api/recommendations/providers/clima_provider.py"),
        _read("services/api/recommendations/providers/agricultura_provider.py"),
        _read("services/api/recommendations/providers/financeiro_provider.py"),
        _read("services/api/recommendations/providers/pecuaria_provider.py"),
        _read("services/api/recommendations/providers/estoque_provider.py"),
        _read("services/api/recommendations/providers/frota_provider.py"),
        _read("services/api/recommendations/providers/esg_provider.py"),
        _read("services/api/recommendations/providers/wizard_provider.py"),
        _read("services/api/recommendations/providers/campo_provider.py"),
    )

    for source in files:
        assert "alert_engine" not in source
        assert "notifications" not in source
        assert "NotificationDispatcher" not in source
        assert "CampoPWA" not in source
        assert "frontend" not in source.lower()


def test_recommendations_do_not_import_climate_recommendation_service() -> None:
    files = (
        _read("services/api/recommendations/engine.py"),
        _read("services/api/recommendations/lifecycle_service.py"),
        _read("services/api/recommendations/provider.py"),
        _read("services/api/recommendations/runner.py"),
        _read("services/api/recommendations/scheduler.py"),
        _read("services/api/recommendations/providers/clima_provider.py"),
        _read("services/api/recommendations/providers/agricultura_provider.py"),
        _read("services/api/recommendations/providers/financeiro_provider.py"),
        _read("services/api/recommendations/providers/pecuaria_provider.py"),
        _read("services/api/recommendations/providers/estoque_provider.py"),
        _read("services/api/recommendations/providers/frota_provider.py"),
        _read("services/api/recommendations/providers/esg_provider.py"),
        _read("services/api/recommendations/providers/wizard_provider.py"),
        _read("services/api/recommendations/providers/campo_provider.py"),
        _read("services/api/recommendations/query_service.py"),
        _read("services/api/recommendations/router.py"),
    )

    for source in files:
        assert "ClimaRecommendationService" not in source
