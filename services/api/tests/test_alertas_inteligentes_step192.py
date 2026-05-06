import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from financeiro.services.alerta_inteligente_service import AlertaInteligenteService

@pytest.mark.asyncio
async def test_gerar_alertas_baixa_rentabilidade():
    # Setup
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock DRE com margem < 10%
    dre_mock = MagicMock()
    dre_mock.margem_percentual = 5.0
    dre_mock.receita_bruta = 100000
    dre_mock.custos_operacionais = 95000
    
    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock):
        with patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value={}):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)
            
            # Validações
            assert len(alertas) > 0
            assert any(a["tipo"] == "RENTABILIDADE" for a in alertas)
            assert alertas[0]["gravidade"] == "media"

@pytest.mark.asyncio
async def test_gerar_alertas_desvio_critico():
    # Setup
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock DRE saudável
    dre_mock = MagicMock()
    dre_mock.margem_percentual = 20.0
    dre_mock.receita_bruta = 100000
    dre_mock.custos_operacionais = 80000
    
    # Mock Desvio > 20%
    analise_mock = {
        "cenario_escolhido": "Otimista",
        "desvio_percentual": 25.0
    }
    
    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock):
        with patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value=analise_mock):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)
            
            # Validações
            assert any(a["tipo"] == "PLANEJAMENTO" for a in alertas)
            assert alertas[0]["gravidade"] == "alta"

@pytest.mark.asyncio
async def test_ausencia_de_alertas():
    # Setup
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock DRE saudável e sem desvio
    dre_mock = MagicMock()
    dre_mock.margem_percentual = 15.0
    dre_mock.receita_bruta = 100000
    dre_mock.custos_operacionais = 85000
    
    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock):
        with patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value={}):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)
            
            # Validações
            assert len(alertas) == 0
