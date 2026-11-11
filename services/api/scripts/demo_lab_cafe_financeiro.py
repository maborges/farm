"""Add synthetic overhead and payment states to the coffee demonstration."""

import asyncio
from datetime import date

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_model
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Use finance services to create expenses and register selected settlements."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from financeiro.comercializacao.models import ComercializacaoCommodity
        from financeiro.models.conciliacao import ContaBancaria
        from financeiro.models.despesa import Despesa
        from financeiro.models.plano_conta import PlanoConta
        from financeiro.models.receita import Receita
        from financeiro.schemas.despesa_schema import (
            BaixaDespesaRequest,
            DespesaCreate,
            RateioCreate,
        )
        from financeiro.schemas.receita_schema import ReceitaUpdate
        from financeiro.services.despesa_service import DespesaService
        from financeiro.services.receita_service import ReceitaService

        account = await ensure_model(
            session,
            ContaBancaria,
            demo_id("cafe/conta-ficticia"),
            {
                "tenant_id": TENANT_ID,
                "nome": "Conta fictícia — demonstração",
                "tipo": "CORRENTE",
                "ativa": True,
                "homologada_para_remessa": False,
            },
        )
        plan = await ensure_model(
            session,
            PlanoConta,
            demo_id("cafe/conta-administrativa"),
            {
                "tenant_id": TENANT_ID,
                "codigo": "2.01",
                "nome": "Administração da safra",
                "tipo": "DESPESA",
                "natureza": "ANALITICA",
                "categoria_rfb": "CUSTEIO",
                "ativo": True,
                "is_sistema": False,
            },
        )
        await session.commit()
        for farm in (1, 2):
            farm_id = demo_id(("cafe" if farm == 1 else "pecuaria") + "/fazenda")
            for plot in (1, 2):
                key = f"cafe/fazenda-{farm}/talhao-{plot}"
                source_id = demo_id(key + "/despesa-administrativa")
                expense = (
                    await session.execute(
                        select(Despesa).where(
                            Despesa.tenant_id == TENANT_ID,
                            Despesa.origem_tipo == "DEMO_CAFE",
                            Despesa.origem_id == source_id,
                        )
                    )
                ).scalar_one_or_none()
                service = DespesaService(session, TENANT_ID)
                if expense is None:
                    data = DespesaCreate(
                        unidade_produtiva_id=farm_id,
                        plano_conta_id=plan.id,
                        cultivo_id=demo_id("cafe/cultivo-2026"),
                        descricao="Gestão administrativa fictícia da safra",
                        valor_total=10000,
                        data_emissao=date(2026, 10, 1),
                        data_vencimento=date(2026, 11, 5),
                        competencia=date(2026, 10, 1),
                        origem_tipo="DEMO_CAFE",
                        origem_id=source_id,
                        observacoes="Despesa fictícia de demonstração.",
                        rateios=[
                            RateioCreate(
                                safra_id=demo_id("cafe/safra-2026"),
                                talhao_id=demo_id(key),
                                valor_rateado=10000,
                                percentual=100,
                            )
                        ],
                    )
                    expense = (await service.create_with_rateio(data))[0]
                    await session.commit()
                if expense.valor_total != 10000 or expense.unidade_produtiva_id != farm_id:
                    raise DemoLabTargetError("Unexpected demonstration expense")
                if plot == 1 and expense.status == "A_PAGAR":
                    await service.baixar(
                        expense.id,
                        BaixaDespesaRequest(
                            data_pagamento=date(2026, 11, 4),
                            valor_pago=10000,
                            forma_pagamento="TRANSFERENCIA",
                            conta_bancaria_pagamento_id=account.id,
                        ),
                    )
                    await session.commit()
                sale = (
                    await session.execute(
                        select(ComercializacaoCommodity).where(
                            ComercializacaoCommodity.tenant_id == TENANT_ID,
                            ComercializacaoCommodity.numero_contrato == f"DEMO-2026-{farm}-{plot}",
                        )
                    )
                ).scalar_one()
                receipt = (
                    await session.execute(
                        select(Receita).where(
                            Receita.tenant_id == TENANT_ID,
                            Receita.id == sale.receita_id,
                        )
                    )
                ).scalar_one()
                if plot == 1 and receipt.status == "A_RECEBER":
                    await ReceitaService(session, TENANT_ID).atualizar(
                        receipt.id,
                        ReceitaUpdate(
                            valor_recebido=750000,
                            data_recebimento=date(2026, 11, 4),
                            forma_recebimento="TRANSFERENCIA",
                        ),
                    )
                    await session.commit()
        print("Synthetic expenses and selected settlements verified")


if __name__ == "__main__":
    asyncio.run(load())
