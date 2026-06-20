import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from enterprise.models.sprints_27_33 import AnimalGenetica, ConfinamentoLote, Cocho, RacaoTMR, SugestaoAcasalamento
from pecuaria.advanced_service import PecuariaAdvancedService
from pecuaria.producao.models import ProducaoLeite


pytestmark = pytest.mark.asyncio


def _result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


async def test_resumo_genetica_agrega_registros() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    genetica_1 = MagicMock(spec=AnimalGenetica, matriz=True, reprodutor=False)
    genetica_2 = MagicMock(spec=AnimalGenetica, matriz=False, reprodutor=True)
    sugestao = MagicMock(spec=SugestaoAcasalamento)
    session.execute.side_effect = [_result([genetica_1, genetica_2]), _result([sugestao])]

    resumo = await PecuariaAdvancedService(session, tenant_id).resumo_genetica()

    assert resumo["total_registros"] == 2
    assert resumo["total_matrizes"] == 1
    assert resumo["total_reprodutores"] == 1
    assert resumo["total_sugestoes"] == 1


async def test_resumo_confinamento_agrega_lotes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    lote_1 = MagicMock(spec=ConfinamentoLote, total_animais=20, ganho_medio_diario=1.2, conversao_alimentar=6.1)
    lote_2 = MagicMock(spec=ConfinamentoLote, total_animais=30, ganho_medio_diario=1.6, conversao_alimentar=5.8)
    racao = MagicMock(spec=RacaoTMR)
    cocho = MagicMock(spec=Cocho)
    session.execute.side_effect = [_result([lote_1, lote_2]), _result([racao]), _result([cocho])]

    resumo = await PecuariaAdvancedService(session, tenant_id).resumo_confinamento()

    assert resumo["total_lotes"] == 2
    assert resumo["total_animais"] == 50
    assert resumo["total_racoes"] == 1
    assert resumo["total_cochos"] == 1
    assert resumo["gmd_medio"] == pytest.approx(1.4)
    assert resumo["conversao_media"] == pytest.approx(5.95)


async def test_resumo_leite_agrega_volume() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    prod_1 = MagicMock(spec=ProducaoLeite, volume_litros=100.0, gordura_pct=3.5, proteina_pct=3.2)
    prod_2 = MagicMock(spec=ProducaoLeite, volume_litros=120.0, gordura_pct=3.7, proteina_pct=3.1)
    session.execute.return_value = _result([prod_1, prod_2])

    resumo = await PecuariaAdvancedService(session, tenant_id).resumo_leite()

    assert resumo["total_registros"] == 2
    assert resumo["volume_total_litros"] == 220.0
    assert resumo["media_volume_litros"] == 110.0
    assert resumo["media_gordura_pct"] == pytest.approx(3.6)
    assert resumo["media_proteina_pct"] == pytest.approx(3.15)


async def test_criar_producao_leite_persiste_tenant() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    service = PecuariaAdvancedService(session, tenant_id)
    obj = await service.criar_producao(
        {
            "unidade_produtiva_id": uuid.uuid4(),
            "data": date(2026, 1, 1),
            "turno": "MANHA",
            "volume_litros": 100,
        }
    )

    session.add.assert_called_once()
    assert obj.tenant_id == tenant_id
