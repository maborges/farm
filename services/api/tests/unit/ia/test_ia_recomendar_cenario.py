import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from ia.dre_intelligence_service import ContextoCenarios, RecomendacaoCenarioIA, recomendar_cenario_safra, ContextoDRE

@pytest.mark.asyncio
async def test_recomendar_cenario_deterministico_sem_cenarios():
    """Testa se retorna recomendação vazia quando não há cenários."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = AsyncMock()
    
    dre_real = ContextoDRE(
        receita_bruta=100, custos_operacionais=80, resultado_operacional=20, margem_percentual=20
    )
    ctx = ContextoCenarios(dre_real=dre_real, cenarios=[])

    # Mock para CenarioFinanceiroService.listar retornando lista vazia
    with patch("financeiro.services.cenario_service.CenarioFinanceiroService.listar", return_value=[]), \
         patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_real):
        
        res = await recomendar_cenario_safra(ctx, tenant_id=tenant_id, session=session)
        
        assert res.fonte == "DETERMINISTICO"
        assert "Nenhum cenário" in res.resumo
        assert res.cenario_recomendado_id is None

@pytest.mark.asyncio
async def test_recomendar_cenario_deterministico_fallback_melhor_margem():
    """Testa o fallback determinístico escolhendo a melhor margem."""
    from ia.dre_intelligence_service import _recomendacao_deterministica
    
    dre_real = ContextoDRE(
        receita_bruta=100, custos_operacionais=80, resultado_operacional=20, margem_percentual=20
    )
    
    # cenários na ContextoCenarios é list[dict]
    cenarios = [
        {"id": "1", "nome": "Pessimista", "receita_simulada": 90, "custos_simulados": 80, "resultado_simulado": 10, "margem_simulada": 11.1},
        {"id": "2", "nome": "Otimista", "receita_simulada": 120, "custos_simulados": 70, "resultado_simulado": 50, "margem_simulada": 41.6},
    ]
    
    ctx = ContextoCenarios(dre_real=dre_real, cenarios=cenarios)
    res = _recomendacao_deterministica(ctx)
    
    assert res.fonte == "DETERMINISTICO"
    assert res.cenario_recomendado_id == "2"
    assert "Otimista" in res.resumo

@pytest.mark.asyncio
async def test_recomendar_cenario_ia_sucesso():
    """Testa o fluxo completo de recomendação via IA com sucesso."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    dre_real = ContextoDRE(
        receita_bruta=100000, custos_operacionais=60000, resultado_operacional=40000, margem_percentual=40
    )
    
    cenario_id = str(uuid.uuid4())
    cenarios = [
        {"id": cenario_id, "nome": "Cenário Teste", "receita_simulada": 110000, "custos_simulados": 60000, "resultado_simulado": 50000, "margem_simulada": 45.4}
    ]
    
    ctx = ContextoCenarios(dre_real=dre_real, cenarios=cenarios)
    
    mock_recomendacao = RecomendacaoCenarioIA(
        cenario_recomendado_id=cenario_id,
        resumo="Este é o melhor cenário.",
        justificativas=["Melhor margem"],
        pontos_risco=["Baixo risco"],
        nivel_confianca=0.9,
        fonte="IA"
    )
    
    with patch("ia.dre_intelligence_service.tenant_tem_ia", return_value=True), \
         patch("ia.dre_intelligence_service._ia_globalmente_habilitada", return_value=True), \
         patch("ia.usage_service.verificar_limite_ia", return_value=(True, "OK")), \
         patch("ia.dre_intelligence_service._chamar_ia_recomendacao", return_value=mock_recomendacao), \
         patch("ia.usage_service.registrar_uso_ia", return_value=None):
        
        # Mocking tier query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "PLATINUM"
        session.execute.return_value = mock_result
        
        res = await recomendar_cenario_safra(ctx, tenant_id=tenant_id, session=session)
        
        assert res.fonte == "IA"
        assert res.cenario_recomendado_id == cenario_id
        assert res.resumo == "Este é o melhor cenário."
