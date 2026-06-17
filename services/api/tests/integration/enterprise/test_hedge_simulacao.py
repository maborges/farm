import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from financeiro.hedge.schemas import HedgeExposicaoResponse, SimulacaoExposicaoRequest
from financeiro.hedge.service import HedgeExposureService
from core.exceptions import BusinessRuleError

pytestmark = pytest.mark.asyncio

TENANT_ID = uuid4()

def _make_session() -> MagicMock:
    return MagicMock()

def get_base_response():
    return HedgeExposicaoResponse(
        tenant_id=TENANT_ID,
        safra_id=None,
        commodity=None,
        producao_estimada_sc=10000.0,
        estoque_fisico_sc=2000.0,
        exposicao_bruta_sc=12000.0,
        ja_vendido_sc=5000.0,
        ja_hedgeado_sc=4000.0,
        exposicao_liquida_sc=7000.0,
        exposicao_aberta_sc=3000.0,
        percentual_cobertura=57.14,
        hedge_ratio=0.5714,
        classificacao_risco="BOM",
    )


@patch("financeiro.hedge.service.HedgeExposureService.calcular_exposicao")
async def test_simulacao_sucesso_aumentando_producao(mock_calc):
    mock_calc.return_value = get_base_response()
    request = SimulacaoExposicaoRequest(
        variacao_producao_sc=3000.0,
        variacao_estoque_sc=0.0,
        variacao_venda_sc=0.0,
        variacao_hedge_sc=0.0
    )
    
    svc = HedgeExposureService(_make_session(), TENANT_ID)
    data = await svc.simular_exposicao(request)
    
    # Atual
    assert data.cenario_atual.producao_estimada_sc == 10000.0
    assert data.cenario_atual.exposicao_bruta_sc == 12000.0
    
    # Simulado
    assert data.cenario_simulado.producao_estimada_sc == 13000.0
    assert data.cenario_simulado.exposicao_bruta_sc == 15000.0
    assert data.cenario_simulado.exposicao_liquida_sc == 10000.0 # 15000 - 5000
    assert data.cenario_simulado.exposicao_aberta_sc == 6000.0 # 10000 - 4000
    assert data.cenario_simulado.percentual_cobertura == 40.0


@patch("financeiro.hedge.service.HedgeExposureService.calcular_exposicao")
async def test_simulacao_erro_producao_negativa(mock_calc):
    mock_calc.return_value = get_base_response()
    request = SimulacaoExposicaoRequest(
        variacao_producao_sc=-15000.0,
    )
    
    svc = HedgeExposureService(_make_session(), TENANT_ID)
    with pytest.raises(BusinessRuleError, match="não pode ser negativa"):
        await svc.simular_exposicao(request)


@patch("financeiro.hedge.service.HedgeExposureService.calcular_exposicao")
async def test_simulacao_erro_venda_acima_do_lastro(mock_calc):
    mock_calc.return_value = get_base_response()
    request = SimulacaoExposicaoRequest(
        variacao_venda_sc=8000.0,
    )
    
    svc = HedgeExposureService(_make_session(), TENANT_ID)
    with pytest.raises(BusinessRuleError, match="excede o lastro físico"):
        await svc.simular_exposicao(request)


@patch("financeiro.hedge.service.HedgeExposureService.calcular_exposicao")
async def test_simulacao_erro_hedge_acima_exposicao(mock_calc):
    mock_calc.return_value = get_base_response()
    request = SimulacaoExposicaoRequest(
        variacao_hedge_sc=3500.0,
    )
    
    svc = HedgeExposureService(_make_session(), TENANT_ID)
    with pytest.raises(BusinessRuleError, match="excede a exposição real"):
        await svc.simular_exposicao(request)


@patch("financeiro.hedge.service.HedgeExposureService.calcular_exposicao")
async def test_simulacao_venda_sem_base_fisica(mock_calc):
    base_response = HedgeExposicaoResponse(
        tenant_id=TENANT_ID,
        producao_estimada_sc=0.0,
        estoque_fisico_sc=0.0,
        exposicao_bruta_sc=0.0,
        ja_vendido_sc=0.0,
        ja_hedgeado_sc=0.0,
        exposicao_liquida_sc=0.0,
        exposicao_aberta_sc=0.0,
        percentual_cobertura=0.0,
        hedge_ratio=0.0,
        classificacao_risco="DESCOBERTO",
    )
    mock_calc.return_value = base_response
    
    request = SimulacaoExposicaoRequest(
        variacao_venda_sc=1000.0,
    )
    
    svc = HedgeExposureService(_make_session(), TENANT_ID)
    with pytest.raises(BusinessRuleError, match="sem base física"):
        await svc.simular_exposicao(request)
