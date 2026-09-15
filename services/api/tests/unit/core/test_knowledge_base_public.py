"""Contratos públicos da Base de Conhecimento."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from core.routers.knowledge_base import get_article_by_slug, list_kb_public


@pytest.mark.asyncio
async def test_public_article_query_excludes_private_articles() -> None:
    """A busca de um artigo não deve expor conteúdo privado."""
    article = SimpleNamespace(visualizacoes=3)
    result = Mock()
    result.scalar_one_or_none.return_value = article
    session = AsyncMock()
    session.execute.return_value = result

    await get_article_by_slug("guia-publico", session)

    statement = str(session.execute.await_args.args[0])
    assert "conhecimento_artigos.is_publico IS true" in statement
    assert article.visualizacoes == 4
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_category_listing_uses_public_article_criteria() -> None:
    """A lista de categorias carrega somente artigos que podem ser publicados."""
    scalars = Mock()
    scalars.all.return_value = []
    result = Mock()
    result.scalars.return_value = scalars
    session = AsyncMock()
    session.execute.return_value = result

    assert await list_kb_public(session) == []
    options = session.execute.await_args.args[0]._with_options
    assert any(option.__class__.__name__ == "LoaderCriteriaOption" for option in options)
