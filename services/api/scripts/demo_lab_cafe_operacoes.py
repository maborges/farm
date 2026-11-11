"""Execute the planned synthetic coffee tasks via the agricultural service."""

import asyncio

from sqlalchemy import select

from scripts.demo_lab_cafe import TASKS
from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session
from scripts.demo_lab_guard import DemoLabTargetError

TYPES = ("PREPARO_SOLO", "PLANTIO", "ADUBAÇÃO", "OUTROS", "COLHEITA", "OUTROS")


async def load():
    """Execute non-input tasks; input consumption is loaded separately."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.schemas import OperacaoAgricolaCreate
        from agricola.operacoes.service import OperacaoService
        from agricola.tarefas.models import SafraTarefa

        service = OperacaoService(session, TENANT_ID)
        for farm in (1, 2):
            for plot in (1, 2):
                key = f"cafe/fazenda-{farm}/talhao-{plot}"
                for index, (phase, _, description, day, cost) in enumerate(TASKS, 1):
                    if index == 3:
                        continue  # The fertilizer must be consumed from stock.
                    task_id = demo_id(f"{key}/tarefa-{index}")
                    task = (
                        await session.execute(
                            select(SafraTarefa).where(
                                SafraTarefa.id == task_id, SafraTarefa.tenant_id == TENANT_ID
                            )
                        )
                    ).scalar_one()
                    existing = (
                        (
                            await session.execute(
                                select(OperacaoAgricola).where(
                                    OperacaoAgricola.tenant_id == TENANT_ID,
                                    OperacaoAgricola.tarefa_id == task_id,
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if existing:
                        if len(existing) != 1 or task.operacao_id != existing[0].id:
                            raise DemoLabTargetError("Unexpected task operation state")
                        continue
                    if task.status != "APROVADA":
                        raise DemoLabTargetError("Unexpected planned task status")
                    data = OperacaoAgricolaCreate(
                        safra_id=demo_id("cafe/safra-2026"),
                        cultivo_id=demo_id("cafe/cultivo-2026"),
                        talhao_id=demo_id(key),
                        production_unit_id=demo_id(key + "/unidade"),
                        tarefa_id=task_id,
                        tipo=TYPES[index - 1],
                        descricao=description,
                        fase_safra=phase,
                        data_prevista=day,
                        data_realizada=day,
                        area_aplicada_ha=25,
                        custo_total=cost,
                        observacoes="Registro sintético de demonstração.",
                    )
                    await service.criar(data)
                    print(f"Executed farm {farm}, plot {plot}, task {index}", flush=True)


if __name__ == "__main__":
    asyncio.run(load())
