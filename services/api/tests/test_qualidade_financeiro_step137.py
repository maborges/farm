"""Step 137 — Testes: qualidade dos dados financeiros."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from financeiro.schemas.lancamento_schema import LancamentoCreate, CATEGORIAS_VALIDAS
from financeiro.models.lancamento import LancamentoFinanceiro


# ── schema: validações ────────────────────────────────────────────────────────

def test_valor_zero_rejeitado():
    with pytest.raises(Exception):
        LancamentoCreate(descricao="Teste", valor=0, data=date.today(), tipo="CUSTO", categoria="OPERACOES")


def test_valor_negativo_rejeitado():
    with pytest.raises(Exception):
        LancamentoCreate(descricao="Teste", valor=-10, data=date.today(), tipo="CUSTO", categoria="OPERACOES")


def test_categoria_invalida_rejeitada():
    with pytest.raises(Exception):
        LancamentoCreate(descricao="Teste", valor=100, data=date.today(), tipo="CUSTO", categoria="XPTO_INVALIDO")


def test_categoria_valida_normalizada():
    for cat in CATEGORIAS_VALIDAS:
        lc = LancamentoCreate(descricao="Teste", valor=100, data=date.today(), tipo="CUSTO", categoria=cat.lower())
        assert lc.categoria == cat


def test_tipo_invalido_rejeitado():
    with pytest.raises(Exception):
        LancamentoCreate(descricao="Teste", valor=100, data=date.today(), tipo="OUTRO", categoria="OPERACOES")


def test_tipo_receita_aceito():
    lc = LancamentoCreate(descricao="Venda", valor=500, data=date.today(), tipo="RECEITA", categoria="OPERACOES")
    assert lc.tipo == "RECEITA"


def test_origem_normalizada_para_upper():
    lc = LancamentoCreate(descricao="Mov", valor=50, data=date.today(), tipo="CUSTO", categoria="OPERACOES", origem="estoque")
    assert lc.origem == "ESTOQUE"


def test_origem_e_origem_id_opcionais():
    lc = LancamentoCreate(descricao="Mov", valor=50, data=date.today(), tipo="CUSTO", categoria="OPERACOES")
    assert lc.origem is None
    assert lc.origem_id is None


# ── model: campos origem ──────────────────────────────────────────────────────

def test_model_tem_campo_origem():
    assert hasattr(LancamentoFinanceiro, "origem")


def test_model_tem_campo_origem_id():
    assert hasattr(LancamentoFinanceiro, "origem_id")


# ── service: safra inválida ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safra_invalida_levanta_404():
    from financeiro.services.lancamento_service import LancamentoService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    svc = LancamentoService(session, uuid.uuid4())
    dados = LancamentoCreate(
        descricao="Custo", valor=100, data=date.today(), tipo="CUSTO", categoria="OPERACOES",
        safra_id=uuid.uuid4(),
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await svc.criar(dados)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_safra_outro_tenant_rejeitada():
    from financeiro.services.lancamento_service import LancamentoService

    safra = MagicMock()
    safra.tenant_id = uuid.uuid4()  # diferente do tenant do service

    session = AsyncMock()
    session.get = AsyncMock(return_value=safra)

    svc = LancamentoService(session, uuid.uuid4())
    dados = LancamentoCreate(
        descricao="Custo", valor=100, data=date.today(), tipo="CUSTO", categoria="OPERACOES",
        safra_id=uuid.uuid4(),
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await svc.criar(dados)
    assert exc_info.value.status_code == 404


# ── service: duplicata ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicata_levanta_409():
    from financeiro.services.lancamento_service import LancamentoService

    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    safra = MagicMock()
    safra.tenant_id = tenant_id

    existing_id = MagicMock()
    existing_id.__iter__ = MagicMock(return_value=iter([uuid.uuid4()]))

    session = AsyncMock()
    session.get = AsyncMock(return_value=safra)
    result_mock = MagicMock()
    result_mock.first = MagicMock(return_value=(uuid.uuid4(),))
    session.execute = AsyncMock(return_value=result_mock)

    svc = LancamentoService(session, tenant_id)
    dados = LancamentoCreate(
        descricao="Semente soja", valor=500, data=date(2024, 3, 1),
        tipo="CUSTO", categoria="INSUMOS", safra_id=safra_id,
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await svc.criar(dados)
    assert exc_info.value.status_code == 409


# ── service: criação válida ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_criar_lancamento_valido():
    from financeiro.services.lancamento_service import LancamentoService

    tenant_id = uuid.uuid4()

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.first = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()

    lancamento = LancamentoFinanceiro(
        id=uuid.uuid4(), tenant_id=tenant_id, safra_id=None,
        descricao="Teste", valor=100, data=date.today(),
        tipo="CUSTO", categoria="OPERACOES", origem=None, origem_id=None,
    )
    session.refresh = AsyncMock(side_effect=lambda obj: obj)

    svc = LancamentoService(session, tenant_id)
    dados = LancamentoCreate(descricao="Teste", valor=100, data=date.today(), tipo="CUSTO", categoria="OPERACOES")

    with patch.object(svc.session, "refresh", new_callable=AsyncMock) as mock_refresh:
        mock_refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4()) or obj
        result = await svc.criar(dados)

    session.add.assert_called_once()
    session.commit.assert_called_once()


# ── lancamento com origem (estoque) ───────────────────────────────────────────

def test_lancamento_create_aceita_origem_estoque():
    oid = uuid.uuid4()
    lc = LancamentoCreate(
        descricao="Saída de insumo",
        valor=200,
        data=date.today(),
        tipo="CUSTO",
        categoria="INSUMOS",
        origem="ESTOQUE",
        origem_id=oid,
    )
    assert lc.origem == "ESTOQUE"
    assert lc.origem_id == oid
