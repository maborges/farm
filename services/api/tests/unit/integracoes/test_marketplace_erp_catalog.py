from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from integracoes.marketplace_router import listar_erps_disponiveis


@pytest.mark.asyncio
async def test_catalogo_erp_lista_apenas_providers_oficiais() -> None:
    db = AsyncMock()
    result = MagicMock()
    db.execute.return_value = result
    result.all.return_value = [
        SimpleNamespace(
            id=1,
            nome="Sankhya",
            slug="sankhya",
            descricao=None,
            logo_url=None,
        )
    ]

    response = await listar_erps_disponiveis(ativa=True, db=db)

    statement = db.execute.await_args.args[0]
    where_sql = str(statement.whereclause)
    assert "marketplace_integracoes.oficial IS true" in where_sql
    assert [provider["slug"] for provider in response] == ["sankhya"]
