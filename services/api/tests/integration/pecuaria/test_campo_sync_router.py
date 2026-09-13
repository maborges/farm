import pytest
import uuid
from httpx import AsyncClient
from datetime import date, datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal
from core.database import async_session_maker

pytestmark = pytest.mark.asyncio

from tests.integration.conftest import _gerar_token

@pytest.fixture
def my_headers_admin(tenant_id: uuid.UUID):
    token = _gerar_token(tenant_id, [
        "CORE",
        "P1_REBANHO",
        "A2_CAMPO"
    ])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(uuid.uuid4())
    }

async def _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="100", peso=100.0):
    a = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco=brinc,
        data_entrada=date.today(),
        peso_atual_kg=peso
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a

async def _criar_tarefa(session, tenant_id, module="pecuaria", type_="PESAGEM", status="CONCLUIDA", status_execucao="CONCLUIDA", dados=None):
    if dados is None:
        dados = {}
    
    t = TarefaCampo(
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        module=module,
        type=type_,
        status=status,
        status_execucao=status_execucao,
        client_id=str(uuid.uuid4()),
        dados=dados,
        origem="MANUAL",
        prioridade="NORMAL",
        localizacao_status="INDISPONIVEL",
        concluida_em=datetime.now(),
        client_created_at=datetime.now(),
        client_updated_at=datetime.now()
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def test_processar_tarefa_valida(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="001", peso=100.0)
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    response = await client.post(
        f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar",
        headers=my_headers_admin
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["total_recebido"] == 1
    assert data["total_processado"] == 1
    assert data["total_ignorados"] == 0

    # Verify side effects
    await session.refresh(a1)
    assert a1.peso_atual_kg == 150.0

    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id)
    evts = (await session.execute(stmt)).scalars().all()
    assert len(evts) == 1
    assert evts[0].tipo == "PESAGEM"


async def test_reprocessar_tarefa_idempotente(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="002", peso=100.0)
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    # First call
    res1 = await client.post(f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar", headers=my_headers_admin)
    assert res1.status_code == 200

    # Second call (Idempotency)
    res2 = await client.post(f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar", headers=my_headers_admin)
    assert res2.status_code == 200
    data = res2.json()
    assert data["status"] == "SUCCESS"
    assert data["total_processado"] == 0
    assert data["total_ignorados"] == 1


async def test_bloquear_tarefa_outro_tenant(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, outro_tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    unidade_produtiva_outro_tenant = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:tenant_id, 'Tenant B Sync', :documento, true, 0, 10240, 'pt-BR', NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"tenant_id": str(outro_tenant_id), "documento": outro_tenant_id.hex[:11]},
    )
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda B Sync', true, NOW(), NOW())
            """
        ),
        {"id": str(unidade_produtiva_outro_tenant), "tenant_id": str(outro_tenant_id)},
    )
    await session.commit()

    a1 = await _criar_animal(session, outro_tenant_id, unidade_produtiva_outro_tenant, brinc="003", peso=100.0)
    tarefa = await _criar_tarefa(session, outro_tenant_id, dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    response = await client.post(
        f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar",
        headers=my_headers_admin  # This user belongs to tenant_id, not outro_tenant_id
    )

    # Note: Our router converts this specific "ignored" to 404
    assert response.status_code == 404
    assert "não encontrada ou não pertence ao tenant" in response.json()["detail"]


async def test_rejeitar_modulo_agricola(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="004")
    tarefa = await _criar_tarefa(session, tenant_id, module="agricola", dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    response = await client.post(f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar", headers=my_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "IGNORED"
    assert any("ignorado" in e.lower() for e in data["erros"])


async def test_rejeitar_status_pendente(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="005")
    tarefa = await _criar_tarefa(session, tenant_id, status="PENDENTE", status_execucao="PENDENTE", dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    response = await client.post(f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar", headers=my_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "IGNORED"
    assert any("concluida" in e.lower() for e in data["erros"])


async def test_retornar_erro_payload_invalido(
    client: AsyncClient, my_headers_admin: dict, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
):
    # Payload has negative weight
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="006")
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": -10.0}]
    })

    response = await client.post(f"/api/v1/pecuaria/campo/tarefas/{tarefa.id}/processar", headers=my_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ERROR"
    assert any("inválido" in e.lower() for e in data["erros"])
    
    # Event count must be zero
    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id)
    evts = (await session.execute(stmt)).scalars().all()
    assert len(evts) == 0
