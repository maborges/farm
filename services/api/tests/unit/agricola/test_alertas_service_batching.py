from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from agricola.alertas.service import AlertasAgricolasService

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _make_service() -> tuple[AlertasAgricolasService, AsyncMock]:
    session = AsyncMock()
    tenant_id = uuid4()
    svc = AlertasAgricolasService(session, tenant_id)
    svc.notif_svc.criar_e_push = AsyncMock()
    return svc, session


async def test_verificar_fase_parada_usa_agregado_por_safra():
    svc, session = _make_service()
    safra_antiga = SimpleNamespace(id=uuid4(), cultura="Soja", ano_safra="2025/2026", status="PLANTIO")
    safra_recente = SimpleNamespace(id=uuid4(), cultura="Milho", ano_safra="2025/2026", status="PLANTIO")
    svc._safras_ativas = AsyncMock(return_value=[safra_antiga, safra_recente])

    result = MagicMock()
    result.all.return_value = [
        (safra_antiga.id, datetime.now(timezone.utc) - timedelta(days=11)),
        (safra_recente.id, datetime.now(timezone.utc) - timedelta(days=2)),
    ]
    session.execute.return_value = result

    total = await svc._verificar_fase_parada()

    assert session.execute.await_count == 1
    assert total == 1
    assert svc.notif_svc.criar_e_push.await_count == 1


async def test_verificar_fenologia_vencida_usa_agregado_por_safra():
    svc, session = _make_service()
    safra_antiga = SimpleNamespace(id=uuid4(), cultura="Soja", ano_safra="2025/2026", status="DESENVOLVIMENTO")
    safra_recente = SimpleNamespace(id=uuid4(), cultura="Milho", ano_safra="2025/2026", status="DESENVOLVIMENTO")

    result_safras = MagicMock()
    result_safras.scalars.return_value.all.return_value = [safra_antiga, safra_recente]
    result_fen = MagicMock()
    result_fen.all.return_value = [
        (safra_antiga.id, date.today() - timedelta(days=15)),
        (safra_recente.id, date.today() - timedelta(days=4)),
    ]
    session.execute.side_effect = [result_safras, result_fen]

    total = await svc._verificar_fenologia_vencida()

    assert session.execute.await_count == 2
    assert total == 1
    assert svc.notif_svc.criar_e_push.await_count == 1


async def test_verificar_checklist_pendente_usa_agregado_por_safra():
    svc, session = _make_service()
    safra_pendente = SimpleNamespace(id=uuid4(), cultura="Soja", ano_safra="2025/2026", status="PLANTIO")
    safra_ok = SimpleNamespace(id=uuid4(), cultura="Milho", ano_safra="2025/2026", status="PLANTIO")
    svc._safras_ativas = AsyncMock(return_value=[safra_pendente, safra_ok])

    result = MagicMock()
    result.all.return_value = [
        (safra_pendente.id, 2),
        (safra_ok.id, 0),
    ]
    session.execute.return_value = result

    total = await svc._verificar_checklist_pendente()

    assert session.execute.await_count == 1
    assert total == 1
    assert svc.notif_svc.criar_e_push.await_count == 1


async def test_detectar_devolucao_sem_movimento_original_consulta_itens_e_movimentos_em_lote():
    svc, session = _make_service()
    devolucao_problem = SimpleNamespace(id=uuid4(), pedido_id=uuid4())
    devolucao_ok = SimpleNamespace(id=uuid4(), pedido_id=uuid4())
    item_problem = SimpleNamespace(
        devolucao_id=devolucao_problem.id,
        lote_id=None,
        produto_id=uuid4(),
        deposito_origem_id=uuid4(),
    )
    item_ok = SimpleNamespace(
        devolucao_id=devolucao_ok.id,
        lote_id=uuid4(),
        produto_id=uuid4(),
        deposito_origem_id=uuid4(),
    )

    result_devolucoes = MagicMock()
    result_devolucoes.all.return_value = [
        (devolucao_problem.id, devolucao_problem.pedido_id),
        (devolucao_ok.id, devolucao_ok.pedido_id),
    ]
    result_itens = MagicMock()
    result_itens.scalars.return_value.all.return_value = [item_problem, item_ok]
    result_mov = MagicMock()
    result_mov.all.return_value = [
        (devolucao_ok.pedido_id, item_ok.produto_id, item_ok.deposito_origem_id, item_ok.lote_id),
    ]
    session.execute.side_effect = [result_devolucoes, result_itens, result_mov]

    finding = await svc._detectar_devolucao_sem_movimento_original()

    assert session.execute.await_count == 3
    assert finding is not None
    assert finding.total == 1
    assert finding.amostras == [str(devolucao_problem.id)]
