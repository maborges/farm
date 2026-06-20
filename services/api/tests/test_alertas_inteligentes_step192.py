import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from financeiro.services.alerta_inteligente_service import AlertaInteligenteService


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

@pytest.mark.asyncio
async def test_gerar_alertas_baixa_rentabilidade():
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock DRE com margem < 10%
    dre_mock = MagicMock()
    dre_mock.margem_percentual = 5.0
    dre_mock.receita_bruta = 100000
    dre_mock.custos_operacionais = 95000
    session.execute.return_value = FakeScalarResult([])

    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock), \
        patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value={}), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService._analisar_comportamento_usuario", AsyncMock(return_value={
            "taxa_execucao": 0.0,
            "taxa_ignorado": 0.0,
            "tipos_mais_executados": [],
            "tipos_mais_ignorados": [],
            "perfil": "EQUILIBRADO",
        })), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService.gerar_alerta_ia", AsyncMock(side_effect=lambda _safra_id, alertas, _comportamento: alertas)), \
        patch("ia.estresse_financeiro_service.IAEstresseFinanceiroService.simular_estresse_financeiro", return_value={"nivel_risco": "BAIXO"}), \
        patch("ia.predicao_risco_service.IAPredicaoRiscoService.prever_risco_financeiro", return_value={"risco": "BAIXO"}):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)

            # Validações
            assert len(alertas) > 0
            alerta_rentabilidade = next(a for a in alertas if a["tipo"] == "RENTABILIDADE")
            assert alerta_rentabilidade["gravidade"] == "media"

@pytest.mark.asyncio
async def test_gerar_alertas_desvio_critico():
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
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
    session.execute.return_value = FakeScalarResult([])
    
    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock), \
        patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value=analise_mock), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService._analisar_comportamento_usuario", AsyncMock(return_value={
            "taxa_execucao": 0.0,
            "taxa_ignorado": 0.0,
            "tipos_mais_executados": [],
            "tipos_mais_ignorados": [],
            "perfil": "EQUILIBRADO",
        })), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService.gerar_alerta_ia", AsyncMock(side_effect=lambda _safra_id, alertas, _comportamento: alertas)), \
        patch("ia.estresse_financeiro_service.IAEstresseFinanceiroService.simular_estresse_financeiro", return_value={"nivel_risco": "BAIXO"}), \
        patch("ia.predicao_risco_service.IAPredicaoRiscoService.prever_risco_financeiro", return_value={"risco": "BAIXO"}):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)
            
            # Validações
            assert any(a["tipo"] == "PLANEJAMENTO" for a in alertas)
            assert alertas[0]["gravidade"] == "alta"

@pytest.mark.asyncio
async def test_ausencia_de_alertas():
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    
    # Mock DRE saudável e sem desvio
    dre_mock = MagicMock()
    dre_mock.margem_percentual = 15.0
    dre_mock.receita_bruta = 100000
    dre_mock.custos_operacionais = 85000
    session.execute.return_value = FakeScalarResult([])

    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock), \
        patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value={}), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService._analisar_comportamento_usuario", AsyncMock(return_value={
            "taxa_execucao": 0.0,
            "taxa_ignorado": 0.0,
            "tipos_mais_executados": [],
            "tipos_mais_ignorados": [],
            "perfil": "EQUILIBRADO",
        })), \
        patch("financeiro.services.alerta_inteligente_service.AlertaInteligenteService.gerar_alerta_ia", AsyncMock(side_effect=lambda _safra_id, alertas, _comportamento: alertas)), \
        patch("ia.estresse_financeiro_service.IAEstresseFinanceiroService.simular_estresse_financeiro", return_value={"nivel_risco": "BAIXO"}), \
        patch("ia.predicao_risco_service.IAPredicaoRiscoService.prever_risco_financeiro", return_value={"risco": "BAIXO"}):
            svc = AlertaInteligenteService(session, tenant_id)
            alertas = await svc.verificar_alertas(safra_id)
            
            # Validações
            assert len(alertas) == 0
