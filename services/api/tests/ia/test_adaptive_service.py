import pytest
import uuid
from unittest.mock import AsyncMock, patch
from ia.adaptive_service import IAAutopilotAdaptiveService

@pytest.mark.asyncio
async def test_avaliar_ajuste_autonomia_alta_aceitacao():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # Mock das métricas: alta aceitação
    metrics = {
        "total_acoes_automaticas": 10,
        "taxa_aprovacao_implicita": 95.0,
        "taxa_reversao": 5.0
    }
    
    # Mock da config: limite atual 5%
    config = AsyncMock()
    config.limite_impacto_percentual = 5.0
    
    with patch("ia.autopilot_metrics_service.IAAutopilotMetricsService.obter_metricas", return_value=metrics):
        with patch("ia.autopilot_service.IAAutopilotService.get_config", return_value=config):
            result = await IAAutopilotAdaptiveService.avaliar_ajuste_autonomia(session, tenant_id)
            
            assert result["deve_ajustar"] is True
            assert result["acao"] == "AUMENTAR_AUTONOMIA"
            assert result["novo_limite"] == 7.0
            assert "95" in result["mensagem"]

@pytest.mark.asyncio
async def test_avaliar_ajuste_autonomia_alta_reversao():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # Mock das métricas: alta reversão
    metrics = {
        "total_acoes_automaticas": 10,
        "taxa_aprovacao_implicita": 60.0,
        "taxa_reversao": 40.0
    }
    
    # Mock da config: limite atual 10%
    config = AsyncMock()
    config.limite_impacto_percentual = 10.0
    
    with patch("ia.autopilot_metrics_service.IAAutopilotMetricsService.obter_metricas", return_value=metrics):
        with patch("ia.autopilot_service.IAAutopilotService.get_config", return_value=config):
            result = await IAAutopilotAdaptiveService.avaliar_ajuste_autonomia(session, tenant_id)
            
            assert result["deve_ajustar"] is True
            assert result["acao"] == "REDUZIR_AUTONOMIA"
            assert result["novo_limite"] == 8.0
            assert "40" in result["mensagem"]

@pytest.mark.asyncio
async def test_avaliar_ajuste_autonomia_volume_insuficiente():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # Mock das métricas: apenas 2 ações
    metrics = {
        "total_acoes_automaticas": 2,
        "taxa_aprovacao_implicita": 100.0,
        "taxa_reversao": 0.0
    }
    
    config = AsyncMock()
    config.limite_impacto_percentual = 5.0
    
    with patch("ia.autopilot_metrics_service.IAAutopilotMetricsService.obter_metricas", return_value=metrics):
        with patch("ia.autopilot_service.IAAutopilotService.get_config", return_value=config):
            result = await IAAutopilotAdaptiveService.avaliar_ajuste_autonomia(session, tenant_id)
            
            assert result["deve_ajustar"] is False
            assert result["motivo"] == "VOLUME_INSUFICIENTE"
