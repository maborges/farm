import pytest

from scripts.demo_lab_guard import (
    DemoLabTargetError,
    validate_demo_lab_identity,
    validate_demo_lab_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://borgus:pw@192.168.0.2:5432/farms",
        "postgresql+asyncpg://deepfarms_demo_runtime:pw@179.197.86.1:5432/deepfarms_demo_lab",
        "postgresql+asyncpg://deepfarms_demo_runtime:pw@127.0.0.1:5432/deepfarms_demo_lab",
        "postgresql+asyncpg://other:pw@192.168.0.2:5432/deepfarms_demo_lab",
        "postgresql+asyncpg://deepfarms_demo_runtime:pw@192.168.0.2:5432/farms",
        "sqlite+aiosqlite:///deepfarms_demo_lab",
        "postgresql+asyncpg://borgus:pw@192.168.0.2:5432/deepfarms_demo_lab?host=localhost",
    ],
)
def test_refuses_untrusted_target(url):
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_url(url)


def test_accepts_explicit_development_target():
    validate_demo_lab_url(
        "postgresql+asyncpg://borgus:pw@192.168.0.2:5432/deepfarms_demo_lab"
    )


def test_database_identity_refuses_superuser_or_bypass_rls():
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_identity(
            "deepfarms_demo_lab", "deepfarms_demo_runtime", True, False, True
        )
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_identity(
            "deepfarms_demo_lab", "deepfarms_demo_runtime", False, True, True
        )


def test_database_identity_refuses_wrong_role_or_database():
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_identity("other", "deepfarms_demo_runtime", False, False, True)
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_identity("deepfarms_demo_lab", "other", False, False, True)


def test_database_identity_accepts_restricted_role():
    validate_demo_lab_identity("deepfarms_demo_lab", "deepfarms_demo_runtime", False, False, True)


def test_database_identity_requires_schema_access():
    with pytest.raises(DemoLabTargetError):
        validate_demo_lab_identity(
            "deepfarms_demo_lab", "deepfarms_demo_runtime", False, False, False
        )
