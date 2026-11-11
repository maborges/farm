import pytest
from fastapi import HTTPException
from starlette.requests import Request

from core.dependencies import require_role


@pytest.mark.asyncio
async def test_require_role_accepts_allowed_role_and_rejects_other_role():
    request = Request({"type": "http", "headers": [(b"x-fazenda-id", b"farm-1")]})
    check = require_role(["agronomo", "admin"])
    allowed = {"role": "agronomo", "fazendas_auth": [{"id": "farm-1", "role": "agronomo"}]}
    assert await check(request, allowed) == allowed
    with pytest.raises(HTTPException) as exc:
        await check(request, {"role": "operador", "fazendas_auth": [{"id": "farm-1", "role": "operador"}]})
    assert exc.value.status_code == 403
