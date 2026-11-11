"""Seed and consume synthetic fertilizer in the isolated laboratory."""

import asyncio
from datetime import date

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_model
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Use the inventory and operation services to record fertilizer consumption."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.schemas import InsumoOperacaoCreate, OperacaoAgricolaCreate
        from agricola.operacoes.service import OperacaoService
        from agricola.tarefas.models import SafraTarefa
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito, EstoqueMovimento, LoteEstoque, SaldoEstoque
        from operacional.services.estoque_service import EstoqueService

        for farm in (1, 2):
            farm_id = demo_id(("cafe" if farm == 1 else "pecuaria") + "/fazenda")
            prefix = f"cafe/fazenda-{farm}"
            product = await ensure_model(
                session,
                Produto,
                demo_id(prefix + "/fertilizante"),
                {
                    "tenant_id": TENANT_ID,
                    "nome": f"Fertilizante demonstração {farm}",
                    "tipo": "FERTILIZANTE",
                    "unidade_medida": "KG",
                    "preco_medio": 4,
                    "ativo": True,
                },
            )
            depot = await ensure_model(
                session,
                Deposito,
                demo_id(prefix + "/deposito"),
                {
                    "tenant_id": TENANT_ID,
                    "unidade_produtiva_id": farm_id,
                    "nome": "Depósito de insumos",
                    "tipo": "GERAL",
                    "ativo": True,
                },
            )
            initial = (
                await session.execute(
                    select(EstoqueMovimento).where(
                        EstoqueMovimento.tenant_id == TENANT_ID,
                        EstoqueMovimento.produto_id == product.id,
                        EstoqueMovimento.deposito_id == depot.id,
                        EstoqueMovimento.tipo_movimento == "SALDO_INICIAL",
                    )
                )
            ).scalar_one_or_none()
            if initial is None:
                lot = LoteEstoque(
                    id=demo_id(prefix + "/lote-fertilizante"),
                    produto_id=product.id,
                    deposito_id=depot.id,
                    numero_lote=f"DEMO-{farm}-2026",
                    data_fabricacao=date(2026, 1, 1),
                    quantidade_inicial=5000,
                    quantidade_atual=5000,
                    custo_unitario=4,
                    status="ATIVO",
                )
                session.add(lot)
                await session.flush()
                stock = EstoqueService(session, TENANT_ID)
                await stock.registrar_saldo_inicial_implantacao(
                    produto_id=product.id,
                    deposito_id=depot.id,
                    quantidade=5000,
                    origem_id=demo_id(prefix + "/saldo-inicial"),
                    custo_unitario=4,
                    unidade_produtiva_id=farm_id,
                    numero_lote_legado=lot.numero_lote,
                    observacao="Saldo inicial fictício da safra 2026",
                )
                balance = (
                    await session.execute(
                        select(SaldoEstoque).where(
                            SaldoEstoque.deposito_id == depot.id,
                            SaldoEstoque.produto_id == product.id,
                        )
                    )
                ).scalar_one()
                balance.custo_medio = 4
                await session.commit()
            for plot in (1, 2):
                key = f"{prefix}/talhao-{plot}"
                task_id = demo_id(key + "/tarefa-3")
                task = (
                    await session.execute(
                        select(SafraTarefa).where(
                            SafraTarefa.tenant_id == TENANT_ID,
                            SafraTarefa.id == task_id,
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
                        raise DemoLabTargetError("Unexpected fertilizer task state")
                    continue
                if task.status != "APROVADA":
                    raise DemoLabTargetError("Unexpected fertilizer task status")
                data = OperacaoAgricolaCreate(
                    safra_id=demo_id("cafe/safra-2026"),
                    cultivo_id=demo_id("cafe/cultivo-2026"),
                    talhao_id=demo_id(key),
                    production_unit_id=demo_id(key + "/unidade"),
                    tarefa_id=task_id,
                    tipo="ADUBAÇÃO",
                    descricao="Adubação de manutenção",
                    fase_safra="DESENVOLVIMENTO",
                    data_prevista=date(2026, 3, 15),
                    data_realizada=date(2026, 3, 15),
                    area_aplicada_ha=25,
                    insumos=[
                        InsumoOperacaoCreate(
                            produto_id=product.id, dose_por_ha=100, unidade="KG", area_aplicada=25
                        )
                    ],
                    observacoes="Dados fictícios de demonstração.",
                )
                await OperacaoService(session, TENANT_ID).criar(data)
                print(f"Fertilizer consumed: farm {farm}, plot {plot}", flush=True)


if __name__ == "__main__":
    asyncio.run(load())
