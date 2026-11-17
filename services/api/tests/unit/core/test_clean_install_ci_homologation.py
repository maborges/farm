"""Fail-closed target checks for the disposable clean-install CI runner."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(API_ROOT))

from scripts.homologar_clean_install_ci import _validated_ci_database_url  # noqa: E402

CI_ENV = {
    "GITHUB_ACTIONS": "true",
    "CI_POSTGRESQL": "true",
    "DATABASE_URL": "postgresql+asyncpg://deepfarms_test:synthetic@localhost:5432/farms_test",
    "TEST_DATABASE_URL": "postgresql+asyncpg://deepfarms_test:synthetic@localhost:5432/farms_test",
}


def test_accepts_only_the_workflow_disposable_postgresql_target() -> None:
    assert _validated_ci_database_url(CI_ENV) == CI_ENV["DATABASE_URL"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("GITHUB_ACTIONS", "false"),
        ("CI_POSTGRESQL", "false"),
        (
            "DATABASE_URL",
            "postgresql+asyncpg://deepfarms_test:synthetic@localhost:5432/farms",
        ),
        (
            "DATABASE_URL",
            "postgresql+asyncpg://deepfarms_test:synthetic@192.168.0.3:5432/farms_test",
        ),
        (
            "DATABASE_URL",
            "postgresql+asyncpg://deepfarms_test:synthetic@localhost:5433/farms_test",
        ),
        (
            "DATABASE_URL",
            "postgresql+asyncpg://deepfarms_auth:synthetic@localhost:5432/farms_test",
        ),
        (
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://deepfarms_test:other@localhost:5432/farms_test",
        ),
    ],
)
def test_rejects_any_non_ci_or_non_disposable_target(key: str, value: str) -> None:
    environ = CI_ENV | {key: value}
    with pytest.raises(RuntimeError):
        _validated_ci_database_url(environ)


def test_rejection_messages_do_not_include_database_credentials() -> None:
    environ = CI_ENV | {"DATABASE_URL": "not-a-url-with-secret"}
    with pytest.raises(RuntimeError) as error:
        _validated_ci_database_url(environ)
    assert "synthetic" not in str(error.value)
