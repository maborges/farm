import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from financeiro.services.alerta_inteligente_service import AlertaInteligenteService


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


async def test_verificar_alertas_busca_historico_recente_uma_vez():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    historico = [
        SimpleNamespace(
            id=uuid.uuid4(),
            tipo_alerta="RENTABILIDADE",
            ignorado=True,
            created_at=datetime.now(timezone.utc),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            tipo_alerta="EFICIENCIA",
            ignorado=False,
            created_at=datetime.now(timezone.utc),
        ),
    ]
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = FakeScalarResult(historico)

    dre_mock = MagicMock()
    dre_mock.margem_percentual = 15.0
    dre_mock.receita_bruta = 1000.0
    dre_mock.custos_operacionais = 850.0

    with patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", return_value=dre_mock), \
        patch("financeiro.services.cenario_service.CenarioFinanceiroService.analisar_desvio", return_value={
            "cenario_escolhido": "Base",
            "desvio_percentual": 25.0,
        }), \
        patch("ia.estresse_financeiro_service.IAEstresseFinanceiroService.simular_estresse_financeiro", return_value={"nivel_risco": "BAIXO"}), \
        patch("ia.predicao_risco_service.IAPredicaoRiscoService.prever_risco_financeiro", return_value={"risco": "BAIXO"}), \
        patch.object(AlertaInteligenteService, "_analisar_comportamento_usuario", AsyncMock(return_value={
            "taxa_execucao": 0.0,
            "taxa_ignorado": 0.0,
            "tipos_mais_executados": [],
            "tipos_mais_ignorados": [],
            "perfil": "EQUILIBRADO",
        })):
        alertas = await AlertaInteligenteService(session, tenant_id).verificar_alertas(safra_id)

    assert session.execute.await_count == 1
    assert session.flush.await_count == 1
    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "PLANEJAMENTO"
