"""Start the restricted development RLS canary on loopback only."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url


API_DIR = Path(__file__).resolve().parent
ENV_FILE = Path(os.environ.get(
    "DEEPFARMS_RLS_CANARY_ENV_FILE",
    API_DIR / ".env.rls-canary.local",
)).expanduser()


def _load_and_validate() -> None:
    if not ENV_FILE.is_file():
        raise SystemExit("Canary env file missing; create the protected local file first.")
    mode = stat.S_IMODE(ENV_FILE.stat().st_mode)
    if mode & 0o077:
        raise SystemExit("Canary env file must be private (chmod 600).")

    values = dotenv_values(ENV_FILE, interpolate=False)
    runtime_password = values.get("DEEPFARMS_CANARY_RUNTIME_PASSWORD")
    auth_password = values.get("DEEPFARMS_CANARY_AUTH_PASSWORD")
    if not runtime_password or not auth_password:
        raise SystemExit(
            "Canary env file must define both runtime and auth passwords; values were not logged."
        )

    expected = ("192.168.0.2", 5432, "farms")
    runtime_url = URL.create(
        "postgresql+asyncpg", username="deepfarms_runtime",
        password=runtime_password, host=expected[0], port=expected[1], database=expected[2],
    )
    auth_url = URL.create(
        "postgresql+asyncpg", username="deepfarms_auth",
        password=auth_password, host=expected[0], port=expected[1], database=expected[2],
    )
    for url, username in ((runtime_url, "deepfarms_runtime"), (auth_url, "deepfarms_auth")):
        parsed = make_url(url.render_as_string(hide_password=False))
        if (parsed.host, parsed.port, parsed.database, parsed.username) != (*expected, username):
            raise SystemExit("Canary database identity validation failed; no URL was logged.")

    os.environ["DATABASE_URL"] = runtime_url.render_as_string(hide_password=False)
    os.environ["AUTHENTICATION_DATABASE_URL"] = auth_url.render_as_string(hide_password=False)
    os.environ["AUTHENTICATION_DATABASE_ROLE"] = "deepfarms_auth"
    os.environ["REQUIRE_RESTRICTED_RUNTIME_ROLE"] = "true"
    os.environ["RUN_EMBEDDED_JOBS"] = "false"
    os.environ["ENABLE_LEGACY_AGRO_DB"] = "false"
    os.environ["DB_POOL_SIZE"] = "2"
    os.environ["DB_MAX_OVERFLOW"] = "0"


if __name__ == "__main__":
    _load_and_validate()
    import uvicorn

    uvicorn.run(
        "rls_canary:app",
        host="127.0.0.1",
        port=8012,
        workers=1,
        reload=False,
        access_log=False,
        log_level="warning",
    )
