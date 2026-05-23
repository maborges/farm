import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.schemas import ProdutoCatalogoCreate, ProdutoCatalogoUpdate
from core.cadastros.service import CatalogoProdutoService
from core.cadastros.produtos.models import Produto
from core.cadastros.produtos.schemas import ProdutoCreate, ProdutoUpdate
from core.cadastros.produtos.service import ProdutoService


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_catalogo_produto_criar_ignora_estoque_minimo(mock_session):
    svc = CatalogoProdutoService(mock_session, uuid.uuid4())
    mock_session.execute.return_value = MagicMock()

    produto = await svc.criar(
        ProdutoCatalogoCreate(
            nome="Produto Legado",
            tipo="INSUMO",
            unidade_medida="KG",
            estoque_minimo=123.0,
            preco_medio=10.0,
            ativo=True,
        )
    )

    assert produto.estoque_minimo == 0.0 or produto.estoque_minimo is None
    created = mock_session.add.call_args[0][0]
    assert created.estoque_minimo == 0.0 or created.estoque_minimo is None


@pytest.mark.asyncio
async def test_catalogo_produto_atualizar_ignora_estoque_minimo(mock_session):
    svc = CatalogoProdutoService(mock_session, uuid.uuid4())
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=svc.tenant_id,
        nome="Produto Legado",
        tipo="INSUMO",
        unidade_medida="KG",
        estoque_minimo=25.0,
        preco_medio=10.0,
        ativo=True,
    )
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=produto)),
        MagicMock(scalar_one=MagicMock(return_value=produto)),
    ]

    atualizado = await svc.atualizar(
        produto.id,
        ProdutoCatalogoUpdate(
            nome="Produto Legado 2",
            estoque_minimo=999.0,
            preco_medio=11.0,
        ),
    )

    assert atualizado.nome == "Produto Legado 2"
    assert atualizado.preco_medio == 11.0
    assert atualizado.estoque_minimo == 25.0


@pytest.mark.asyncio
async def test_catalogo_produto_criar_ignora_preco_ultima_compra(mock_session):
    svc = CatalogoProdutoService(mock_session, uuid.uuid4())
    mock_session.execute.return_value = MagicMock()

    produto = await svc.criar(
        ProdutoCatalogoCreate(
            nome="Produto Legado 2",
            tipo="INSUMO",
            unidade_medida="KG",
            preco_medio=10.0,
            ativo=True,
        )
    )

    created = mock_session.add.call_args[0][0]
    assert getattr(created, "preco_ultima_compra", None) is None


@pytest.mark.asyncio
async def test_catalogo_produto_atualizar_ignora_preco_ultima_compra(mock_session):
    svc = CatalogoProdutoService(mock_session, uuid.uuid4())
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=svc.tenant_id,
        nome="Produto Atual",
        tipo="INSUMO",
        unidade_medida="KG",
        estoque_minimo=10.0,
        preco_medio=9.0,
        preco_ultima_compra=15.0,
        ativo=True,
    )
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=produto)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    atualizado = await svc.atualizar(
        produto.id,
        ProdutoCatalogoUpdate(
            nome="Produto Atualizado",
            preco_ultima_compra=30.0,
            preco_medio=12.0,
        ),
    )

    assert atualizado.nome == "Produto Atualizado"
    assert atualizado.preco_medio == 12.0
    assert atualizado.preco_ultima_compra == 15.0


@pytest.mark.asyncio
async def test_produto_service_criar_ignora_estoque_minimo(mock_session):
    svc = ProdutoService(mock_session, uuid.uuid4())
    mock_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=Produto()))

    produto = await svc.criar_produto(
        ProdutoCreate(
            nome="Produto Novo",
            tipo="INSUMO",
            unidade_medida="KG",
            estoque_minimo=321.0,
            preco_medio=15.0,
        )
    )

    created = mock_session.add.call_args[0][0]
    assert created.estoque_minimo == 0.0 or created.estoque_minimo is None


@pytest.mark.asyncio
async def test_produto_service_atualizar_ignora_estoque_minimo(mock_session):
    svc = ProdutoService(mock_session, uuid.uuid4())
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=svc.tenant_id,
        nome="Produto Atual",
        tipo="INSUMO",
        unidade_medida="KG",
        estoque_minimo=77.0,
        preco_medio=9.0,
        ativo=True,
    )
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=produto)),
        MagicMock(scalar_one=MagicMock(return_value=produto)),
    ]

    atualizado = await svc.atualizar_produto(
        produto.id,
        ProdutoUpdate(
            nome="Produto Atualizado",
            estoque_minimo=555.0,
            preco_medio=12.0,
        ),
    )

    assert atualizado.nome == "Produto Atualizado"
    assert atualizado.preco_medio == 12.0
    assert atualizado.estoque_minimo == 77.0


@pytest.mark.asyncio
async def test_produto_service_criar_ignora_preco_ultima_compra(mock_session):
    svc = ProdutoService(mock_session, uuid.uuid4())
    mock_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=Produto()))

    produto = await svc.criar_produto(
        ProdutoCreate(
            nome="Produto Novo 2",
            tipo="INSUMO",
            unidade_medida="KG",
            preco_medio=15.0,
        )
    )

    created = mock_session.add.call_args[0][0]
    assert getattr(created, "preco_ultima_compra", None) is None


@pytest.mark.asyncio
async def test_produto_service_atualizar_ignora_preco_ultima_compra(mock_session):
    svc = ProdutoService(mock_session, uuid.uuid4())
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=svc.tenant_id,
        nome="Produto Atual 2",
        tipo="INSUMO",
        unidade_medida="KG",
        estoque_minimo=77.0,
        preco_medio=9.0,
        preco_ultima_compra=21.0,
        ativo=True,
    )
    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=produto)),
        MagicMock(scalar_one=MagicMock(return_value=produto)),
    ]

    atualizado = await svc.atualizar_produto(
        produto.id,
        ProdutoUpdate(
            nome="Produto Atualizado 2",
            preco_ultima_compra=33.0,
            preco_medio=12.0,
        ),
    )

    assert atualizado.nome == "Produto Atualizado 2"
    assert atualizado.preco_medio == 12.0
    assert atualizado.preco_ultima_compra == 21.0
