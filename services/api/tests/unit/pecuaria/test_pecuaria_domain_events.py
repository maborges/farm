from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

import pecuaria.services.manejo_sync_service as manejo_sync_module
from alert_engine.models import Domain
from events import DomainEvent
from pecuaria.routers import manejos as pecuaria_manejos
from pecuaria.schemas.manejo_planejamento_schema import (
    ManejoPlanejamentoCreate,
    ManejoPlanejamentoLoteResumo,
    ManejoPlanejamentoOperadorResumo,
    ManejoPlanejamentoResponse,
)
from pecuaria.services.manejo_sync_service import ManejoSyncService


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0
        self.lote: object | None = None

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def get(self, *args: object, **kwargs: object) -> object | None:  # noqa: ARG002
        return self.lote

    def add(self, obj: object) -> None:  # noqa: D401, ARG002
        return None

    async def flush(self) -> None:
        return None

    async def refresh(self, obj: object) -> None:
        return None

    def add_all(self, objs: list[object]) -> None:  # noqa: D401, ARG002
        return None


@pytest.mark.asyncio
async def test_planejamento_sanitario_publica_evento(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    tenant_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session.lote = SimpleNamespace(id=lote_id, unidade_produtiva_id=unidade_produtiva_id)
    planejamento = ManejoPlanejamentoResponse(
        tarefa_campo_id=uuid.uuid4(),
        tipo="VACINACAO",
        lote=ManejoPlanejamentoLoteResumo(id=lote_id, identificacao="Lote 1"),
        area_id=None,
        operador=ManejoPlanejamentoOperadorResumo(id=uuid.uuid4(), nome_exibicao="Operador"),
        status="PENDENTE",
        origem="PROGRAMADA",
        data_programada=date(2026, 6, 25),
        quantidade_animais=2,
        observacoes="Planejamento",
        animais=[],
    )

    class StubService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def planejar(self, payload: ManejoPlanejamentoCreate, user_id: uuid.UUID) -> object:  # noqa: ARG002
            return planejamento

    captured: dict[str, Any] = {}

    async def publish_spy(event: DomainEvent, session=None, logger_context=None, commit=None):  # noqa: ANN001
        captured["event"] = event
        captured["session_commits"] = session.commit_count
        captured["commit"] = commit
        return None

    monkeypatch.setattr(pecuaria_manejos, "ManejoPlanejamentoService", StubService)
    monkeypatch.setattr(pecuaria_manejos, "publish_domain_event_safe", publish_spy)

    result = await pecuaria_manejos.planejar_manejo(
        payload=ManejoPlanejamentoCreate(
            tipo="VACINACAO",
            lote_id=lote_id,
            data_programada=date(2026, 6, 25),
            produto_id=uuid.uuid4(),
            dose=1.0,
            unidade_medida="ML",
        ),
        tenant_id=tenant_id,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        db=session,
    )

    assert result is planejamento
    assert session.commit_count == 1
    event = captured["event"]
    assert event.event_type == "pecuaria.planejamento.sanitario.atualizado"
    assert event.domain == Domain.LIVESTOCK
    assert event.unidade_produtiva_id == unidade_produtiva_id
    assert event.tenant_id == tenant_id
    assert event.entity_type == "planejamento_sanitario"
    assert event.entity_id == planejamento.tarefa_campo_id
    assert event.correlation_id is None
    assert event.causation_id is None
    assert event.metadata["lote_id"] == str(lote_id)
    assert set(event.metadata).issubset(
        {
            "tipo",
            "lote_id",
            "lote_identificacao",
            "operador_id",
            "produto_id",
            "dose",
            "unidade_medida",
            "data_programada",
            "quantidade_animais",
            "observacoes",
        }
    )
    assert captured["session_commits"] == 0
    assert captured["commit"] is False


@pytest.mark.asyncio
async def test_vacinacao_registrada_publica_evento(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    animal_id = uuid.uuid4()
    tarefa = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        client_id=str(uuid.uuid4()),
        concluida_em=datetime(2026, 6, 25),
        dados={
            "lote_id": str(uuid.uuid4()),
            "animais_ids": [str(animal_id), str(uuid.uuid4())],
            "produto_id": str(uuid.uuid4()),
            "dose": 1.5,
            "unidade_medida": "ML",
            "via_aplicacao": "IM",
            "data_evento": "2026-06-25",
        },
    )
    produto = SimpleNamespace(id=uuid.uuid4(), nome="Vacina X", unidade_medida="ML")

    service = ManejoSyncService(session, tenant_id)
    monkeypatch.setattr(
        service,
        "_normalizar_animais_ids",
        lambda value: [animal_id, uuid.uuid4()],
    )
    monkeypatch.setattr(service, "_validar_lote_vacinacao", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_validar_produto_vacina", AsyncMock(return_value=produto))
    monkeypatch.setattr(service, "_validar_dose_vacinacao", lambda value: 1.5)
    monkeypatch.setattr(
        service,
        "_buscar_animais",
        AsyncMock(return_value={animal_id: SimpleNamespace(id=animal_id)}),
    )
    monkeypatch.setattr(
        service,
        "_validar_animais_no_lote",
        lambda animais_banco, animal_ids, lote_id: [],
    )
    monkeypatch.setattr(service, "_animais_ja_processados", AsyncMock(return_value=set()))
    monkeypatch.setattr(service, "_montar_eventos_vacinacao", lambda *args, **kwargs: [])
    monkeypatch.setattr(service, "_registrar_estoque_vacinacao", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_registrar_custo_vacinacao", AsyncMock(return_value=None))

    enqueue_spy = AsyncMock(
        return_value=SimpleNamespace(errors=0, executions=[], warnings=0)
    )
    monkeypatch.setattr("events.helpers.enqueue_domain_event", enqueue_spy)

    result = await service._processar_vacinacao(tarefa)

    assert result.status == "SUCCESS"
    assert session.commit_count == 1
    assert enqueue_spy.await_count == 1
    assert enqueue_spy.await_args is not None
    assert enqueue_spy.await_args.kwargs["commit"] is False
    event = enqueue_spy.await_args.args[0]
    assert event.event_type == "pecuaria.vacinacao.registrada"
    assert event.entity_type == "tarefa_campo"
    assert event.tenant_id == tenant_id
    assert event.unidade_produtiva_id == unidade_produtiva_id
    assert event.entity_id == tarefa.id
    assert event.correlation_id == uuid.UUID(tarefa.client_id)
    assert event.causation_id is None
    assert set(event.metadata).issubset(
        {
            "tarefa_campo_id",
            "lote_id",
            "animal_id",
            "animal_count",
            "produto_id",
            "produto_nome",
            "dose",
            "unidade_medida",
            "via_aplicacao",
            "data_aplicacao",
        }
    )
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_publicacao_falha_nao_quebra_fluxo_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    tenant_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session.lote = SimpleNamespace(id=lote_id, unidade_produtiva_id=unidade_produtiva_id)
    planejamento = ManejoPlanejamentoResponse(
        tarefa_campo_id=uuid.uuid4(),
        tipo="VACINACAO",
        lote=ManejoPlanejamentoLoteResumo(id=lote_id, identificacao="Lote 2"),
        area_id=None,
        operador=None,
        status="PENDENTE",
        origem="PROGRAMADA",
        data_programada=date(2026, 6, 25),
        quantidade_animais=1,
        observacoes=None,
        animais=[],
    )

    class StubService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def planejar(self, payload: ManejoPlanejamentoCreate, user_id: uuid.UUID) -> object:  # noqa: ARG002
            return planejamento

    monkeypatch.setattr(pecuaria_manejos, "ManejoPlanejamentoService", StubService)
    monkeypatch.setattr(
        "events.helpers.enqueue_domain_event",
        AsyncMock(side_effect=RuntimeError("publisher boom")),
    )

    result = await pecuaria_manejos.planejar_manejo(
        payload=ManejoPlanejamentoCreate(
            tipo="VACINACAO",
            lote_id=lote_id,
            data_programada=date(2026, 6, 25),
            produto_id=uuid.uuid4(),
            dose=1.0,
            unidade_medida="ML",
        ),
        tenant_id=tenant_id,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        db=session,
    )

    assert result is planejamento
    assert session.commit_count == 1


def test_pecuaria_nao_importa_dispatcher_diretamente() -> None:
    source_router = Path(pecuaria_manejos.__file__).read_text(encoding="utf-8")
    source_service = Path(manejo_sync_module.__file__).read_text(encoding="utf-8")
    assert "AlertDispatcherService" not in source_router
    assert "dispatch_alert_event" not in source_router
    assert "AlertDispatcherService" not in source_service
    assert "dispatch_alert_event" not in source_service
