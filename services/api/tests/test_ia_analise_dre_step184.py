"""
Step 184 — Testes: Análise Inteligente de DRE via IA.

Garante que a lógica de interpretação de resultados e fallbacks funcione conforme o esperado.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from ia.dre_intelligence_service import ContextoDRE, AnaliseDREIA, analisar_dre_safra

@pytest.mark.asyncio
async def test_analise_deterministica_fallback():
    """Testa se o fallback determinístico funciona quando a IA está desligada."""
    from ia.dre_intelligence_service import _analise_deterministica
    
    ctx = ContextoDRE(
        receita_bruta=100000.0,
        custos_operacionais=60000.0,
        resultado_operacional=40000.0,
        margem_percentual=40.0,
        breakdown_custos=[{"categoria": "INSUMOS", "valor": 60000.0}],
        breakdown_receitas=[{"categoria": "VENDA_PRODUCAO", "valor": 100000.0}]
    )
    
    res = _analise_deterministica(ctx)
    
    assert res.fonte == "DETERMINISTICO"
    # O resumo deve conter o valor formatado
    assert "40.000,00" in res.resumo or "40,000.00" in res.resumo
    assert any("saudável" in p.lower() for p in res.pontos_positivos)
    assert res.nivel_confianca == 1.0

@pytest.mark.asyncio
async def test_analise_dre_ia_sucesso():
    """Simula uma chamada de sucesso para a IA (Anthropic)."""
    ctx = ContextoDRE(
        receita_bruta=100000.0,
        custos_operacionais=60000.0,
        resultado_operacional=40000.0,
        margem_percentual=40.0
    )
    
    mock_analise = AnaliseDREIA(
        resumo="Safra com excelente performance.",
        pontos_positivos=["Alta margem"],
        pontos_atencao=["Nenhum"],
        recomendacoes=["Manter estratégia"],
        nivel_confianca=0.98,
        fonte="IA"
    )
    
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # Mocking availability and tier
    with patch("ia.dre_intelligence_service.tenant_tem_ia", return_value=True), \
         patch("ia.dre_intelligence_service._ia_globalmente_habilitada", return_value=True), \
         patch("ia.usage_service.verificar_limite_ia", return_value=(True, "PLANO")), \
         patch("ia.dre_intelligence_service._chamar_ia_dre", return_value=mock_analise), \
         patch("ia.usage_service.registrar_uso_ia", return_value=None):
        
        # Mocking tier query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "GOLD"
        session.execute.return_value = mock_result
        
        res = await analisar_dre_safra(ctx, tenant_id=tenant_id, session=session)
        
        assert res.fonte == "IA"
        assert res.resumo == "Safra com excelente performance."
        assert res.ia_disponivel is True

@pytest.mark.asyncio
async def test_analise_dre_ia_limite_atingido():
    """Testa fallback quando o limite de IA do tenant é atingido."""
    ctx = ContextoDRE(
        receita_bruta=100000.0,
        custos_operacionais=110000.0,
        resultado_operacional=-10000.0,
        margem_percentual=-10.0
    )
    
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    with patch("ia.dre_intelligence_service.tenant_tem_ia", return_value=True), \
         patch("ia.dre_intelligence_service._ia_globalmente_habilitada", return_value=True), \
         patch("ia.usage_service.verificar_limite_ia", return_value=(False, "LIMITE")), \
         patch("ia.usage_service.registrar_uso_ia", return_value=None):
        
        # Mocking tier query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "FREE"
        session.execute.return_value = mock_result
        
        res = await analisar_dre_safra(ctx, tenant_id=tenant_id, session=session)
        
        assert res.fonte == "DETERMINISTICO"
        assert res.limite_atingido is True
        assert any("superam as receitas" in p.lower() for p in res.pontos_atencao)
