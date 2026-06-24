import pytest
from httpx import AsyncClient
from datetime import datetime, date

from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal


import uuid

import uuid
from tests.integration.conftest import _gerar_token

@pytest.mark.asyncio
async def test_list_sync_status_filters_and_pagination(client: AsyncClient, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, session):
    token_admin = _gerar_token(tenant_id, ["CORE", "P1_REBANHO", "A2_CAMPO"])
    user_id = uuid.uuid4()
    # 1. Create a few TarefasCampo
    t1 = TarefaCampo(
        tenant_id=tenant_id,
        user_id=user_id,
        client_id=str(uuid.uuid4()),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        type="PESAGEM",
        module="pecuaria",
        status_execucao="CONCLUIDA",
        concluida_em=datetime.utcnow(),
        dados={
            "animais": [{"animal_id": "11111111-1111-1111-1111-111111111111", "peso_kg": 200}],
            "sync_pecuaria": {
                "status": "SUCCESS",
                "total_processado": 1,
                "erros": [],
                "data_processamento": datetime.utcnow().isoformat()
            }
        }
    )
    
    t2 = TarefaCampo(
        tenant_id=tenant_id,
        user_id=user_id,
        client_id=str(uuid.uuid4()),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        type="PESAGEM",
        module="pecuaria",
        status_execucao="CONCLUIDA",
        concluida_em=datetime.utcnow(),
        dados={
            "sync_pecuaria": {
                "status": "ERROR",
                "total_processado": 0,
                "erros": ["Animal não encontrado"],
                "data_processamento": datetime.utcnow().isoformat()
            }
        }
    )
    
    t3 = TarefaCampo(
        tenant_id=tenant_id,
        user_id=user_id,
        client_id=str(uuid.uuid4()),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        type="VACINACAO",
        module="pecuaria",
        status_execucao="CONCLUIDA",
        concluida_em=datetime.utcnow(),
        dados={} # PENDENTE
    )

    t4 = TarefaCampo(
        tenant_id=tenant_id,
        user_id=user_id,
        client_id=str(uuid.uuid4()),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        type="PESAGEM",
        module="agricola", # Agricola, should not be returned!
        status_execucao="CONCLUIDA",
        concluida_em=datetime.utcnow(),
        dados={}
    )

    session.add_all([t1, t2, t3, t4])
    await session.commit()
    await session.refresh(t1)
    await session.refresh(t2)
    await session.refresh(t3)
    await session.refresh(t4)

    headers = {"Authorization": f"Bearer {token_admin}"}
    
    # List all pecuaria tasks
    response = await client.get("/api/v1/pecuaria/campo/sync-status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3 # t1, t2, t3 (plus any existing from other tests)
    
    # Ensure agricola is not there
    ids = [t["tarefa_campo_id"] for t in data["items"]]
    assert str(t4.id) not in ids
    assert str(t1.id) in ids
    assert str(t2.id) in ids
    assert str(t3.id) in ids

    # Filter by SUCCESS
    response = await client.get("/api/v1/pecuaria/campo/sync-status?status_processamento=SUCCESS", headers=headers)
    assert response.status_code == 200
    data = response.json()
    ids = [t["tarefa_campo_id"] for t in data["items"]]
    assert str(t1.id) in ids
    assert str(t2.id) not in ids
    
    # Filter by ERROR
    response = await client.get("/api/v1/pecuaria/campo/sync-status?status_processamento=ERROR", headers=headers)
    assert response.status_code == 200
    data = response.json()
    ids = [t["tarefa_campo_id"] for t in data["items"]]
    assert str(t2.id) in ids
    assert str(t1.id) not in ids

    # Filter by PENDENTE
    response = await client.get("/api/v1/pecuaria/campo/sync-status?status_processamento=PENDENTE", headers=headers)
    assert response.status_code == 200
    data = response.json()
    ids = [t["tarefa_campo_id"] for t in data["items"]]
    assert str(t3.id) in ids

    # Filter by type
    response = await client.get("/api/v1/pecuaria/campo/sync-status?type=VACINACAO", headers=headers)
    assert response.status_code == 200
    data = response.json()
    ids = [t["tarefa_campo_id"] for t in data["items"]]
    assert str(t3.id) in ids
    assert str(t1.id) not in ids

@pytest.mark.asyncio
async def test_reprocessar_tarefa(client: AsyncClient, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, session):
    token_admin = _gerar_token(tenant_id, ["CORE", "P1_REBANHO", "A2_CAMPO"])
    user_id = uuid.uuid4()
    # Create animal
    a1 = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        numero_brinco="TEST-REPROCESS",
        sexo="M",
        raca=None,
        categoria="BOI"
    )
    session.add(a1)
    await session.commit()

    # Create task WITH ERROR
    t1 = TarefaCampo(
        tenant_id=tenant_id,
        user_id=user_id,
        client_id=str(uuid.uuid4()),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
        type="PESAGEM",
        module="pecuaria",
        status_execucao="CONCLUIDA",
        dados={
            "animais": [{"animal_id": str(a1.id), "peso_kg": 350}],
            "sync_pecuaria": {
                "status": "ERROR",
                "total_processado": 0,
                "erros": ["Some fake previous error"]
            }
        }
    )
    session.add(t1)
    await session.commit()
    await session.refresh(t1)

    headers = {"Authorization": f"Bearer {token_admin}"}
    
    # Reprocess
    resp = await client.post(f"/api/v1/pecuaria/campo/tarefas/{t1.id}/processar", headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["total_processado"] == 1

    # Ensure it updated the sync_pecuaria on TarefaCampo
    await session.refresh(t1)
    assert t1.dados["sync_pecuaria"]["status"] == "SUCCESS"
    assert t1.dados["sync_pecuaria"]["total_processado"] == 1
    assert t1.dados["sync_pecuaria"]["erros"] == []
