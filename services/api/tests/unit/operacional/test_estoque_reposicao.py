import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import AlertaEstoqueItem

@pytest.mark.asyncio
async def test_calculo_quantidade_sugerida_reposicao():
    """
    Step 146: Validar cálculo de sugestão de reposição.
    Regra: sugerido = (estoque_minimo * 1.2) - saldo_atual
    """
    session = AsyncMock()
    tenant_id = uuid4()
    svc = EstoqueService(session, tenant_id)
    
    # Mock para listar_saldos
    # Item 1: Abaixo do mínimo (Mín: 100, Atual: 50)
    # Sugestão: (100 * 1.2) - 50 = 120 - 50 = 70
    saldo1 = MagicMock()
    saldo1.id = uuid4()
    saldo1.produto_id = uuid4()
    saldo1.produto_nome = "Fertilizante A"
    saldo1.deposito_nome = "Depósito 1"
    saldo1.quantidade_atual = 50.0
    saldo1.estoque_minimo = 100.0
    saldo1.unidade_medida = "L"
    saldo1.abaixo_minimo = True
    
    # Item 2: Acima do mínimo (Mín: 100, Atual: 150)
    # Não deve aparecer no alerta
    saldo2 = MagicMock()
    saldo2.id = uuid4()
    saldo2.produto_id = uuid4()
    saldo2.produto_nome = "Semente B"
    saldo2.deposito_nome = "Depósito 1"
    saldo2.quantidade_atual = 150.0
    saldo2.estoque_minimo = 100.0
    saldo2.unidade_medida = "KG"
    saldo2.abaixo_minimo = False
    
    # Item 3: Exatamente no mínimo (Mín: 100, Atual: 100)
    # Abaixo_minimo True (conforme regra Step 144/145: saldo_atual <= estoque_minimo)
    # Sugestão: (100 * 1.2) - 100 = 120 - 100 = 20
    saldo3 = MagicMock()
    saldo3.id = uuid4()
    saldo3.produto_id = uuid4()
    saldo3.produto_nome = "Defensivo C"
    saldo3.deposito_nome = "Depósito 2"
    saldo3.quantidade_atual = 100.0
    saldo3.estoque_minimo = 100.0
    saldo3.unidade_medida = "L"
    saldo3.abaixo_minimo = True
    
    svc.listar_saldos = AsyncMock(return_value=[saldo1, saldo2, saldo3])
    
    alertas = await svc.listar_alertas_reposicao()
    
    assert len(alertas) == 2
    
    # Validar Item 1
    alerta1 = next(a for a in alertas if a.produto_nome == "Fertilizante A")
    assert alerta1.id == saldo1.id
    assert alerta1.quantidade_sugerida == 70.0
    
    # Validar Item 3
    alerta3 = next(a for a in alertas if a.produto_nome == "Defensivo C")
    assert alerta3.id == saldo3.id
    assert alerta3.quantidade_sugerida == 20.0
    
    # Item 2 não deve estar nos alertas
    assert not any(a.produto_nome == "Semente B" for a in alertas)
