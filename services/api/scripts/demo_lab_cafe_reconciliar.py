"""Link demo fertilizer allocations to their matching stock movements."""

import asyncio

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Link one matching movement to the existing allocation without adding cost."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.custos.models import CostAllocation
        from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
        from operacional.models.estoque import EstoqueMovimento

        for farm in (1, 2):
            for plot in (1, 2):
                key = f"cafe/fazenda-{farm}/talhao-{plot}"
                task = demo_id(key + "/tarefa-3")
                op = (
                    await session.execute(
                        select(OperacaoAgricola).where(
                            OperacaoAgricola.tenant_id == TENANT_ID,
                            OperacaoAgricola.tarefa_id == task,
                        )
                    )
                ).scalar_one()
                execution = (
                    await session.execute(
                        select(OperacaoExecucao).where(
                            OperacaoExecucao.tenant_id == TENANT_ID,
                            OperacaoExecucao.operacao_id == op.id,
                        )
                    )
                ).scalar_one()
                movement = (
                    await session.execute(
                        select(EstoqueMovimento).where(
                            EstoqueMovimento.tenant_id == TENANT_ID,
                            EstoqueMovimento.operacao_execucao_id == execution.id,
                            EstoqueMovimento.tipo_movimento == "SAIDA",
                        )
                    )
                ).scalar_one()
                allocation = (
                    await session.execute(
                        select(CostAllocation).where(
                            CostAllocation.tenant_id == TENANT_ID,
                            CostAllocation.operation_execution_id == execution.id,
                            CostAllocation.source == "OPERATION_EXECUTION",
                        )
                    )
                ).scalar_one()
                if (
                    allocation.production_unit_id != movement.production_unit_id
                    or allocation.amount != movement.custo_total
                    or allocation.inventory_movement_id not in (None, movement.id)
                ):
                    raise DemoLabTargetError("Inconsistent cost or movement context")
                allocation.inventory_movement_id = movement.id
        await session.commit()
        print("Four fertilizer allocations reconciled with stock movements")


if __name__ == "__main__":
    asyncio.run(load())
