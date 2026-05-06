import uuid
import json
from unittest.mock import AsyncMock, patch, MagicMock
from financeiro.services.resumo_diario_service import ResumoDiarioService
from financeiro.schemas.lancamento_schema import SaudeFinanceiraResumo

async def test_resumo_diario_logic():
    # Mock de dependências
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock do AlertaInteligenteService
    mock_alertas = [
        {
            "id": "1",
            "tipo": "MARGEM",
            "gravidade": "alta",
            "titulo": "Margem Crítica",
            "mensagem": "Sua margem caiu.",
            "impacto": "Risco de prejuízo.",
            "recomendacao": "Reduza custos.",
            "prioridade": 95.0,
            "motivo_prioridade": "Urgente"
        }
    ]
    
    # Mock do LancamentoService
    mock_dre = MagicMock()
    mock_dre.receita_bruta = 100000.0
    mock_dre.custos_operacionais = 80000.0
    mock_dre.margem_percentual = 20.0
    
    with patch("financeiro.services.resumo_diario_service.AlertaInteligenteService") as MockAlertaSvc, \
         patch("financeiro.services.resumo_diario_service.LancamentoService") as MockLancSvc:
        
        # Configura MockAlertaSvc
        alerta_svc_instance = MockAlertaSvc.return_value
        alerta_svc_instance.verificar_alertas = AsyncMock(return_value=mock_alertas)
        
        # Configura MockLancSvc
        lanc_svc_instance = MockLancSvc.return_value
        lanc_svc_instance.gerar_dre = AsyncMock(return_value=mock_dre)
        
        service = ResumoDiarioService(session, tenant_id)
        
        # Mock da IA para evitar chamada externa
        with patch.object(service, "_gerar_resumo_ia", new_callable=AsyncMock) as mock_ia:
            mock_ia.return_value = {
                "texto_resumo": "Tudo sob controle.",
                "recomendacao": "Mantenha o curso.",
                "ia_sucesso": True
            }
            
            resumo = await service.obter_resumo(safra_id)
            
            assert resumo.texto_resumo == "Tudo sob controle."
            assert resumo.saude_financeira.margem == 20.0
            assert len(resumo.top_alertas) == 1
            assert resumo.top_alertas[0].id == "1"
            assert resumo.risco_principal == "Risco de prejuízo."
            assert resumo.ia_disponivel is True
            print("✅ Teste de Lógica do Resumo Diário concluído com sucesso!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_resumo_diario_logic())
