import pytest
import uuid
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError
from pecuaria.animal.models import Animal, EventoAnimal
from pecuaria.schemas.pesagem_schema import PesagemCreate
from pecuaria.services.pesagem_service import PesagemService
import campo.models  # For SQLAlchemy to discover 'campo_tarefas' for the FK

pytestmark = pytest.mark.asyncio

async def test_pesagem_service_registrar(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = PesagemService(session, tenant_id)
    
    # Setup
    animal_id = uuid.uuid4()
    animal = Animal(
        id=animal_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco="PESO-001",
        data_entrada=date.today(),
        peso_atual_kg=100.0,
        data_ultima_pesagem=date.today() - timedelta(days=30)
    )
    session.add(animal)
    await session.commit()

    # Registrar
    hoje = date.today()
    payload = PesagemCreate(
        data_evento=hoje,
        peso_kg=130.0,
        observacoes="Pesagem teste"
    )
    
    pesagem = await svc.registrar_pesagem(animal_id, payload)
    
    assert pesagem.peso_kg == 130.0
    assert pesagem.data_evento == hoje
    assert pesagem.gmd_periodo is None # Primeira pesagem registrada via sistema

    await session.refresh(animal)
    assert animal.peso_atual_kg == 130.0
    assert animal.data_ultima_pesagem == hoje


async def test_pesagem_service_listar_gmd(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = PesagemService(session, tenant_id)
    
    animal_id = uuid.uuid4()
    animal = Animal(
        id=animal_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco="PESO-002",
        data_entrada=date.today()
    )
    session.add(animal)
    
    hoje = date.today()
    evt1 = EventoAnimal(tenant_id=tenant_id, animal_id=animal_id, tipo="PESAGEM", data_evento=hoje - timedelta(days=60), peso_kg=100.0)
    evt2 = EventoAnimal(tenant_id=tenant_id, animal_id=animal_id, tipo="PESAGEM", data_evento=hoje - timedelta(days=30), peso_kg=130.0)
    evt3 = EventoAnimal(tenant_id=tenant_id, animal_id=animal_id, tipo="PESAGEM", data_evento=hoje, peso_kg=160.0)
    
    session.add_all([evt1, evt2, evt3])
    await session.commit()

    pesagens = await svc.listar_pesagens(animal_id)
    assert len(pesagens) == 3
    
    # Ordem decrescente
    assert pesagens[0].peso_kg == 160.0
    assert pesagens[0].dias_desde_anterior == 30
    assert pesagens[0].gmd_periodo == 1.0

    assert pesagens[1].peso_kg == 130.0
    assert pesagens[1].gmd_periodo == 1.0

    assert pesagens[2].peso_kg == 100.0
    assert pesagens[2].gmd_periodo is None


async def test_pesagem_service_isolamento(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = PesagemService(session, tenant_id)
    
    # Animal do OUTRO tenant
    animal_id = uuid.uuid4()
    animal = Animal(
        id=animal_id,
        tenant_id=outro_tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco="ISOL-001",
        data_entrada=date.today()
    )
    session.add(animal)
    await session.commit()

    payload = PesagemCreate(data_evento=date.today(), peso_kg=100.0)
    
    with pytest.raises(HTTPException) as exc:
        await svc.registrar_pesagem(animal_id, payload)
    
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await svc.listar_pesagens(animal_id)
    
    assert exc.value.status_code == 404

from sqlalchemy.exc import IntegrityError

async def test_pesagem_service_idempotencia_tarefa_campo(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = PesagemService(session, tenant_id)
    
    animal_id = uuid.uuid4()
    animal = Animal(
        id=animal_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco="IDEM-001",
        data_entrada=date.today()
    )
    session.add(animal)
    await session.commit()

    tarefa_id = uuid.uuid4()
    
    # Payload com a tarefa
    payload = PesagemCreate(
        data_evento=date.today(), 
        peso_kg=120.0,
        tarefa_campo_id=tarefa_id
    )
    
    # Primeira inserção: sucesso
    await svc.registrar_pesagem(animal_id, payload)
    
    # Segunda inserção idêntica: deve falhar por violação de integridade única parcial
    with pytest.raises(IntegrityError):
        await svc.registrar_pesagem(animal_id, payload)
