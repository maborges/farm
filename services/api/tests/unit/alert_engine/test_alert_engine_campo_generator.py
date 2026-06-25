from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from alert_engine.generators import CampoAlertGenerator
from alert_engine.models import AlertLifecycleEvent, AlertStatus, OperationalAlert
from alert_engine.service import AlertLifecycleService
from campo.models import TarefaCampo


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _ensure_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tenants (
                id, nome, documento, ativo, storage_usado_mb, storage_limite_mb,
                idioma_padrao, created_at, updated_at
            )
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(tenant_id),
            "nome": f"Tenant {tenant_id.hex[:8]}",
            "documento": tenant_id.hex[:11],
        },
    )
    await session.commit()


def _task(
    tenant_id: uuid.UUID,
    *,
    task_id: uuid.UUID | None = None,
    status_execucao: str = "PENDENTE",
    data_programada: date | None = None,
    module: str = "pecuaria",
    task_type: str = "VACINACAO",
    dados: dict | None = None,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> TarefaCampo:
    return TarefaCampo(
        id=task_id or uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=None,
        user_id=ADMIN_USER_ID,
        operador_id=None,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao=status_execucao,
        titulo="Tarefa de Campo",
        data_programada=data_programada,
        prioridade="NORMAL",
        type=task_type,
        module=module,
        unidade_produtiva_id=unidade_produtiva_id,
        area_rural_id=None,
        lote_id=None,
        status=status_execucao,
        dados=dados or {},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        latitude=None,
        longitude=None,
        iniciada_em=None,
        concluida_em=datetime.utcnow() if status_execucao == "CONCLUIDA" else None,
        invalidado_em=datetime.utcnow() if status_execucao == "INVALIDADA" else None,
        invalidado_por=ADMIN_USER_ID if status_execucao == "INVALIDADA" else None,
        motivo_invalidacao="Motivo operacional" if status_execucao == "INVALIDADA" else None,
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )


async def _count_alerts(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(OperationalAlert.id)).where(OperationalAlert.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _count_lifecycle_events(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(AlertLifecycleEvent.id)).where(AlertLifecycleEvent.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


@pytest.mark.asyncio
async def test_campo_generator_creates_overdue_alert_and_summary_reflects_it(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task = _task(tenant, data_programada=date.today() - timedelta(days=2))
    session.add(task)
    await session.commit()

    generator = CampoAlertGenerator(session, tenant)
    result = await generator.gerar_alertas_campo()
    summary = await AlertLifecycleService(session, tenant).get_alert_summary()

    alert = (
        await session.execute(select(OperationalAlert).where(OperationalAlert.dedupe_key == f"campo:tarefa_atrasada:{task.id}"))
    ).scalar_one()

    assert result.tarefas_atrasadas == 1
    assert result.total_alertas == 1
    assert alert.source_type == "CAMPO_TAREFA_ATRASADA"
    assert alert.source_id == str(task.id)
    assert alert.domain == "FIELD"
    assert alert.status == AlertStatus.OPEN.value
    assert summary.total_open == 1
    assert summary.top_alerts[0].dedupe_key == alert.dedupe_key
    assert await _count_lifecycle_events(session, tenant) == 1


@pytest.mark.asyncio
async def test_campo_generator_is_idempotent_for_active_overdue_alert(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task = _task(tenant, data_programada=date.today() - timedelta(days=1))
    session.add(task)
    await session.commit()

    generator = CampoAlertGenerator(session, tenant)
    first = await generator.gerar_alertas_campo()
    second = await generator.gerar_alertas_campo()

    assert first.tarefas_atrasadas == 1
    assert second.tarefas_atrasadas == 1
    assert await _count_alerts(session, tenant) == 1
    assert await _count_lifecycle_events(session, tenant) == 1


@pytest.mark.asyncio
async def test_completed_task_does_not_generate_overdue_alert(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task = _task(tenant, status_execucao="CONCLUIDA", data_programada=date.today() - timedelta(days=1))
    session.add(task)
    await session.commit()

    result = await CampoAlertGenerator(session, tenant).gerar_alertas_campo()

    assert result.tarefas_atrasadas == 0
    assert await _count_alerts(session, tenant) == 0


@pytest.mark.asyncio
async def test_invalidated_task_is_only_marked_as_invalid(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task = _task(
        tenant,
        status_execucao="INVALIDADA",
        data_programada=date.today() - timedelta(days=1),
        dados={"motivo": "dados inconsistentes"},
    )
    session.add(task)
    await session.commit()

    result = await CampoAlertGenerator(session, tenant).gerar_alertas_campo()
    alert = (
        await session.execute(select(OperationalAlert).where(OperationalAlert.dedupe_key == f"campo:tarefa_invalida:{task.id}"))
    ).scalar_one()

    assert result.tarefas_invalidas == 1
    assert result.tarefas_atrasadas == 0
    assert result.total_alertas == 1
    assert await _count_alerts(session, tenant) == 1
    assert alert.severity == "CRITICAL"
    assert alert.source_type == "CAMPO_TAREFA_INVALIDA"
    assert "Motivo" in alert.message


@pytest.mark.asyncio
async def test_sync_failure_generates_specific_alert(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task = _task(
        tenant,
        status_execucao="CONCLUIDA",
        task_type="VACINACAO",
        dados={
            "sync_pecuaria": {
                "status": "ERROR",
                "erros": ["Falha interna ao persistir resultado."],
                "data_processamento": datetime.utcnow().isoformat(),
            }
        },
    )
    session.add(task)
    await session.commit()

    result = await CampoAlertGenerator(session, tenant).gerar_alertas_campo()
    alert = (
        await session.execute(select(OperationalAlert).where(OperationalAlert.dedupe_key == f"campo:sync_falha:{task.id}"))
    ).scalar_one()

    assert result.sync_falhas == 1
    assert result.total_alertas == 1
    assert await _count_alerts(session, tenant) == 1
    assert alert.source_type == "CAMPO_SYNC_FALHA"
    assert alert.priority == "URGENT"
    assert "Falha de sincronização" in alert.title
    assert "Falha interna" in alert.message


@pytest.mark.asyncio
async def test_other_tenant_is_not_considered(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)

    session.add_all(
        [
            _task(tenant_a, data_programada=date.today() - timedelta(days=1)),
            _task(tenant_b, data_programada=date.today() - timedelta(days=1)),
        ]
    )
    await session.commit()

    result = await CampoAlertGenerator(session, tenant_a).gerar_alertas_campo()

    assert result.tarefas_atrasadas == 1
    assert await _count_alerts(session, tenant_a) == 1
    other_count = await _count_alerts(session, tenant_b)
    assert other_count == 0


@pytest.mark.asyncio
async def test_dedupe_uses_source_id_task_id(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    task_id = uuid.uuid4()
    session.add(_task(tenant, task_id=task_id, data_programada=date.today() - timedelta(days=1)))
    await session.commit()

    await CampoAlertGenerator(session, tenant).gerar_alertas_campo()
    alert = (
        await session.execute(select(OperationalAlert).where(OperationalAlert.dedupe_key == f"campo:tarefa_atrasada:{task_id}"))
    ).scalar_one()

    assert alert.source_id == str(task_id)
    assert alert.dedupe_key == f"campo:tarefa_atrasada:{task_id}"
