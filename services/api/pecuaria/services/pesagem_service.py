from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, asc
from uuid import UUID
from fastapi import HTTPException

from core.base_service import BaseService
from pecuaria.animal.models import Animal, EventoAnimal
from pecuaria.schemas.pesagem_schema import PesagemCreate, PesagemResponse
from pecuaria.services.gmd_utils import calcular_gmd

class PesagemService(BaseService[EventoAnimal]):
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(EventoAnimal, db, tenant_id)

    async def registrar_pesagem(self, animal_id: UUID, obj_in: PesagemCreate) -> PesagemResponse:
        # Validar animal e tenant
        stmt = select(Animal).where(Animal.id == animal_id, Animal.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        animal = result.scalars().first()

        if not animal:
            raise HTTPException(status_code=404, detail="Animal não encontrado ou não pertence a esta unidade")

        # Inserir o EventoAnimal
        evento = EventoAnimal(
            tenant_id=self.tenant_id,
            animal_id=animal_id,
            tipo="PESAGEM",
            data_evento=obj_in.data_evento,
            peso_kg=obj_in.peso_kg,
            observacoes=obj_in.observacoes,
            tarefa_campo_id=obj_in.tarefa_campo_id,
            operador_id=obj_in.operador_id
        )
        self.session.add(evento)

        # Tratar a atualização de Animal.peso_atual_kg
        # Precisamos ver se esta pesagem é a mais recente
        if animal.data_ultima_pesagem is None or obj_in.data_evento >= animal.data_ultima_pesagem:
            animal.peso_atual_kg = obj_in.peso_kg
            animal.data_ultima_pesagem = obj_in.data_evento
        
        await self.session.commit()

        # GMD do evento recém-criado: busca só a pesagem cronologicamente anterior
        # (não relista todo o histórico do animal para achar esse único dado).
        anterior_stmt = (
            select(EventoAnimal)
            .where(
                EventoAnimal.animal_id == animal_id,
                EventoAnimal.tenant_id == self.tenant_id,
                EventoAnimal.tipo == "PESAGEM",
                EventoAnimal.data_evento < obj_in.data_evento,
            )
            .order_by(desc(EventoAnimal.data_evento))
            .limit(1)
        )
        anterior = (await self.session.execute(anterior_stmt)).scalars().first()

        dias_desde_anterior = None
        gmd = None
        if anterior and anterior.peso_kg is not None and evento.peso_kg is not None:
            dias = (evento.data_evento - anterior.data_evento).days
            gmd = calcular_gmd(evento.peso_kg, anterior.peso_kg, dias)
            if gmd is not None:
                dias_desde_anterior = dias

        return PesagemResponse(
            id=evento.id,
            animal_id=evento.animal_id,
            data_evento=evento.data_evento,
            peso_kg=evento.peso_kg, # type: ignore
            dias_desde_anterior=dias_desde_anterior,
            gmd_periodo=gmd,
            observacoes=evento.observacoes,
            tarefa_campo_id=evento.tarefa_campo_id,
            operador_id=evento.operador_id
        )

    async def listar_pesagens(self, animal_id: UUID) -> list[PesagemResponse]:
        # Validar animal e tenant
        stmt = select(Animal).where(Animal.id == animal_id, Animal.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        if not result.scalars().first():
            raise HTTPException(status_code=404, detail="Animal não encontrado")

        # Buscar todos os eventos PESAGEM ordenados cronologicamente
        stmt = (
            select(EventoAnimal)
            .where(
                EventoAnimal.animal_id == animal_id,
                EventoAnimal.tenant_id == self.tenant_id,
                EventoAnimal.tipo == "PESAGEM"
            )
            .order_by(asc(EventoAnimal.data_evento))
        )
        
        result = await self.session.execute(stmt)
        eventos = result.scalars().all()

        responses = []
        peso_anterior = None
        data_anterior = None

        for evt in eventos:
            dias_desde_anterior = None
            gmd = None

            if data_anterior and peso_anterior is not None and evt.peso_kg is not None:
                dias = (evt.data_evento - data_anterior).days
                gmd = calcular_gmd(evt.peso_kg, peso_anterior, dias)
                if gmd is not None:
                    dias_desde_anterior = dias

            responses.append(PesagemResponse(
                id=evt.id,
                animal_id=evt.animal_id,
                data_evento=evt.data_evento,
                peso_kg=evt.peso_kg, # type: ignore
                dias_desde_anterior=dias_desde_anterior,
                gmd_periodo=gmd,
                observacoes=evt.observacoes,
                tarefa_campo_id=evt.tarefa_campo_id,
                operador_id=evt.operador_id
            ))

            peso_anterior = evt.peso_kg
            data_anterior = evt.data_evento

        # Retornar decrescente (mais recente primeiro)
        return list(reversed(responses))
