import uuid
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

import pytest

from ambiental.service import AmbientalService, CarbonoService
from iot_integracao.new_holland.models import CarbonoEmissao, CarbonoProjeto, CarbonoRelatorio


pytestmark = pytest.mark.asyncio


def _result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = items[0] if items else None
    return result


async def test_dashboard_carbono_agrega_totais_e_contagens() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    emissao_1 = MagicMock(spec=CarbonoEmissao, escopo=1, total_co2e=12.5)
    emissao_2 = MagicMock(spec=CarbonoEmissao, escopo=2, total_co2e=7.5)
    projeto = MagicMock(spec=CarbonoProjeto, creditos_verificados=5.0)
    relatorio = MagicMock(spec=CarbonoRelatorio)

    session.execute.side_effect = [
        _result([emissao_1, emissao_2]),
        _result([projeto]),
        _result([relatorio]),
    ]

    service = AmbientalService(session, tenant_id)

    resumo = await service.dashboard_carbono()

    assert resumo["total_emissoes"] == 20.0
    assert resumo["total_creditos"] == 5.0
    assert resumo["saldo_liquido"] == 15.0
    assert resumo["total_emissoes_registradas"] == 2
    assert resumo["total_projetos"] == 1
    assert resumo["total_relatorios"] == 1
    assert resumo["emissoes_escopo_1"] == 12.5
    assert resumo["emissoes_escopo_2"] == 7.5
    assert resumo["emissoes_escopo_3"] == 0


async def test_registrar_emissao_carbono_preenche_factor_padrao_e_total() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    emissao = MagicMock(spec=CarbonoEmissao)
    session.execute.return_value = _result([])

    service = AmbientalService(session, tenant_id)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    created = await service.registrar_emissao_carbono(
        {
            "escopo": 1,
            "categoria": "diesel",
            "quantidade": 10,
            "unidade": "L",
            "data_referencia": datetime(2026, 1, 1, 8, 30),
        }
    )

    session.add.assert_called_once()
    assert created.fator_emissao == 2.68
    assert created.total_co2e == 26.8


async def test_gerar_relatorio_carbono_cria_periodo_e_saldo() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    emissao = MagicMock(spec=CarbonoEmissao, escopo=1, total_co2e=12.0)
    projeto = MagicMock(spec=CarbonoProjeto, creditos_verificados=3.0, status="certificado")
    session.execute.side_effect = [
        _result([emissao]),
        _result([projeto]),
    ]
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    service = AmbientalService(session, tenant_id)

    relatorio = await service.gerar_relatorio_carbono(date(2026, 1, 1), date(2026, 1, 31))

    assert relatorio.total_geral == 12.0
    assert relatorio.creditos_gerados == 3.0
    assert relatorio.saldo_liquido == 9.0
    assert relatorio.escopo_1_total == 12.0
    assert relatorio.escopo_2_total == 0
    assert relatorio.escopo_3_total == 0


async def test_exportar_pdf_carbono_retorna_bytes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    relatorio = SimpleNamespace(
        id=7,
        tenant_id=str(tenant_id),
        periodo_inicio=datetime(2026, 1, 1),
        periodo_fim=datetime(2026, 1, 31),
    )
    session.execute.return_value = _result([relatorio])

    service = AmbientalService(session, tenant_id)

    with patch.object(CarbonoService, "gerar_pdf_resumo", new=AsyncMock(return_value=b"%PDF-1.4\n")) as mocked_pdf:
        pdf = await service.exportar_pdf_carbono(7)

    assert pdf == b"%PDF-1.4\n"
    mocked_pdf.assert_awaited_once()
