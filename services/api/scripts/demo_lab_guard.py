"""Fail-closed identity checks for the demonstration database in development.

These checks do not prove that schema policies or service-side effects are safe.
"""

from sqlalchemy.engine import make_url


class DemoLabTargetError(ValueError):
    """The configured database is not the dedicated demonstration laboratory."""


def validate_demo_lab_url(database_url: str) -> None:
    """Reject targets other than the dedicated demonstration database and role."""
    try:
        url = make_url(database_url)
    except (TypeError, ValueError) as exc:
        raise DemoLabTargetError("Invalid laboratory database URL") from exc
    if (
        url.drivername != "postgresql+asyncpg"
        or url.host != "192.168.0.2"
        or url.port not in (None, 5432)
        or url.database != "deepfarms_demo_lab"
        or url.username != "borgus"
        or url.query
    ):
        raise DemoLabTargetError("Refusing non-dedicated demonstration database")


def validate_demo_lab_identity(
    database: str, user: str, superuser: bool, bypass_rls: bool,
    demo_schema_usage: bool,
) -> None:
    """Require the restricted laboratory role with access to its application schema."""
    if (
        database != "deepfarms_demo_lab"
        or user != "deepfarms_demo_runtime"
        or superuser
        or bypass_rls
        or not demo_schema_usage
    ):
        raise DemoLabTargetError("Refusing database identity or RLS-bypassing role")
