"""Step 140 — Testes: edição segura de lançamentos financeiros."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from financeiro.schemas.lancamento_schema import LancamentoUpdate
from financeiro.models.lancamento import LancamentoFinanceiro


def _make_lancamento(origem: str | None = None, tenant_id: uuid.UUID | None = None) -> LancamentoFinanceiro:
    tid = tenant_id or uuid.uuid4()
    return LancamentoFinanceiro(
        id=uuid.uuid4(),
        tenant_id=tid,
        safra_id=None,
        descricao="Custo original",
        valor=100.0,
        data=date(2026, 4, 1),
        tipo="CUSTO",
        categoria="OPERACOES",
        origem=origem,
        origem_id=None,
    )


def _make_session(lancamento: LancamentoFinanceiro | None):
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = lancamento
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda obj: obj)
    return session


# ── schema: LancamentoUpdate ──────────────────────────────────────────────────

def test_update_todos_opcionais():
    u = LancamentoUpdate()
    assert u.descricao is None
    assert u.valor is None
    assert u.data is None
    assert u.categoria is None


def test_update_valor_invalido_rejeitado():
    with pytest.raises(Exception):
        LancamentoUpdate(valor=0)


def test_update_categoria_invalida_rejeitada():
    with pytest.raises(Exception):
        LancamentoUpdate(categoria="XPTO")


def test_update_categoria_valida():
    u = LancamentoUpdate(categoria="insumos")
    assert u.categoria == "INSUMOS"


# ── service: edição manual permitida ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_edicao_manual_permitida():
    from financeiro.services.lancamento_service import LancamentoService

    tenant_id = uuid.uuid4()
    lanc = _make_lancamento(origem=None, tenant_id=tenant_id)
    session = _make_session(lanc)

    svc = LancamentoService(session, tenant_id)
    update = LancamentoUpdate(descricao="Novo nome", valor=200.0)
    result = await svc.atualizar(lanc.id, update)

    assert result.descricao == "Novo nome"
    assert result.valor == 200.0


@pytest.mark.asyncio
async def test_edicao_origem_manual_explicita_permitida():
    from financeiro.services.lancamento_service import LancamentoService

    tenant_id = uuid.uuid4()
    lanc = _make_lancamento(origem="MANUAL", tenant_id=tenant_id)
    session = _make_session(lanc)

    svc = LancamentoService(session, tenant_id)
    result = await svc.atualizar(lanc.id, LancamentoUpdate(valor=50.0))
    assert result.valor == 50.0


# ── service: edição automático bloqueada ─────────────────────────────────────

@pytest.mark.asyncio
async def test_edicao_estoque_bloqueada():
    from financeiro.services.lancamento_service import LancamentoService
    from fastapi import HTTPException

    tenant_id = uuid.uuid4()
    lanc = _make_lancamento(origem="ESTOQUE", tenant_id=tenant_id)
    session = _make_session(lanc)

    svc = LancamentoService(session, tenant_id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.atualizar(lanc.id, LancamentoUpdate(valor=999.0))
    assert exc_info.value.status_code == 422
    assert "estoque" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_edicao_outra_origem_automatica_bloqueada():
    from financeiro.services.lancamento_service import LancamentoService
    from fastapi import HTTPException

    tenant_id = uuid.uuid4()
    lanc = _make_lancamento(origem="NFE", tenant_id=tenant_id)
    session = _make_session(lanc)

    svc = LancamentoService(session, tenant_id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.atualizar(lanc.id, LancamentoUpdate(descricao="Hack"))
    assert exc_info.value.status_code == 422


# ── service: 404 quando não encontrado ───────────────────────────────────────

@pytest.mark.asyncio
async def test_edicao_lancamento_nao_encontrado():
    from financeiro.services.lancamento_service import LancamentoService
    from fastapi import HTTPException

    session = _make_session(None)
    svc = LancamentoService(session, uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await svc.atualizar(uuid.uuid4(), LancamentoUpdate(valor=10.0))
    assert exc_info.value.status_code == 404


# ── service: tenant isolation ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_edicao_tenant_isolation():
    from financeiro.services.lancamento_service import LancamentoService
    from fastapi import HTTPException

    # Sessão não encontra o registro (pertence a outro tenant)
    session = _make_session(None)
    svc = LancamentoService(session, uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await svc.atualizar(uuid.uuid4(), LancamentoUpdate(valor=10.0))
    assert exc_info.value.status_code == 404


# ── rota registrada ───────────────────────────────────────────────────────────

def test_rota_patch_lancamento_registrada():
    from financeiro.routers.lancamentos import router
    paths = {route.path for route in router.routes}
    assert "/lancamentos/{lancamento_id}" in paths


def test_rota_patch_metodo_patch():
    from financeiro.routers.lancamentos import router
    for route in router.routes:
        if route.path == "/lancamentos/{lancamento_id}":
            assert "PATCH" in route.methods
            break
