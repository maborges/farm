import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from ia.dre_intelligence_service import _calcular_score_ia

@pytest.mark.asyncio
async def test_calcular_score_ia_sem_dados():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # Mock do resultado do banco (vazio)
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_res
    
    score = await _calcular_score_ia(tenant_id, session)
    
    assert score["total_decisoes"] == 0
    assert score["status"] == "SEM_DADOS"

@pytest.mark.asyncio
async def test_calcular_score_ia_com_sucesso():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    safra_id = uuid.uuid4()
    
    # Mock do cenário recomendado e escolhido
    cenario = MagicMock()
    cenario.safra_id = safra_id
    cenario.resultado_simulado = 1000.0
    cenario.recomendado_pela_ia = True
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [cenario]
    session.execute.return_value = mock_res
    
    # Mock do LancamentoService para retornar o DRE Real
    with patch("financeiro.services.lancamento_service.LancamentoService") as mock_svc_cls:
        mock_svc = AsyncMock()
        # Resultado real com desvio de 5% (Acerto)
        mock_svc.gerar_dre.return_value = {"resultado_operacional": 1050.0}
        mock_svc_cls.return_value = mock_svc
        
        score = await _calcular_score_ia(tenant_id, session)
        
        assert score["total_decisoes"] == 1
        assert score["acertos"] == 1
        assert score["taxa_acerto"] == 100.0
        assert score["status"] == "BOM"

@pytest.mark.asyncio
async def test_calcular_score_ia_com_distribuicao():
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    
    # 3 cenários: 1 acerto, 1 parcial, 1 erro
    c1 = MagicMock(resultado_simulado=1000.0, safra_id=uuid.uuid4()) # Real 1050 (5% - Acerto)
    c2 = MagicMock(resultado_simulado=1000.0, safra_id=uuid.uuid4()) # Real 1200 (20% - Parcial)
    c3 = MagicMock(resultado_simulado=1000.0, safra_id=uuid.uuid4()) # Real 1400 (40% - Erro)
    
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [c1, c2, c3]
    session.execute.return_value = mock_res
    
    with patch("financeiro.services.lancamento_service.LancamentoService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.gerar_dre.side_effect = [
            {"resultado_operacional": 1050.0},
            {"resultado_operacional": 1200.0},
            {"resultado_operacional": 1400.0}
        ]
        mock_svc_cls.return_value = mock_svc
        
        score = await _calcular_score_ia(tenant_id, session)
        
        assert score["total_decisoes"] == 3
        assert score["acertos"] == 1
        assert score["parciais"] == 1
        assert score["erros"] == 1
        assert score["taxa_acerto"] == 33.3
        assert score["status"] == "CRITICO"
