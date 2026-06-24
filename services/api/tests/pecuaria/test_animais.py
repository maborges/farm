import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.exceptions import EntityNotFoundError, TenantViolationError
from pecuaria.animal.models import Animal, SexoAnimal, CategoriaAnimal, EspecieAnimal, LoteAnimal
from pecuaria.schemas.animal_schema import AnimalCreate, AnimalUpdate, AnimalFilter
from pecuaria.services.animal_service import AnimalService

pytestmark = pytest.mark.asyncio

async def test_animal_service_create_and_get(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = AnimalService(session, tenant_id)
    
    payload = AnimalCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        numero_brinco="BR-001",
        nome="Estrela",
        sexo=SexoAnimal.FEMEA,
        categoria=CategoriaAnimal.VACA_CORTE,
        peso_atual_kg=450.0
    )
    
    # Criar
    animal = await svc.create(payload)
    assert animal.id is not None
    assert animal.numero_brinco == "BR-001"
    assert animal.tenant_id == tenant_id
    
    # Consultar
    fetched = await svc.get_or_fail(animal.id)
    assert fetched.nome == "Estrela"


async def test_animal_service_list_paginated_and_filters(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = AnimalService(session, tenant_id)
    
    await svc.create(AnimalCreate(unidade_produtiva_id=unidade_produtiva_id, numero_brinco="BR-002", sexo=SexoAnimal.MACHO))
    await svc.create(AnimalCreate(unidade_produtiva_id=unidade_produtiva_id, numero_brinco="BR-003", sexo=SexoAnimal.FEMEA))
    await svc.create(AnimalCreate(unidade_produtiva_id=unidade_produtiva_id, numero_sisbov="SIS-004", sexo=SexoAnimal.MACHO))
    
    # Lista tudo paginado
    items, total = await svc.list_paginated(0, 10, unidade_produtiva_id, AnimalFilter())
    assert total >= 3
    assert len(items) >= 3
    
    # Filtro de texto `q`
    items, total = await svc.list_paginated(0, 10, unidade_produtiva_id, AnimalFilter(q="SIS"))
    assert total == 1
    assert items[0].numero_sisbov == "SIS-004"
    
    # Filtro de enum
    items, total = await svc.list_paginated(0, 10, unidade_produtiva_id, AnimalFilter(sexo=SexoAnimal.FEMEA))
    # considerando que BR-003 + possíveis outros
    assert all(i.sexo == SexoAnimal.FEMEA for i in items)


async def test_animal_service_update_and_delete(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = AnimalService(session, tenant_id)
    
    animal = await svc.create(AnimalCreate(unidade_produtiva_id=unidade_produtiva_id, numero_brinco="DEL-001"))
    
    # Update
    updated = await svc.update(animal.id, AnimalUpdate(nome="Boi Zebu", peso_atual_kg=500.0))
    assert updated.nome == "Boi Zebu"
    assert updated.peso_atual_kg == 500.0
    
    # Delete
    await svc.hard_delete(animal.id)
    
    # Verifica que não existe mais
    with pytest.raises(EntityNotFoundError):
        await svc.get_or_fail(animal.id)


async def test_animal_service_tenant_isolation(session_a: AsyncSession, session_b: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc_a = AnimalService(session_a, tenant_id)
    svc_b = AnimalService(session_b, outro_tenant_id)
    
    animal_a = await svc_a.create(AnimalCreate(unidade_produtiva_id=unidade_produtiva_id, numero_brinco="TEN-A"))
    
    # Tenta acessar do tenant B
    with pytest.raises(EntityNotFoundError):
        await svc_b.get_or_fail(animal_a.id)
        
    # Tenta atualizar o animal do Tenant A usando o Tenant B (deve falhar por EntityNotFound, pois svc.get_or_fail falha antes)
    with pytest.raises(EntityNotFoundError):
        await svc_b.update(animal_a.id, AnimalUpdate(nome="Hacked"))


async def test_animal_service_invalid_lote(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID):
    svc = AnimalService(session, tenant_id)
    
    payload = AnimalCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        numero_brinco="ERR-01",
        lote_id=uuid.uuid4() # Lote inexistente
    )
    
    with pytest.raises(EntityNotFoundError, match="Lote com ID"):
        await svc.create(payload)
