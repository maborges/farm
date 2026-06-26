from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from campo import router as campo_router
from campo.schemas import (
    SyncPushItem,
    SyncPushRequest,
    TarefaProgramadaInvalidarRequest,
    TarefaProgramadaUpdate,
)
from pecuaria.services.manejo_sync_service import ManejoSyncResult, ManejoSyncService


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0
        self.refreshed: list[object] = []
        self.task: object | None = None

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def refresh(self, obj: object) -> None:
        self.refreshed.append(obj)

    async def get(self, *args: object, **kwargs: object) -> object | None:  # noqa: ARG002
        return self.task


def _make_task() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        module="pecuaria",
        type="VACINACAO",
        client_id=str(uuid.uuid4()),
        status_execucao="CONCLUIDA",
        dados={"sync_pecuaria": {"status": "OK", "erros": []}},
    )


@pytest.mark.asyncio
async def test_invalidar_tarefa_publica_evento_pos_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    task = _make_task()
    session.task = task

    class StubService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def invalidar(self, tarefa_id: uuid.UUID, motivo: str) -> object:  # noqa: ARG002
            return task

    captured: dict[str, Any] = {}

    async def publish_spy(event, session=None, logger_context=None):  # noqa: ANN001
        captured["event"] = event
        captured["session_commits"] = session.commit_count
        captured["logger_context"] = logger_context
        return None

    monkeypatch.setattr(campo_router, "TarefaProgramadaService", StubService)
    monkeypatch.setattr(campo_router, "publish_domain_event_safe", publish_spy)

    result = await campo_router.invalidar_tarefa(
        tarefa_id=task.id,
        body=TarefaProgramadaInvalidarRequest(motivo="Status corrigido manualmente"),
        request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
        tenant_id=task.tenant_id,
        user_id=uuid.uuid4(),
        session=session,
    )

    assert result is task
    assert session.commit_count == 1
    event = captured["event"]
    assert event.event_type == "campo.tarefa.invalidada"
    assert event.entity_type == "tarefa_campo"
    assert event.entity_id == task.id
    assert event.tenant_id == task.tenant_id
    assert event.unidade_produtiva_id == task.unidade_produtiva_id
    assert event.metadata["status_novo"] == "INVALIDADA"
    assert captured["session_commits"] == 1


@pytest.mark.asyncio
async def test_update_sem_transicao_relevante_nao_publica_evento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    task = _make_task()

    class StubService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def atualizar(self, tarefa_id: uuid.UUID, data: object) -> object:  # noqa: ARG002
            return task

    publish_spy = AsyncMock()
    monkeypatch.setattr(campo_router, "TarefaProgramadaService", StubService)
    monkeypatch.setattr(campo_router, "publish_domain_event_safe", publish_spy)

    result = await campo_router.atualizar_tarefa_programada(
        tarefa_id=task.id,
        data=TarefaProgramadaUpdate(),
        tenant_id=task.tenant_id,
        session=session,
    )

    assert result is task
    publish_spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_failure_publica_evento(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    task = _make_task()
    session.task = task

    fake_device = SimpleNamespace(id=uuid.uuid4(), tenant_id=task.tenant_id)

    class StubSyncService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            self.tarefas_pecuaria_sync = [task.id]

        async def push(self, items: list[object]) -> list[dict[str, object]]:  # noqa: ARG002
            return [{"local_id": "1", "status": "UPDATED"}]

    class StubDispositivoService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def atualizar_last_sync(self, device_id: uuid.UUID) -> None:  # noqa: ARG002
            return None

    class StubManejoSyncService:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401, ARG002
            pass

        async def processar_tarefa_campo(self, tarefa_id: uuid.UUID) -> None:  # noqa: ARG002
            raise RuntimeError("sync failure")

    publish_spy = AsyncMock(side_effect=RuntimeError("publisher boom"))
    monkeypatch.setattr(campo_router, "_get_device_from_token", AsyncMock(return_value=fake_device))
    monkeypatch.setattr(campo_router, "SyncService", StubSyncService)
    monkeypatch.setattr(campo_router, "DispositivoService", StubDispositivoService)
    monkeypatch.setattr(
        "pecuaria.services.manejo_sync_service.ManejoSyncService",
        StubManejoSyncService,
    )
    monkeypatch.setattr("events.helpers.publish_domain_event", publish_spy)

    response = await campo_router.sync_push(
        request=SimpleNamespace(),
        body=SyncPushRequest(
            device_id=fake_device.id,
            items=[
                SyncPushItem(
                    local_id="1",
                    operation="UPDATE",
                    entity_type="TarefaCampo",
                    payload={},
                    client_created_at=datetime.utcnow(),
                    client_updated_at=datetime.utcnow(),
                )
            ],
        ),
        session=session,
    )

    assert response.results[0].status == "UPDATED"
    assert session.commit_count >= 2
    assert publish_spy.await_count == 1
    assert publish_spy.await_args is not None
    event = publish_spy.await_args.args[0]
    assert event.event_type == "campo.sync.falha"
    assert event.entity_id == task.id


@pytest.mark.asyncio
async def test_sync_failure_result_publica_evento(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    tarefa = _make_task()
    tarefa.tenant_id = tenant_id
    tarefa.unidade_produtiva_id = unidade_produtiva_id
    tarefa.module = "pecuaria"
    tarefa.type = "VACINACAO"
    tarefa.status_execucao = "CONCLUIDA"
    tarefa.status = "CONCLUIDA"

    service = ManejoSyncService(session, tenant_id)
    monkeypatch.setattr(service, "_buscar_tarefa", AsyncMock(return_value=tarefa))
    monkeypatch.setattr(
        service,
        "_processar_vacinacao",
        AsyncMock(
            return_value=ManejoSyncResult(
                status="ERROR",
                total_recebido=1,
                total_processado=0,
                total_ignorados=0,
                erros=["Falha ao processar lote"],
                tarefa_campo_id=tarefa.id,
            )
        ),
    )
    persist_spy = AsyncMock()
    monkeypatch.setattr(service, "_persistir_resultado", persist_spy)
    publish_spy = AsyncMock(
        return_value=SimpleNamespace(errors=0, executions=[], warnings=0)
    )
    monkeypatch.setattr("events.helpers.publish_domain_event", publish_spy)

    result = await service.processar_tarefa_campo(tarefa.id)

    assert result.status == "ERROR"
    assert persist_spy.await_count == 1
    assert publish_spy.await_count == 1
    event = publish_spy.await_args.args[0]
    assert event.event_type == "campo.sync.falha"
    assert event.entity_id == tarefa.id
    assert event.tenant_id == tenant_id
    assert event.unidade_produtiva_id == unidade_produtiva_id


def test_campo_nao_importa_dispatcher_diretamente() -> None:
    source = Path(campo_router.__file__).read_text(encoding="utf-8")
    assert "AlertDispatcherService" not in source
    assert "dispatch_alert_event" not in source
