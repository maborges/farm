"""
Insere itens de checklist e tarefas padrão no PhaseTemplate de COLHEITA
de pimenta-do-reino já criado (id 81e7ba18-bc8c-446c-be52-4372e6302d1e).
Uso: PYTHONPATH=/opt/lampp/htdocs/farm/services/api python scripts/seed_checklist_items_colheita_pimenta_reino.py
"""
import asyncio
import uuid
from sqlalchemy import select
from core.database import async_session_maker
from agricola.models.templates import PhaseTemplate, PhaseTemplateChecklistItem, PhaseTemplateTask

TEMPLATE_ID = uuid.UUID("81e7ba18-bc8c-446c-be52-4372e6302d1e")

# (titulo, obrigatorio, ordem)
CHECKLIST_ITEMS = [
    ("Verificar maturação das espigas (grãos vermelhos/amarelos por cacho)", True, 1),
    ("Confirmar disponibilidade de mão de obra para colheita manual", True, 2),
    ("Preparar lonas/panos e recipientes de coleta", True, 3),
    ("Verificar condições climáticas (evitar colheita em chuva)", True, 4),
    ("Inspecionar espaldeiras/tutores quanto a segurança para colheita", False, 5),
    ("Definir ordem de colheita por talhão (maturação mais avançada primeiro)", True, 6),
    ("Preparar área de terreiro/secador para recepção da colheita", True, 7),
    ("Verificar disponibilidade de sacaria/big bags para transporte", False, 8),
    ("Registrar EPIs disponíveis para equipe de colheita", False, 9),
    ("Conferir balança para pesagem em campo", False, 10),
]

# (tipo, titulo, criticidade, ordem)
TASKS = [
    ("COLHEITA", "Colher cachos maduros por talhão", "CRITICA", 1),
    ("COLHEITA", "Transportar cachos colhidos até o terreiro/secador", "CRITICA", 2),
    ("COLHEITA", "Debulhar (separar grãos dos cachos)", "CRITICA", 3),
    ("COLHEITA", "Lavar/selecionar grãos (pimenta preta vs branca)", "NORMAL", 4),
    ("COLHEITA", "Secar grãos ao sol ou em secador até umidade adequada", "CRITICA", 5),
    ("COLHEITA", "Registrar produtividade colhida por talhão (kg/ha)", "NORMAL", 6),
    ("COLHEITA", "Armazenar grãos secos em local ventilado e protegido de umidade", "NORMAL", 7),
    ("COLHEITA", "Registrar custo de colheita e mão de obra utilizada", "OPCIONAL", 8),
    ("COLHEITA", "Emitir romaneio/nota de produção da safra", "OPCIONAL", 9),
]


async def seed():
    async with async_session_maker() as session:
        container = await session.get(PhaseTemplate, TEMPLATE_ID)
        if not container:
            print(f"PhaseTemplate {TEMPLATE_ID} não encontrado.")
            return

        existing_items = set((await session.execute(
            select(PhaseTemplateChecklistItem.titulo).where(
                PhaseTemplateChecklistItem.phase_template_id == container.id
            )
        )).scalars().all())
        existing_tasks = set((await session.execute(
            select(PhaseTemplateTask.titulo).where(
                PhaseTemplateTask.phase_template_id == container.id
            )
        )).scalars().all())

        itens_inseridos = 0
        for titulo, obrigatorio, ordem in CHECKLIST_ITEMS:
            if titulo in existing_items:
                continue
            session.add(PhaseTemplateChecklistItem(
                phase_template_id=container.id,
                titulo=titulo,
                obrigatorio=obrigatorio,
                ordem=ordem,
                ativo=True,
            ))
            itens_inseridos += 1

        tarefas_inseridas = 0
        for tipo, titulo, criticidade, ordem in TASKS:
            if titulo in existing_tasks:
                continue
            session.add(PhaseTemplateTask(
                phase_template_id=container.id,
                tipo=tipo,
                titulo=titulo,
                criticidade=criticidade,
                ordem=ordem,
            ))
            tarefas_inseridas += 1

        await session.commit()
        print(
            f"Seed concluído: {itens_inseridos} itens de checklist inseridos, "
            f"{tarefas_inseridas} tarefas padrão inseridas."
        )


if __name__ == "__main__":
    asyncio.run(seed())
