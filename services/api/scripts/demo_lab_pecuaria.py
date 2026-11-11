"""Load a synthetic livestock scenario into the dedicated demo lab only."""

from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_area, ensure_base


async def load() -> dict:
    """Create one livestock property and real, repeatable animal histories."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
        from pecuaria.models.manejo import ManejoLote
        from pecuaria.schemas.animal_schema import AnimalCreate
        from pecuaria.schemas.manejo_schema import ManejoLoteCreate
        from pecuaria.schemas.pesagem_schema import PesagemCreate
        from pecuaria.services.animal_service import AnimalService
        from pecuaria.services.dashboard_resumo_service import PecuariaDashboardResumoService
        from pecuaria.services.manejo_service import ManejoLoteService
        from pecuaria.services.pesagem_service import PesagemService

        property_ = await ensure_base(session, "pecuaria")
        parent = None
        for key, kind, name in (
            ("raiz", "AREA_RURAL", "Área Rural"),
            ("gleba", "GLEBA", "Gleba Pecuária"),
            ("talhao", "TALHAO", "Pastagem Principal"),
            ("operacional", "AREA_OPERACIONAL", "Área de Pastejo"),
            ("piquete", "PIQUETE", "Piquete 01"),
        ):
            area = await ensure_area(session, f"pecuaria/{key}", {
                "unidade_produtiva_id": property_.id, "parent_id": parent,
                "tipo": kind, "nome": name, "ativo": True,
            })
            parent = area.id

        lot_id = demo_id("pecuaria/lote-01")
        lote = (await session.execute(select(LoteAnimal).where(
            LoteAnimal.id == lot_id, LoteAnimal.tenant_id == TENANT_ID
        ))).scalar_one_or_none()
        if lote is None:
            lote = LoteAnimal(
                id=lot_id, tenant_id=TENANT_ID, unidade_produtiva_id=property_.id,
                area_id=parent, identificacao="Lote Demo 01", especie="BOVINO",
                categoria="GARROTE", raca="Nelore", quantidade_cabecas=0,
                peso_medio_kg=0, data_formacao=date(2025, 1, 1), ativo=True,
            )
            session.add(lote)
            await session.flush()
        elif lote.unidade_produtiva_id != property_.id or lote.area_id != parent:
            raise ValueError("Lote demonstrativo com vínculo divergente")

        animals = AnimalService(session, TENANT_ID)
        weights = PesagemService(session, TENANT_ID)
        for index in range(1, 6):
            animal_id = demo_id(f"pecuaria/animal-{index}")
            animal = (await session.execute(select(Animal).where(
                Animal.id == animal_id, Animal.tenant_id == TENANT_ID
            ))).scalar_one_or_none()
            if animal is None:
                data = AnimalCreate(
                    unidade_produtiva_id=property_.id, lote_id=lot_id,
                    numero_brinco=f"DEMO-{index:03d}", especie="BOVINO",
                    categoria="GARROTE", sexo="MACHO", raca="Nelore",
                    data_nascimento=date(2024, 3, index), data_entrada=date(2025, 1, 1),
                ).model_dump()
                data["id"] = animal_id
                await animals.create(data)
                await session.commit()
            elif animal.lote_id != lot_id or animal.unidade_produtiva_id != property_.id:
                raise ValueError("Animal demonstrativo com vínculo divergente")

            for day, weight in ((date(2025, 2, 1), 180 + index),
                                (date(2025, 5, 2), 252 + index)):
                existing = (await session.execute(select(EventoAnimal).where(
                    EventoAnimal.tenant_id == TENANT_ID, EventoAnimal.animal_id == animal_id,
                    EventoAnimal.tipo == "PESAGEM", EventoAnimal.data_evento == day,
                ))).scalar_one_or_none()
                if existing is None:
                    await weights.registrar_pesagem(animal_id, PesagemCreate(
                        data_evento=day, peso_kg=weight, observacoes="Dados fictícios",
                    ))
                elif existing.peso_kg != weight:
                    raise ValueError("Pesagem demonstrativa divergente")

        await animals._materializar_lote(lot_id)
        manejo = (await session.execute(select(ManejoLote).where(
            ManejoLote.tenant_id == TENANT_ID, ManejoLote.lote_id == lot_id,
            ManejoLote.tipo_evento == "VACINACAO",
            ManejoLote.data_evento == date(2025, 4, 1),
        ))).scalar_one_or_none()
        if manejo is None:
            await ManejoLoteService(TENANT_ID).registrar_evento(session, obj_in=ManejoLoteCreate(
                lote_id=lot_id, tipo_evento="VACINACAO", data_evento=date(2025, 4, 1),
                quantidade_cabecas=5, observacoes="Vacinação fictícia de treinamento",
            ))
        await session.commit()
        summary = await PecuariaDashboardResumoService(session, TENANT_ID, property_.id).resumir()
        return summary.model_dump()


if __name__ == "__main__":
    print(asyncio.run(load()))
