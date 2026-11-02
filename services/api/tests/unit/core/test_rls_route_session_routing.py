from contextlib import asynccontextmanager

import pytest
from starlette.requests import Request

from core import dependencies


def _request(method: str, path: str) -> Request:
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


@pytest.mark.parametrize("method,path", sorted(dependencies.RLS_DEV_RESTRICTED_ROUTE_PAIRS))
def test_only_exact_approved_route_pairs_select_restricted_session(monkeypatch, method, path):
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    assert dependencies.uses_restricted_route_session(_request(method, path)) is True


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/auth/login"),
        ("POST", "/api/v1/notificacoes"),
        ("PATCH", "/api/v1/notificacoes/"),
        ("GET", "/api/v1/notificacoes/nao-lidas-count"),
        ("GET", "/docs"),
    ],
)
def test_other_methods_and_paths_stay_on_legacy_engine(monkeypatch, method, path):
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    assert dependencies.uses_restricted_route_session(_request(method, path)) is False


def test_disabled_flag_does_not_select_restricted_session(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", False)
    assert dependencies.uses_restricted_route_session(
        _request("POST", "/api/v1/auth/login")
    ) is False


@pytest.mark.asyncio
async def test_get_session_uses_restricted_factory_only_for_allowlisted_request(monkeypatch):
    observed = []

    class Session:
        def __init__(self):
            self.info = {}

    def factory(name):
        @asynccontextmanager
        async def _context():
            observed.append(name)
            yield Session()
        return _context

    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    monkeypatch.setattr(dependencies, "async_session_maker", factory("legacy"))
    monkeypatch.setattr(dependencies, "rls_dev_async_session_maker", factory("restricted"))

    restricted_generator = dependencies.get_session(
        _request("GET", "/api/v1/notificacoes/")
    )
    session = await anext(restricted_generator)
    assert isinstance(session, Session)
    assert session.info["rls_dev_restricted_route"] is True
    assert observed == ["restricted"]
    await restricted_generator.aclose()

    legacy_generator = dependencies.get_session(_request("GET", "/api/v1/auth/me"))
    session = await anext(legacy_generator)
    assert isinstance(session, Session)
    assert "rls_dev_restricted_route" not in session.info
    assert observed == ["restricted", "legacy"]
    await legacy_generator.aclose()


@pytest.mark.asyncio
async def test_restricted_route_fails_closed_without_factory(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    monkeypatch.setattr(dependencies, "rls_dev_async_session_maker", None)
    legacy_called = False

    def legacy_factory():
        nonlocal legacy_called
        legacy_called = True
        raise AssertionError("legacy fallback must not run")

    monkeypatch.setattr(dependencies, "async_session_maker", legacy_factory)
    with pytest.raises(RuntimeError, match="Restricted route session"):
        await anext(dependencies.get_session(_request("POST", "/api/v1/auth/login")))
    assert legacy_called is False


def test_all_routes_flag_selects_restricted_session_for_any_route(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "rls_dev_route_sessions_enabled", True)
    monkeypatch.setattr(dependencies.settings, "rls_dev_all_routes_enabled", True)
    assert dependencies.uses_restricted_route_session(_request("GET", "/api/v1/safras")) is True
    assert dependencies.uses_restricted_route_session(_request("POST", "/api/v1/campo/requisicoes")) is True

