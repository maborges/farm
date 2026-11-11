"""Start a loopback-only API whose connections are restricted to the demo lab."""

from __future__ import annotations

import os

import sqlalchemy.ext.asyncio as sa_async

from scripts.demo_lab_bootstrap import lab_url
from scripts.demo_lab_guard import validate_demo_lab_url


def main() -> None:
    """Run the API against deepfarms_demo_lab with the non-bypass runtime role."""
    database_url = lab_url()
    validate_demo_lab_url(database_url)
    os.environ.update(
        {
            "DATABASE_URL": database_url,
            "RUN_EMBEDDED_JOBS": "false",
            "RLS_DEV_ROUTE_SESSIONS_ENABLED": "false",
            "RLS_DEV_ALL_ROUTES_ENABLED": "false",
            "REQUIRE_RESTRICTED_RUNTIME_ROLE": "false",
            "AUTHENTICATION_DATABASE_URL": "",
            "RECOMMENDATION_DISPATCHER_DATABASE_URL": "",
        }
    )

    original_create_async_engine = sa_async.create_async_engine

    def create_lab_engine(target, *args, **kwargs):
        validate_demo_lab_url(str(target))
        connect_args = kwargs.setdefault("connect_args", {})
        server_settings = connect_args.setdefault("server_settings", {})
        server_settings["role"] = "deepfarms_demo_runtime"
        return original_create_async_engine(target, *args, **kwargs)

    sa_async.create_async_engine = create_lab_engine

    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8017, log_level="info")


if __name__ == "__main__":
    main()
