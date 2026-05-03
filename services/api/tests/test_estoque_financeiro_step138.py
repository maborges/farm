"""Step 138 — Testes: integração estoque → financeiro com rastreabilidade."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch, call

from financeiro.models.lancamento import LancamentoFinanceiro


def _make_session(dup_found: bool = False):
    """Helper: monta AsyncSession mockado."""
    session = AsyncMock()
    dup_result = MagicMock()
    dup_result.first = MagicMock(return_value=(uuid.uuid4(),) if dup_found else None)
    session.execute = AsyncMock(return_value=dup_result)
    session.add = MagicMock()
    return session


# ── _criar_lancamento_insumo: campos origem ────────────────────────────────────

@pytest.mark.asyncio
async def test_lancamento_tem_origem_estoque():
    from operacional.services.estoque_service import EstoqueService

    tenant_id = uuid.uuid4()
    mov_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, tenant_id)

    await svc._criar_lancamento_insumo(
        safra_id=safra_id,
        nome_produto="Semente Soja",
        custo_unitario=10.0,
        quantidade=5.0,
        movimentacao_id=mov_id,
    )

    session.add.assert_called_once()
    lancamento = session.add.call_args[0][0]
    assert isinstance(lancamento, LancamentoFinanceiro)
    assert lancamento.origem == "ESTOQUE"
    assert lancamento.origem_id == mov_id


@pytest.mark.asyncio
async def test_lancamento_origem_id_corresponde_movimento():
    from operacional.services.estoque_service import EstoqueService

    tenant_id = uuid.uuid4()
    mov_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, tenant_id)

    await svc._criar_lancamento_insumo(
        safra_id=safra_id,
        nome_produto="Fertilizante",
        custo_unitario=20.0,
        quantidade=3.0,
        movimentacao_id=mov_id,
    )

    lancamento = session.add.call_args[0][0]
    assert lancamento.origem_id == mov_id


@pytest.mark.asyncio
async def test_lancamento_safra_id_preservado():
    from operacional.services.estoque_service import EstoqueService

    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    mov_id = uuid.uuid4()

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, tenant_id)

    await svc._criar_lancamento_insumo(
        safra_id=safra_id,
        nome_produto="Defensivo",
        custo_unitario=15.0,
        quantidade=2.0,
        movimentacao_id=mov_id,
    )

    lancamento = session.add.call_args[0][0]
    assert lancamento.safra_id == safra_id


# ── custo calculado corretamente ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_custo_calculado_quantidade_x_preco():
    from operacional.services.estoque_service import EstoqueService

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, uuid.uuid4())

    await svc._criar_lancamento_insumo(
        safra_id=uuid.uuid4(),
        nome_produto="Soja",
        custo_unitario=12.5,
        quantidade=4.0,
        movimentacao_id=uuid.uuid4(),
    )

    lancamento = session.add.call_args[0][0]
    assert lancamento.valor == pytest.approx(50.0)


# ── idempotência: não duplicar ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repetir_processamento_nao_duplica():
    from operacional.services.estoque_service import EstoqueService

    session = _make_session(dup_found=True)
    svc = EstoqueService(session, uuid.uuid4())

    await svc._criar_lancamento_insumo(
        safra_id=uuid.uuid4(),
        nome_produto="Herbicida",
        custo_unitario=8.0,
        quantidade=10.0,
        movimentacao_id=uuid.uuid4(),
    )

    session.add.assert_not_called()


# ── sem movimentacao_id: não faz check de duplicata ───────────────────────────

@pytest.mark.asyncio
async def test_sem_movimentacao_id_cria_sem_idempotencia():
    from operacional.services.estoque_service import EstoqueService

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, uuid.uuid4())

    await svc._criar_lancamento_insumo(
        safra_id=uuid.uuid4(),
        nome_produto="Insumo legado",
        custo_unitario=5.0,
        quantidade=2.0,
        movimentacao_id=None,
    )

    session.add.assert_called_once()
    lancamento = session.add.call_args[0][0]
    assert lancamento.origem == "ESTOQUE"
    assert lancamento.origem_id is None


# ── valor zero não gera lançamento ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_valor_zero_nao_gera_lancamento():
    from operacional.services.estoque_service import EstoqueService

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, uuid.uuid4())

    await svc._criar_lancamento_insumo(
        safra_id=uuid.uuid4(),
        nome_produto="Item grátis",
        custo_unitario=0.0,
        quantidade=5.0,
        movimentacao_id=uuid.uuid4(),
    )

    session.add.assert_not_called()


# ── descrição padronizada ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_descricao_padronizada():
    from operacional.services.estoque_service import EstoqueService

    session = _make_session(dup_found=False)
    svc = EstoqueService(session, uuid.uuid4())

    await svc._criar_lancamento_insumo(
        safra_id=uuid.uuid4(),
        nome_produto="Herbicida X",
        custo_unitario=5.0,
        quantidade=2.0,
        movimentacao_id=uuid.uuid4(),
    )

    lancamento = session.add.call_args[0][0]
    assert lancamento.descricao == "Uso de insumo: Herbicida X"
    assert lancamento.categoria == "INSUMOS"
    assert lancamento.tipo == "CUSTO"
