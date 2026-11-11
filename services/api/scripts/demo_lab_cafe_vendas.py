"""Create synthetic harvest and sales using the laboratory business services."""

import asyncio
from datetime import date

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_model
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Create four traceable harvest lots and confirmed sales."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.colheita.models import ProdutoColhido
        from agricola.colheita.schemas import ProdutoColhidoCreate
        from agricola.colheita.service import ProdutoColhidoService
        from agricola.romaneios.models import RomaneioColheita
        from agricola.romaneios.schemas import RomaneioColheitaCreate
        from agricola.romaneios.service import RomaneioService
        from core.cadastros.commodities.models import Commodity
        from core.cadastros.pessoas.models import Pessoa
        from financeiro.comercializacao.models import ComercializacaoCommodity
        from financeiro.comercializacao.schemas import ComercializacaoCreate
        from financeiro.comercializacao.service import ComercializacaoService
        from financeiro.models.plano_conta import PlanoConta

        commodity = await ensure_model(
            session,
            Commodity,
            demo_id("cafe/commodity"),
            {
                "tenant_id": TENANT_ID,
                "nome": "Café beneficiado demonstração",
                "codigo": "DEMO_CAFE_LAB",
                "tipo": "GRAO",
                "unidade_padrao": "SACA_60KG",
                "peso_unidade": 60,
                "ativo": True,
                "sistema": False,
            },
        )
        buyer = await ensure_model(
            session,
            Pessoa,
            demo_id("cafe/comprador"),
            {
                "tenant_id": TENANT_ID,
                "tipo": "PJ",
                "nome_exibicao": "Comprador fictício de café",
                "ativo": True,
                "base_legal": "CONTRATO",
            },
        )
        await ensure_model(
            session,
            PlanoConta,
            demo_id("cafe/conta-receita"),
            {
                "tenant_id": TENANT_ID,
                "codigo": "1.01",
                "nome": "Venda de café",
                "tipo": "RECEITA",
                "natureza": "ANALITICA",
                "categoria_rfb": "RECEITA_ATIVIDADE",
                "ativo": True,
                "is_sistema": False,
            },
        )
        await session.commit()
        for farm in (1, 2):
            for plot in (1, 2):
                key = f"cafe/fazenda-{farm}/talhao-{plot}"
                number = f"DEMO-2026-{farm}-{plot}"
                rom = (
                    await session.execute(
                        select(RomaneioColheita).where(
                            RomaneioColheita.tenant_id == TENANT_ID,
                            RomaneioColheita.numero_romaneio == number,
                        )
                    )
                ).scalar_one_or_none()
                if rom is None:
                    rom = await RomaneioService(session, TENANT_ID).criar(
                        RomaneioColheitaCreate(
                            safra_id=demo_id("cafe/safra-2026"),
                            talhao_id=demo_id(key),
                            production_unit_id=demo_id(key + "/unidade"),
                            numero_romaneio=number,
                            data_colheita=date(2026, 8, 15),
                            peso_bruto_kg=45000,
                            tara_kg=0,
                            umidade_pct=12,
                            impureza_pct=1,
                            destino="ARMAZEM",
                            observacoes="Colheita fictícia de café beneficiado.",
                        )
                    )
                if rom.talhao_id != demo_id(key) or float(rom.sacas_60kg or 0) != 750:
                    raise DemoLabTargetError("Unexpected harvest record")
                lot = (
                    await session.execute(
                        select(ProdutoColhido).where(
                            ProdutoColhido.tenant_id == TENANT_ID,
                            ProdutoColhido.romaneio_id == rom.id,
                        )
                    )
                ).scalar_one_or_none()
                if lot is None:
                    lot = await ProdutoColhidoService(session, TENANT_ID).criar(
                        ProdutoColhidoCreate(
                            safra_id=demo_id("cafe/safra-2026"),
                            talhao_id=demo_id(key),
                            romaneio_id=rom.id,
                            commodity_id=commodity.id,
                            quantidade=750,
                            unidade="SACA_60KG",
                            peso_liquido_kg=45000,
                            data_entrada=date(2026, 9, 15),
                            destino="ARMAZEM",
                            observacoes="Lote fictício de demonstração.",
                        )
                    )
                    await session.commit()
                sale = (
                    await session.execute(
                        select(ComercializacaoCommodity).where(
                            ComercializacaoCommodity.tenant_id == TENANT_ID,
                            ComercializacaoCommodity.produto_colhido_id == lot.id,
                        )
                    )
                ).scalar_one_or_none()
                service = ComercializacaoService(session, TENANT_ID)
                if sale is None:
                    sale = await service.criar(
                        ComercializacaoCreate(
                            commodity_id=commodity.id,
                            comprador_id=buyer.id,
                            numero_contrato=number,
                            produto_colhido_id=lot.id,
                            quantidade=750,
                            unidade="SACA_60KG",
                            preco_unitario=1000,
                            forma_pagamento="PRAZO",
                            data_entrega_prevista=date(2026, 10, 20),
                            observacoes="Venda fictícia para demonstração.",
                        )
                    )
                for current, target in (
                    ("RASCUNHO", "CONFIRMADO"),
                    ("CONFIRMADO", "EM_TRANSITO"),
                    ("EM_TRANSITO", "ENTREGUE"),
                    ("ENTREGUE", "FINALIZADO"),
                ):
                    if sale.status == current:
                        await service.transicionar_status(
                            sale, target, data_entrega_real=date(2026, 10, 20)
                        )
                if sale.status != "FINALIZADO" or not sale.receita_id:
                    raise DemoLabTargetError("Sale did not produce an accounts-receivable entry")
                print(f"Harvest and sale completed: farm {farm}, plot {plot}", flush=True)


if __name__ == "__main__":
    asyncio.run(load())
