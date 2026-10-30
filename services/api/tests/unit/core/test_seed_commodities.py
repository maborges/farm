from __future__ import annotations

import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from scripts.initial_load import seed_commodities


@pytest.mark.asyncio
async def test_seed_serializes_classification_extra_as_json_object(monkeypatch):
    import asyncpg

    class FakeConnection:
        def __init__(self):
            self.current_code = None
            self.classifications = []
            self.commit_count = 0
            self.closed = False

        @asynccontextmanager
        async def transaction(self):
            yield
            self.commit_count += 1

        async def fetchval(self, query, *args):
            if "FROM cadastros_commodities WHERE codigo" in query:
                self.current_code = args[0]
                return uuid4()
            return None

        async def execute(self, _query, *args):
            self.classifications.append((self.current_code, args))

        async def close(self):
            self.closed = True

    connection = FakeConnection()

    async def fake_connect(_url):
        return connection

    monkeypatch.setattr(asyncpg, "connect", fake_connect)

    await seed_commodities.run_seed()

    extra_values = [
        args[9]
        for code, args in connection.classifications
        if code == "BOI_GORDO" and args[1] == "PREMIUM"
    ]
    assert len(extra_values) == 1
    assert json.loads(extra_values[0]) == {
        "descricao_extra": "Gordura de cobertura uniforme"
    }
    assert all(
        isinstance(json.loads(args[9]), dict)
        for _code, args in connection.classifications
        if args[9] is not None
    )
    assert connection.commit_count == 1
    assert connection.closed is True
