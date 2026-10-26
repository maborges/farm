from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[3]


def test_postgresql_offline_baseline_qualifies_version_table() -> None:
    """Generate SQL offline using synthetic credentials; no DB connection occurs."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "ENVIRONMENT": "development",
        "APP_ENV": "development",
    }
    env["DATABASE_URL"] = (
        "postgresql+asyncpg://offline_user:synthetic-only@127.0.0.1:55432/"
        "offline_contract_test"
    )
    result = subprocess.run(  # noqa: S603 - fixed argv; synthetic target; offline only.
        [  # noqa: S603 - fixed executable/argv; no shell; offline target only.
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "upgrade",
            "baseline_deepfarms_v1",
            "--sql",
        ],
        cwd=API_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    sql = result.stdout
    schema_ddl = sql.index("CREATE SCHEMA IF NOT EXISTS farms;")
    version_table = sql.index("CREATE TABLE farms.alembic_version (")
    revision_insert = sql.index(
        "INSERT INTO farms.alembic_version (version_num)"
    )

    assert schema_ddl < version_table < revision_insert
    assert not re.search(r"CREATE TABLE\s+alembic_version\s*\(", sql)
    assert "SET search_path TO farms;" in sql
