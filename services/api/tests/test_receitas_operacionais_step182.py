"""Step 182 — Testes: Receitas Operacionais."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from financeiro.services.lancamento_service import LancamentoService
from financeiro.schemas.lancamento_schema import LancamentoCreate

@pytest.mark.asyncio
async def test_criar_receita_valida():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock da Safra
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id
    
    session = AsyncMock()
    session.get.return_value = safra_mock
    # Mock do check de duplicata (não encontra nenhuma)
    dup_mock = MagicMock()
    dup_mock.first.return_value = None
    session.execute.return_value = dup_mock
    
    svc = LancamentoService(session, tenant_id)
    dados = LancamentoCreate(
        descricao="Venda de Milho",
        valor=50000.0,
        data=date(2026, 6, 1),
        safra_id=safra_id,
        tipo="RECEITA",
        categoria="VENDA_PRODUCAO"
    )
    
    lancamento = await svc.criar(dados)
    
    assert lancamento.tipo == "RECEITA"
    assert lancamento.valor == 50000.0
    assert lancamento.categoria == "VENDA_PRODUCAO"
    session.add.assert_called_once()

@pytest.mark.asyncio
async def test_erro_categoria_invalida_receita():
    # Isso deve ser pego pelo schema, mas podemos testar o LancamentoCreate diretamente
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError) as exc:
        LancamentoCreate(
            descricao="Venda Inválida",
            valor=100.0,
            data=date(2026, 6, 1),
            safra_id=uuid.uuid4(),
            tipo="RECEITA",
            categoria="INSUMOS" # Insumos é de CUSTO
        )
    assert "Categoria inválida para RECEITA" in str(exc.value)

@pytest.mark.asyncio
async def test_receita_impacta_resumo():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    session = AsyncMock()
    result_mock = MagicMock()
    row = MagicMock()
    row.total_custos = 1000.0
    row.total_receitas = 2500.0
    row.quantidade = 2
    result_mock.one.return_value = row
    session.execute.return_value = result_mock
    
    svc = LancamentoService(session, tenant_id)
    resumo = await svc.resumo(safra_id=safra_id)
    
    assert resumo.total_receitas == 2500.0
    assert resumo.saldo == 1500.0 # 2500 - 1000

@pytest.mark.asyncio
async def test_isolamento_tenant_na_criacao_receita():
    tenant_id_a = uuid.uuid4()
    tenant_id_b = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock da Safra pertencente ao Tenant B
    safra_mock = MagicMock()
    safra_mock.tenant_id = tenant_id_b
    
    session = AsyncMock()
    session.get.return_value = safra_mock
    
    # Tenant A tenta criar receita vinculada à safra do Tenant B
    svc = LancamentoService(session, tenant_id_a)
    dados = LancamentoCreate(
        descricao="Venda Ilegítima",
        valor=1000.0,
        data=date(2026, 6, 1),
        safra_id=safra_id,
        tipo="RECEITA",
        categoria="OUTRAS_RECEITAS"
    )
    
    with pytest.raises(HTTPException) as exc:
        await svc.criar(dados)
    assert exc.value.status_code == 404
    assert "Safra não encontrada" in exc.value.detail
