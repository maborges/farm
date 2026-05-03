"""Step 139 — Testes: auditoria operacional estoque → financeiro."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from financeiro.schemas.lancamento_schema import LancamentoOrigemItem, LancamentoResponse


# ── schema: LancamentoOrigemItem ──────────────────────────────────────────────

def test_lancamento_origem_item_campos():
    item = LancamentoOrigemItem(
        lancamento_id=uuid.uuid4(),
        descricao="Uso de insumo: Herbicida",
        valor=192.50,
        origem="ESTOQUE",
        origem_id=uuid.uuid4(),
        data=date(2026, 5, 1),
        categoria="INSUMOS",
        gerado_automaticamente=True,
    )
    assert item.gerado_automaticamente is True
    assert item.origem == "ESTOQUE"


def test_lancamento_origem_item_manual():
    item = LancamentoOrigemItem(
        lancamento_id=uuid.uuid4(),
        descricao="Combustível trator",
        valor=300.0,
        origem="MANUAL",
        origem_id=None,
        data=date(2026, 4, 10),
        categoria="OPERACOES",
        gerado_automaticamente=False,
    )
    assert item.gerado_automaticamente is False
    assert item.origem_id is None


# ── schema: LancamentoResponse.gerado_automaticamente ─────────────────────────

def test_response_gerado_automaticamente_true():
    r = LancamentoResponse(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=None,
        descricao="Uso de insumo: Soja",
        valor=100.0,
        data=date.today(),
        tipo="CUSTO",
        categoria="INSUMOS",
        origem="ESTOQUE",
        origem_id=uuid.uuid4(),
        created_at=__import__("datetime").datetime.now(),
    )
    assert r.gerado_automaticamente is True


def test_response_gerado_automaticamente_false():
    r = LancamentoResponse(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=None,
        descricao="Custo manual",
        valor=50.0,
        data=date.today(),
        tipo="CUSTO",
        categoria="OPERACOES",
        origem=None,
        origem_id=None,
        created_at=__import__("datetime").datetime.now(),
    )
    assert r.gerado_automaticamente is False


# ── service: listar_origens ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_origens_retorna_lista():
    from financeiro.services.lancamento_service import LancamentoService
    from financeiro.models.lancamento import LancamentoFinanceiro

    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    mov_id = uuid.uuid4()

    lancamento = LancamentoFinanceiro(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        descricao="Uso de insumo: Fertilizante",
        valor=192.50,
        data=date(2026, 5, 1),
        tipo="CUSTO",
        categoria="INSUMOS",
        origem="ESTOQUE",
        origem_id=mov_id,
    )

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [lancamento]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    svc = LancamentoService(session, tenant_id)
    itens = await svc.listar_origens(safra_id)

    assert len(itens) == 1
    assert itens[0].origem == "ESTOQUE"
    assert itens[0].origem_id == mov_id
    assert itens[0].gerado_automaticamente is True


@pytest.mark.asyncio
async def test_listar_origens_manual_gerado_false():
    from financeiro.services.lancamento_service import LancamentoService
    from financeiro.models.lancamento import LancamentoFinanceiro

    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    lancamento = LancamentoFinanceiro(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        descricao="Custo manual",
        valor=80.0,
        data=date(2026, 4, 15),
        tipo="CUSTO",
        categoria="OPERACOES",
        origem=None,
        origem_id=None,
    )

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [lancamento]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    svc = LancamentoService(session, tenant_id)
    itens = await svc.listar_origens(safra_id)

    assert itens[0].gerado_automaticamente is False
    assert itens[0].origem == "MANUAL"


# ── rota registrada ───────────────────────────────────────────────────────────

def test_rota_origens_registrada():
    from financeiro.routers.lancamentos import router
    paths = {route.path for route in router.routes}
    assert "/lancamentos/origens" in paths


def test_rota_origens_metodo_get():
    from financeiro.routers.lancamentos import router
    for route in router.routes:
        if route.path == "/lancamentos/origens":
            assert "GET" in route.methods
            break
