import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError, BusinessRuleError
from pecuaria.animal.models import Animal, LoteAnimal
from pecuaria.schemas.animal_schema import AnimalCreate, AnimalUpdate, AnimalFilter

class AnimalService(BaseService[Animal]):
    
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None, ip_address: str | None = None):
        super().__init__(Animal, session, tenant_id, user_id, ip_address)
        
    async def _validate_references(self, data: dict):
        # Validação do lote_id
        if data.get("lote_id"):
            lote_id = data["lote_id"]
            stmt = select(LoteAnimal).where(
                and_(
                    LoteAnimal.id == lote_id,
                    LoteAnimal.tenant_id == self.tenant_id
                )
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(f"Lote com ID {lote_id} não encontrado neste tenant.")
            
        # Validação de pai_id
        if data.get("pai_id"):
            pai_id = data["pai_id"]
            stmt = select(Animal).where(
                and_(
                    Animal.id == pai_id,
                    Animal.tenant_id == self.tenant_id
                )
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(f"Animal Pai com ID {pai_id} não encontrado neste tenant.")
                
        # Validação de mae_id
        if data.get("mae_id"):
            mae_id = data["mae_id"]
            stmt = select(Animal).where(
                and_(
                    Animal.id == mae_id,
                    Animal.tenant_id == self.tenant_id
                )
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(f"Animal Mãe com ID {mae_id} não encontrado neste tenant.")

    async def create(self, obj_in: AnimalCreate | dict) -> Animal:
        data = obj_in.model_dump() if isinstance(obj_in, AnimalCreate) else obj_in
        await self._validate_references(data)
        return await super().create(data)

    async def update(self, id: uuid.UUID, obj_in: AnimalUpdate | dict) -> Animal:
        data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, AnimalUpdate) else obj_in
        await self._validate_references(data)
        return await super().update(id, data)

    async def list_paginated(
        self, 
        skip: int, 
        limit: int, 
        unidade_produtiva_id: uuid.UUID,
        filter_params: AnimalFilter
    ) -> Tuple[list[Animal], int]:
        
        stmt = select(Animal).where(
            and_(
                Animal.tenant_id == self.tenant_id,
                Animal.unidade_produtiva_id == unidade_produtiva_id
            )
        )
        
        if filter_params.q:
            q = f"%{filter_params.q}%"
            stmt = stmt.where(
                or_(
                    Animal.numero_brinco.ilike(q),
                    Animal.numero_sisbov.ilike(q),
                    Animal.nome.ilike(q)
                )
            )
            
        if filter_params.lote_id:
            stmt = stmt.where(Animal.lote_id == filter_params.lote_id)
        if filter_params.categoria:
            stmt = stmt.where(Animal.categoria == filter_params.categoria)
        if filter_params.status:
            stmt = stmt.where(Animal.status == filter_params.status)
        if filter_params.sexo:
            stmt = stmt.where(Animal.sexo == filter_params.sexo)
        if filter_params.especie:
            stmt = stmt.where(Animal.especie == filter_params.especie)
            
        # Contagem total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0
        
        # Paginação e ordenação (mais recentes primeiro)
        stmt = stmt.order_by(Animal.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        
        return list(result.scalars().all()), total
