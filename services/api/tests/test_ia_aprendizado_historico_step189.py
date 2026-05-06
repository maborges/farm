"""
Step 189 — Testes: IA Aprende com Histórico de Decisão.

Verifica se o histórico de decisões passadas é corretamente recuperado e incluído no prompt da IA.
"""
import uuid
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from ia.dre_intelligence_service import (
    _obter_historico_decisoes, 
    ContextoCenarios, 
    _montar_prompt_recomendacao, 
    ContextoDRE
)

@pytest.mark.asyncio
async def test_obter_historico_decisoes_vazio():
    """Garante que retorna lista vazia se não houver decisões anteriores."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    
    res = await _obter_historico_decisoes(tenant_id, session)
    assert res == []

@pytest.mark.asyncio
async def test_obter_historico_decisoes_com_dados():
    """Verifica se recupera corretamente o histórico e calcula desvios."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    mock_cenario = MagicMock()
    mock_cenario.safra_id = safra_id
    mock_cenario.nome = "Conservador"
    mock_cenario.resultado_simulado = 1000.0  # Planejado
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_cenario]
    session.execute.return_value = mock_result
    
    # Mock do LancamentoService para retornar resultado real
    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new_callable=AsyncMock) as mock_dre:
        # Se planejou 1000 e deu 800, desvio é -20%
        mock_dre.return_value = {"resultado_operacional": 800.0}
        
        res = await _obter_historico_decisoes(tenant_id, session)
        
        assert len(res) == 1
        assert res[0]["cenario_escolhido"] == "Conservador"
        assert res[0]["resultado_real"] == 800.0
        assert res[0]["desvio_percentual"] == "-20.0%"

def test_montar_prompt_recomendacao_com_historico():
    """Valida se o bloco de histórico é injetado corretamente no prompt."""
    ctx_dre = ContextoDRE(
        receita_bruta=1000, 
        custos_operacionais=500, 
        resultado_operacional=500, 
        margem_percentual=50.0
    )
    
    historico = [
        {"cenario_escolhido": "Otimista", "desvio_percentual": "+5.2%"},
        {"cenario_escolhido": "Pessimista", "desvio_percentual": "-15.0%"}
    ]
    
    ctx = ContextoCenarios(
        dre_real=ctx_dre,
        cenarios=[{"id": "1", "nome": "Novo Cenário", "resultado_simulado": 600}],
        historico=historico
    )
    
    prompt = _montar_prompt_recomendacao(ctx)
    
    # Verifica presença do cabeçalho de histórico
    assert "HISTÓRICO DE DECISÕES REAIS" in prompt
    # Verifica itens do histórico
    assert "- Cenário 'Otimista' → desvio +5.2%" in prompt
    assert "- Cenário 'Pessimista' → desvio -15.0%" in prompt
    # Verifica instrução de aprendizado
    assert "Evite repetir estratégias com desempenho negativo" in prompt
    # Verifica se os dados brutos também estão no JSON (para contexto adicional da IA)
    assert "historico_decisoes" in prompt

def test_montar_prompt_recomendacao_sem_historico():
    """Garante que o prompt não contém o bloco de histórico se ele estiver vazio."""
    ctx_dre = ContextoDRE(100, 50, 50, 50)
    ctx = ContextoCenarios(
        dre_real=ctx_dre,
        cenarios=[{"id": "1", "nome": "Cenário A", "resultado_simulado": 60}],
        historico=[]
    )
    
    prompt = _montar_prompt_recomendacao(ctx)
    
    assert "HISTÓRICO DE DECISÕES REAIS" not in prompt
    assert "Evite repetir estratégias" not in prompt
