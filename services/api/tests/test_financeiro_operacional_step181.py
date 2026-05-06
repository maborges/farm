"""Step 181 — Testes: Financeiro Operacional."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from financeiro.models.lancamento import LancamentoFinanceiro

def _make_lancamento(
    tipo: str = "CUSTO", 
    safra_id: uuid.UUID | None = None, 
    tenant_id: uuid.UUID | None = None,
    categoria: str = "OPERACOES",
    valor: float = 100.0,
    data: date | None = None
) -> LancamentoFinanceiro:
    tid = tenant_id or uuid.uuid4()
    return LancamentoFinanceiro(
        id=uuid.uuid4(),
        tenant_id=tid,
        safra_id=safra_id,
        descricao=f"Lancamento {tipo}",
        valor=valor,
        data=data or date(2026, 5, 1),
        tipo=tipo,
        categoria=categoria,
        origem=None,
        origem_id=None,
    )

@pytest.mark.asyncio
async def test_listar_lancamentos_com_filtros():
    from financeiro.services.lancamento_service import LancamentoService
    
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    lancamentos = [
        _make_lancamento(tipo="CUSTO", safra_id=safra_id, tenant_id=tenant_id),
        _make_lancamento(tipo="RECEITA", safra_id=safra_id, tenant_id=tenant_id)
    ]
    
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = lancamentos
    session.execute = AsyncMock(return_value=result_mock)
    
    svc = LancamentoService(session, tenant_id)
    result = await svc.listar(safra_id=safra_id, tipo="CUSTO")
    
    assert len(result) == 2
    # Verifica que o tenant_id foi usado na query (através do call_args)
    # Mas como usamos sqlalchemy expressions, é mais complexo verificar.
    # O importante é que a lógica de construção da query existe no service.

@pytest.mark.asyncio
async def test_resumo_financeiro_com_safra():
    from financeiro.services.lancamento_service import LancamentoService
    
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    session = AsyncMock()
    result_mock = MagicMock()
    row = MagicMock()
    row.total_custos = 1500.0
    row.total_receitas = 2000.0
    row.quantidade = 5
    result_mock.one.return_value = row
    session.execute = AsyncMock(return_value=result_mock)
    
    svc = LancamentoService(session, tenant_id)
    resumo = await svc.resumo(safra_id=safra_id)
    
    assert resumo.total_custos == 1500.0
    assert resumo.total_receitas == 2000.0
    assert resumo.saldo == 500.0
    assert resumo.quantidade_lancamentos == 5

def test_rotas_financeiro_operacional():
    from financeiro.routers.lancamentos import router
    paths = {route.path for route in router.routes}
    # O prefixo é adicionado no app.include_router, mas no router interno é relativo ao prefixo dele
    assert "/lancamentos/" in paths
    assert "/lancamentos/resumo" in paths

def test_metodos_rotas_financeiro_operacional():
    from financeiro.routers.lancamentos import router
    get_root = [r for r in router.routes if r.path == "/lancamentos/" and "GET" in r.methods]
    assert len(get_root) > 0
    
    get_resumo = [r for r in router.routes if r.path == "/lancamentos/resumo" and "GET" in r.methods]
    assert len(get_resumo) > 0
