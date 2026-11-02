"""Start the main development API with RLS sessions on three routes only."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from dotenv import dotenv_values

API_DIR = Path(__file__).resolve().parent
ENV_FILE = Path(os.environ.get(
    "DEEPFARMS_RLS_CANARY_ENV_FILE",
    API_DIR / ".env.rls-canary.local",
)).expanduser()


def _prepare_environment() -> None:
    if not ENV_FILE.is_file():
        raise SystemExit("Restricted route credential file is missing")
    if stat.S_IMODE(ENV_FILE.stat().st_mode) & 0o077:
        raise SystemExit("Restricted route credential file must have mode 0600")
    values = dotenv_values(ENV_FILE, interpolate=False)
    if not values.get("DEEPFARMS_CANARY_RUNTIME_PASSWORD") or not values.get(
        "DEEPFARMS_CANARY_AUTH_PASSWORD"
    ):
        raise SystemExit("Restricted route credentials are incomplete")

    # Do not change DATABASE_URL: it remains the legacy connection for routes
    # that are not in the exact RLS allowlist inside get_session().
    os.environ["DEEPFARMS_RLS_CANARY_ENV_FILE"] = str(ENV_FILE)
    os.environ["RLS_DEV_ROUTE_SESSIONS_ENABLED"] = "true"
    os.environ["RUN_EMBEDDED_JOBS"] = "false"


if __name__ == "__main__":
    _prepare_environment()
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8013,
        workers=1,
        reload=False,
        access_log=False,
        log_level="warning",
    )
