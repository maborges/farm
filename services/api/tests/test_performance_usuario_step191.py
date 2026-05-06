import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from financeiro.services.performance_service import PerformanceService
from financeiro.schemas.lancamento_schema import DREOperacional

@pytest.mark.asyncio
async def test_performance_usuario_calculo_correto():
    # Mock da sessão e tenant
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    
    # Mock retorno economia total
    mock_res_economia = MagicMock()
    mock_res_economia.scalar.return_value = 15000.50
    
    # Mock retorno decisões (cenários escolhidos)
    mock_cenario = MagicMock()
    mock_cenario.tenant_id = tenant_id
    mock_cenario.safra_id = uuid.uuid4()
    mock_cenario.escolhido = True
    mock_cenario.resultado_simulado = 50000.0
    mock_cenario.nome = "Cenário Teste"
    
    mock_res_decisoes = MagicMock()
    mock_res_decisoes.scalars.return_value.all.return_value = [mock_cenario]
    
    # Mock retorno melhor compra
    mock_compra = MagicMock()
    mock_compra.economia_absoluta = 60000.0
    mock_compra.fornecedor_nome = "Fornecedor Top"
    
    mock_res_compra = MagicMock()
    mock_res_compra.scalar_one_or_none.return_value = mock_compra
    
    session.execute.side_effect = [
        mock_res_economia, # Economia Total
        mock_res_decisoes, # Cenários Escolhidos
        mock_res_compra    # Melhor Compra
    ]
    
    # Mock do LancamentoService para o DRE Real
    with patch("financeiro.services.performance_service.LancamentoService") as MockSvc:
        svc_inst = MockSvc.return_value
        svc_inst.gerar_dre = AsyncMock(return_value={"resultado_operacional": 52000.0})
        
        service = PerformanceService(session, tenant_id)
        result = await service.obter_performance_usuario()
        
        assert result["total_decisoes"] == 1
        assert result["economia_total"] == 15000.50
        assert result["taxa_sucesso"] == 100.0 # 52k vs 50k é 4% de desvio (sucesso)
        assert "Negociação: Fornecedor Top" in result["melhor_decisao"]["safra"]
        assert result["nivel"] == "PROFISSIONAL" # (1 * 1000) + 15000 = 16000 >= 5000

@pytest.mark.asyncio
async def test_performance_usuario_sem_dados():
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    
    mock_res_economia = MagicMock()
    mock_res_economia.scalar.return_value = 0
    
    mock_res_decisoes = MagicMock()
    mock_res_decisoes.scalars.return_value.all.return_value = []
    
    mock_res_compra = MagicMock()
    mock_res_compra.scalar_one_or_none.return_value = None
    
    session.execute.side_effect = [
        mock_res_economia,
        mock_res_decisoes,
        mock_res_compra
    ]
    
    service = PerformanceService(session, tenant_id)
    result = await service.obter_performance_usuario()
    
    assert result["total_decisoes"] == 0
    assert result["economia_total"] == 0
    assert result["taxa_sucesso"] == 0
    assert result["nivel"] == "INICIANTE"
    assert result["ranking"] == "TOP 50%"


@pytest.mark.asyncio
async def test_performance_usuario_aceita_dre_como_schema():
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    mock_res_economia = MagicMock()
    mock_res_economia.scalar.return_value = 1000.0

    mock_cenario = MagicMock()
    mock_cenario.safra_id = uuid.uuid4()
    mock_cenario.resultado_simulado = 20000.0
    mock_cenario.nome = "Cenário Schema"
    mock_cenario.id = uuid.uuid4()

    mock_res_decisoes = MagicMock()
    mock_res_decisoes.scalars.return_value.all.return_value = [mock_cenario]

    mock_res_compra = MagicMock()
    mock_res_compra.scalar_one_or_none.return_value = None

    session.execute.side_effect = [
        mock_res_economia,
        mock_res_decisoes,
        mock_res_compra,
    ]

    dre = DREOperacional(
        receita_bruta=30000.0,
        custos_operacionais=9000.0,
        resultado_operacional=21000.0,
        margem_percentual=70.0,
        breakdown_receitas=[],
        breakdown_custos=[],
    )

    with patch("financeiro.services.performance_service.LancamentoService") as MockSvc:
        svc_inst = MockSvc.return_value
        svc_inst.gerar_dre = AsyncMock(return_value=dre)

        service = PerformanceService(session, tenant_id)
        result = await service.obter_performance_usuario()

        assert result["total_decisoes"] == 1
        assert result["taxa_sucesso"] == 100.0
        assert result["melhor_decisao"]["safra"] == "Planejamento Cenário Schema"


@pytest.mark.asyncio
async def test_performance_usuario_faz_fallback_parcial_quando_consulta_falha():
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    mock_res_decisoes = MagicMock()
    mock_res_decisoes.scalars.return_value.all.return_value = []

    session.execute.side_effect = [
        RuntimeError("compras indisponiveis"),
        mock_res_decisoes,
        RuntimeError("melhor compra indisponivel"),
    ]

    service = PerformanceService(session, tenant_id)
    result = await service.obter_performance_usuario()

    assert result["total_decisoes"] == 0
    assert result["economia_total"] == 0.0
    assert result["nivel"] == "INICIANTE"
