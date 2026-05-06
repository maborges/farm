import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from ia.performance_service import IAPerformanceService

@pytest.mark.asyncio
async def test_get_dashboard_metrics_no_data():
    """Testa o dashboard de performance quando não há dados."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    
    # Mock para queries retornando zero/nulo
    mock_row_acerto = MagicMock()
    mock_row_acerto.total = 0
    mock_row_acerto.uteis = 0
    
    mock_row_alertas = MagicMock()
    mock_row_alertas.total = 0
    mock_row_alertas.visualizados = 0
    mock_row_alertas.executados = 0
    
    mock_row_acoes = MagicMock()
    mock_row_acoes.total = 0
    mock_row_acoes.concluidas = 0
    
    res_acerto = MagicMock()
    res_acerto.one.return_value = mock_row_acerto
    
    res_alertas = MagicMock()
    res_alertas.one.return_value = mock_row_alertas
    
    res_acoes = MagicMock()
    res_acoes.one.return_value = mock_row_acoes
    
    res_tempo = MagicMock()
    res_tempo.scalar.return_value = 0
    
    res_economia = MagicMock()
    res_economia.scalars.return_value = []
    
    # Configurando o mock da sessão para retornar os resultados na ordem
    session.execute.side_effect = [res_acerto, res_alertas, res_acoes, res_tempo, res_economia]
    
    res = await IAPerformanceService.get_dashboard_metrics(session, tenant_id)
    
    assert res["metrics"]["taxa_acerto_ia"] == 0.0
    assert res["metrics"]["economia_total_gerada"] == 0.0
    assert res["metrics"]["taxa_conclusao_acoes"] == 0.0
    assert res["funil"]["gerados"] == 0
    assert "economia média de R$ 0.00" in res["resumo_performance"]

@pytest.mark.asyncio
async def test_get_dashboard_metrics_with_data():
    """Testa o dashboard de performance com dados populados."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    
    # 1. Mock para taxa de acerto (8 de 10 úteis = 80%)
    mock_row_acerto = MagicMock()
    mock_row_acerto.total = 10
    mock_row_acerto.uteis = 8
    res_acerto = MagicMock()
    res_acerto.one.return_value = mock_row_acerto
    
    # 2. Mock para alertas (100 gerados, 80 visualizados, 40 executados = 50% de execução)
    mock_row_alertas = MagicMock()
    mock_row_alertas.total = 100
    mock_row_alertas.visualizados = 80
    mock_row_alertas.executados = 40
    res_alertas = MagicMock()
    res_alertas.one.return_value = mock_row_alertas
    
    # 3. Mock para ações assistidas (40 iniciadas, 30 concluídas = 75% de conclusão)
    mock_row_acoes = MagicMock()
    mock_row_acoes.total = 40
    mock_row_acoes.concluidas = 30
    res_acoes = MagicMock()
    res_acoes.one.return_value = mock_row_acoes
    
    # 4. Mock para tempo médio (600 segundos = 10 minutos)
    res_tempo = MagicMock()
    res_tempo.scalar.return_value = 600.0
    
    # 5. Mock para economia (Total: 2000.50)
    res_economia = MagicMock()
    res_economia.scalars.return_value = [{"impacto_financeiro": 1500.50}, {"impacto_financeiro": 500.00}]
    
    session.execute.side_effect = [res_acerto, res_alertas, res_acoes, res_tempo, res_economia]
    
    res = await IAPerformanceService.get_dashboard_metrics(session, tenant_id)
    
    assert res["metrics"]["taxa_acerto_ia"] == 80.0
    assert res["metrics"]["taxa_execucao_alertas"] == 50.0
    assert res["metrics"]["taxa_conclusao_acoes"] == 75.0
    assert res["metrics"]["tempo_medio_decisao"] == 10.0
    assert res["metrics"]["economia_total_gerada"] == 2000.50
    assert res["metrics"]["economia_media_por_decisao"] == 2000.50 / 30
    assert "economia média de R$ 66.68" in res["resumo_performance"]
    assert "taxa de acerto de 80.0%" in res["resumo_performance"]
