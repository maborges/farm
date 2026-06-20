from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agricola.dashboard.service import DashboardAgricolaService

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_resumo_agrega_checklist_por_safra_e_fase_em_uma_consulta():
    session = AsyncMock()
    tenant_id = uuid4()
    svc = DashboardAgricolaService(session, tenant_id)

    safra_ativa_1 = SimpleNamespace(id=uuid4(), status="PLANTIO", cultura="Soja", ano_safra="2025/2026")
    safra_ativa_2 = SimpleNamespace(id=uuid4(), status="DESENVOLVIMENTO", cultura="Milho", ano_safra="2025/2026")
    safra_encerrada = SimpleNamespace(id=uuid4(), status="ENCERRADA", cultura="Trigo", ano_safra="2024/2025")

    result_safras = MagicMock()
    result_safras.scalars.return_value.all.return_value = [safra_ativa_1, safra_ativa_2, safra_encerrada]
    result_area = MagicMock()
    result_area.scalar.return_value = 10
    result_custo = MagicMock()
    result_custo.scalar.return_value = 20
    result_meta = MagicMock()
    result_meta.scalar.return_value = 30
    result_rom = MagicMock()
    result_rom.first.return_value = (5, 100)
    result_checklist = MagicMock()
    result_checklist.all.return_value = [
        (safra_ativa_1.id, safra_ativa_1.status, 2),
        (safra_ativa_2.id, safra_ativa_2.status, 0),
    ]
    result_nde = MagicMock()
    result_nde.all.return_value = []
    reg1 = SimpleNamespace(
        safra_id=safra_ativa_1.id,
        escala=SimpleNamespace(codigo="V1", nome="Vegetativo"),
        data_observacao=date.today(),
    )
    reg2 = SimpleNamespace(
        safra_id=safra_ativa_2.id,
        escala=SimpleNamespace(codigo="V2", nome="Vegetativo 2"),
        data_observacao=date.today(),
    )
    result_fen = MagicMock()
    result_fen.scalars.return_value.all.return_value = [reg1, reg2]

    session.execute.side_effect = [
        result_safras,
        result_area,
        result_custo,
        result_meta,
        result_rom,
        result_checklist,
        result_nde,
        result_fen,
    ]

    resumo = await svc.resumo()

    assert session.execute.await_count == 8
    assert resumo["kpis"]["total_safras_ativas"] == 2
    assert resumo["kpis"]["total_alertas"] == 1
    assert resumo["alertas_checklist"] == [
        {
            "safra_id": str(safra_ativa_1.id),
            "safra": "Soja 2025/2026",
            "fase": "PLANTIO",
            "pendentes": 2,
            "severidade": "AVISO",
        }
    ]
