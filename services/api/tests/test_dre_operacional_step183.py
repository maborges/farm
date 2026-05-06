"""Step 183 — Testes: DRE Operacional."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from financeiro.services.lancamento_service import LancamentoService

@pytest.mark.asyncio
async def test_calculo_dre_operacional_completo():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    session = AsyncMock()
    
    # Mock da Safra
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id
    session.get.return_value = safra_mock
    
    # Mock das Receitas por Categoria
    rec_mock = MagicMock()
    rec_mock.fetchall.return_value = [
        ("VENDA_PRODUCAO", 100000.0),
        ("OUTRAS_RECEITAS", 5000.0)
    ]
    
    # Mock dos Custos por Categoria
    custo_mock = MagicMock()
    custo_mock.fetchall.return_value = [
        ("INSUMOS", 40000.0),
        ("OPERACOES", 20000.0),
        ("MAO_OBRA", 10000.0)
    ]
    
    # Simula as duas execuções (uma para receita, outra para custo)
    session.execute.side_effect = [rec_mock, custo_mock]
    
    svc = LancamentoService(session, tenant_id)
    dre = await svc.gerar_dre(safra_id)
    
    assert dre.receita_bruta == 105000.0
    assert dre.custos_operacionais == 70000.0
    assert dre.resultado_operacional == 35000.0
    assert dre.margem_percentual == pytest.approx(33.333, 0.01)
    assert len(dre.breakdown_receitas) == 2
    assert len(dre.breakdown_custos) == 3

@pytest.mark.asyncio
async def test_dre_safra_sem_lancamentos():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    session = AsyncMock()
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id
    session.get.return_value = safra_mock
    
    empty_mock = MagicMock()
    empty_mock.fetchall.return_value = []
    session.execute.return_value = empty_mock
    
    svc = LancamentoService(session, tenant_id)
    dre = await svc.gerar_dre(safra_id)
    
    assert dre.receita_bruta == 0
    assert dre.resultado_operacional == 0
    assert dre.margem_percentual == 0

@pytest.mark.asyncio
async def test_dre_isolamento_tenant():
    tenant_id_a = uuid.uuid4()
    tenant_id_b = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    session = AsyncMock()
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id_b # Safra é do Tenant B
    session.get.return_value = safra_mock
    
    # Tenant A tenta acessar
    svc = LancamentoService(session, tenant_id_a)
    
    with pytest.raises(HTTPException) as exc:
        await svc.gerar_dre(safra_id)
    assert exc.value.status_code == 404
