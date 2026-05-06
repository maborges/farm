import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from ia.upgrade_recomendacao_service import IARecomendacaoUpgradeService
from core.constants import PlanTier

@pytest.mark.asyncio
async def test_get_recomendacao_basico_com_roi_alto():
    """Testa recomendação de upgrade para usuário Básico com ROI significativo."""
    tenant_id = uuid4()
    session = AsyncMock()
    
    # Mock de métricas (Economia de R$ 5000)
    mock_metrics = {
        "metrics": {
            "economia_total_gerada": 5000.0,
            "taxa_acerto_ia": 90,
            "tempo_medio_decisao": 10,
            "taxa_conclusao_acoes": 80,
            "economia_media_por_decisao": 500.0
        }
    }
    
    # Mock de uso (Baixo uso para não disparar por limite)
    mock_uso = {
        "limite_plano": 10,
        "usado_plano": 2,
        "total_disponivel": 8
    }

    with patch("ia.performance_service.IAPerformanceService.get_dashboard_metrics", return_value=mock_metrics), \
         patch("ia.upgrade_recomendacao_service.consultar_creditos", return_value=mock_uso):
        
        result = await IARecomendacaoUpgradeService.get_recomendacao(session, tenant_id, PlanTier.BASICO.value)
        
        assert result["deve_recomendar"] is True
        assert result["plano_recomendado"] == "PROFISSIONAL"
        assert result["tipo"] == "UPGRADE_PLANO"
        assert "economia" in result["mensagem"].lower()

@pytest.mark.asyncio
async def test_get_recomendacao_profissional_limite_proximo():
    """Testa recomendação de créditos para usuário Profissional próximo ao limite."""
    tenant_id = uuid4()
    session = AsyncMock()
    
    mock_metrics = {
        "metrics": {"economia_total_gerada": 100.0}
    }
    
    # Mock de uso (85% do limite)
    mock_uso = {
        "limite_plano": 100,
        "usado_plano": 85,
        "total_disponivel": 15
    }

    with patch("ia.performance_service.IAPerformanceService.get_dashboard_metrics", return_value=mock_metrics), \
         patch("ia.upgrade_recomendacao_service.consultar_creditos", return_value=mock_uso):
        
        result = await IARecomendacaoUpgradeService.get_recomendacao(session, tenant_id, PlanTier.PROFISSIONAL.value)
        
        assert result["deve_recomendar"] is True
        assert result["tipo"] == "CREDITOS_IA"
        assert result["plano_recomendado"] == "ADICIONAL_CREDITOS"

@pytest.mark.asyncio
async def test_sem_recomendacao_para_baixo_roi():
    """Testa que não recomenda nada se o ROI for insignificante."""
    tenant_id = uuid4()
    session = AsyncMock()
    
    mock_metrics = {
        "metrics": {"economia_total_gerada": 10.0}
    }
    mock_uso = {"limite_plano": 10, "usado_plano": 0}

    with patch("ia.performance_service.IAPerformanceService.get_dashboard_metrics", return_value=mock_metrics), \
         patch("ia.upgrade_recomendacao_service.consultar_creditos", return_value=mock_uso):
        
        result = await IARecomendacaoUpgradeService.get_recomendacao(session, tenant_id, PlanTier.BASICO.value)
        
        assert result["deve_recomendar"] is False
