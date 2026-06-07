from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy import text

from campo.models import DispositivoCampo, TarefaCampo
from campo.schemas import SyncPushItem, TarefaProgramadaCreate
from campo.service import SyncService, TarefaProgramadaService
from core.models.auth import Usuario


pytestmark = pytest.mark.asyncio


async def test_tarefa_programada_preenche_client_timestamps(session, tenant_id):
    suffix = uuid.uuid4().hex[:8]
    user = Usuario(
        id=uuid.uuid4(),
        email=f"operador-{suffix}@teste.com",
        username=f"operador_teste_{suffix}",
        nome_completo="Operador Teste",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": "12345678901"},
    )
    session.add(user)
    await session.commit()

    service = TarefaProgramadaService(session, tenant_id, user.id)
    tarefa = await service.criar(
        TarefaProgramadaCreate(
            titulo="Verificar limpeza do talhão",
            type="APLICACAO_DEFENSIVO",
            module="agricola",
            data_programada=date(2026, 5, 28),
            prioridade="BAIXA",
            unidade_produtiva_id=uuid.uuid4(),
            dados={"observacao": "Teste"},
        )
    )
    await session.commit()

    assert tarefa.client_created_at is not None
    assert tarefa.client_updated_at is not None
    assert tarefa.client_created_at == tarefa.client_updated_at


async def test_sync_push_update_aceita_client_updated_at_com_timezone(session, tenant_id):
    suffix = uuid.uuid4().hex[:8]
    user = Usuario(
        id=uuid.uuid4(),
        email=f"operador-push-{suffix}@teste.com",
        username=f"operador_push_{suffix}",
        nome_completo="Operador Push",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": "12345678901"},
    )
    session.add(user)
    await session.commit()

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[uuid.uuid4()],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=device.id,
        user_id=user.id,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao="PENDENTE",
        titulo="Pulverização",
        data_programada=date.today(),
        prioridade="NORMAL",
        type="APLICACAO_DEFENSIVO",
        module="agricola",
        unidade_produtiva_id=uuid.uuid4(),
        status="PENDENTE",
        dados={},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(device)
    session.add(task)
    await session.commit()

    service = SyncService(session, tenant_id, device)
    item = SyncPushItem(
        local_id=str(task.id),
        operation="UPDATE",
        entity_type="task",
        server_id=str(task.id),
        payload={
            "status": "PENDENTE",
            "dados": {},
            "status_execucao": "EM_EXECUCAO",
        },
        client_created_at=datetime.now(timezone.utc),
        client_updated_at=datetime.now(timezone.utc),
    )

    result = await service._process_item(item)

    assert result.status == "UPDATED"
