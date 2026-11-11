"""Create the synthetic coffee season in the isolated demonstration laboratory."""

import asyncio
from datetime import date

from scripts.demo_lab_common import (
    TENANT_ID,
    demo_id,
    demo_session,
    ensure_area,
    ensure_base,
    ensure_model,
)

# Coffee is perennial: the PLANTIO phase documents stand maintenance/replanting,
# not the establishment of the entire crop in this season.
PHASES = (
    ("PLANEJADA", date(2026, 1, 5)),
    ("PREPARO_SOLO", date(2026, 1, 15)),
    ("PLANTIO", date(2026, 2, 10)),
    ("DESENVOLVIMENTO", date(2026, 3, 5)),
    ("COLHEITA", date(2026, 6, 1)),
    ("POS_COLHEITA", date(2026, 9, 1)),
    ("ENCERRADA", date(2026, 11, 5)),
)

TASKS = (
    ("PREPARO_SOLO", "OUTRO", "Roçada e conservação das entrelinhas", date(2026, 1, 20), 3000),
    ("PLANTIO", "PLANTIO", "Replantio pontual de falhas", date(2026, 2, 15), 2500),
    ("DESENVOLVIMENTO", "ADUBACAO_NITROGENIO", "Adubação de manutenção", date(2026, 3, 15), 10000),
    ("DESENVOLVIMENTO", "OUTRO", "Monitoramento e manejo da lavoura", date(2026, 4, 15), 2000),
    ("COLHEITA", "COLHEITA", "Colheita de café", date(2026, 7, 1), 15000),
    ("POS_COLHEITA", "OUTRO", "Secagem e beneficiamento", date(2026, 9, 15), 5000),
)


async def create_plan(session, season, crop):
    """Record a costed plan and a task for each phase and coffee plot."""
    from agricola.a1_planejamento.models import ItemOrcamentoSafra
    from agricola.planejamento_operacional.models import PlanoOperacional, PlanoOperacionalTarefa
    from agricola.tarefas.models import SafraTarefa

    plan = await ensure_model(
        session,
        PlanoOperacional,
        demo_id("cafe/plano"),
        {
            "tenant_id": TENANT_ID,
            "safra_id": season.id,
            "nome": "Plano operacional Café 2026",
            "descricao": "Planejamento sintético das duas fazendas.",
            "data_inicio_prevista": date(2026, 1, 5),
            "data_fim_prevista": date(2026, 11, 5),
            "versao": 1,
        },
    )
    if plan.status == "RASCUNHO":
        plan.status = "PRONTO"
    for category, description, amount in (
        ("FERTILIZANTE", "Adubação de manutenção", 40000),
        ("MAO_DE_OBRA", "Mão de obra de colheita e tratos", 90000),
        ("SERVICO", "Secagem e beneficiamento", 20000),
    ):
        await ensure_model(
            session,
            ItemOrcamentoSafra,
            demo_id("cafe/orcamento/" + category),
            {
                "tenant_id": TENANT_ID,
                "safra_id": season.id,
                "cultivo_id": crop.id,
                "categoria": category,
                "descricao": description,
                "quantidade": 1,
                "unidade": "verba",
                "custo_unitario": amount,
                "custo_total": amount,
                "origem_tipo": "MANUAL",
                "ordem": 0,
            },
        )
    for farm_index in (1, 2):
        for number in (1, 2):
            key = f"cafe/fazenda-{farm_index}/talhao-{number}"
            for order, (phase, kind, description, day, cost) in enumerate(TASKS, 1):
                task_key = f"{key}/tarefa-{order}"
                task = await ensure_model(
                    session,
                    SafraTarefa,
                    demo_id(task_key),
                    {
                        "tenant_id": TENANT_ID,
                        "safra_id": season.id,
                        "production_unit_id": demo_id(key + "/unidade"),
                        "talhao_id": demo_id(key),
                        "cultivo_area_id": demo_id(key + "/cultivo"),
                        "origem": "MANUAL",
                        "tipo": kind,
                        "fase": phase,
                        "criticidade": "NORMAL",
                        "ordem": order,
                        "descricao": description,
                        "prioridade": "MEDIA",
                        "area_ha": 25,
                        "custo_estimado": cost,
                        "data_prevista": day,
                    },
                )
                if task.status == "PENDENTE_APROVACAO":
                    task.status = "APROVADA"
                await ensure_model(
                    session,
                    PlanoOperacionalTarefa,
                    demo_id(task_key + "/plano"),
                    {
                        "tenant_id": TENANT_ID,
                        "plano_operacional_id": plan.id,
                        "safra_tarefa_id": task.id,
                        "status_planejamento": "PRONTA",
                        "data_programada": day,
                        "ordem_execucao": order,
                    },
                )


async def load():
    """Prepare a planned season and its territory using the area service."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from agricola.cultivos.models import Cultivo, CultivoArea
        from agricola.production_units.models import ProductionUnit
        from agricola.safras.models import Safra, SafraTalhao
        from core.cadastros.produtos.models import ProdutoCultura

        farms = [await ensure_base(session, scenario) for scenario in ("cafe", "pecuaria")]
        culture = await ensure_model(
            session,
            ProdutoCultura,
            demo_id("cafe/cultura"),
            {
                "tenant_id": TENANT_ID,
                "nome": "Café",
                "nome_cientifico": "Coffea arabica",
                "grupo": "GRAOS",
                "ativa": True,
                "sistema": False,
            },
        )
        season = await ensure_model(
            session,
            Safra,
            demo_id("cafe/safra-2026"),
            {
                "tenant_id": TENANT_ID,
                "ano_safra": "2026",
                "cultura": "Café",
                "observacoes": "Safra sintética para demonstração.",
            },
        )
        crop = await ensure_model(
            session,
            Cultivo,
            demo_id("cafe/cultivo-2026"),
            {
                "tenant_id": TENANT_ID,
                "safra_id": season.id,
                "cultura": "Café",
                "cultivar_id": culture.id,
                "cultivar_nome": "Arábica",
                "data_inicio": date(2026, 1, 5),
                "data_colheita_prevista": date(2026, 6, 1),
                "produtividade_meta_sc_ha": 30,
                "observacoes": "Lavoura perene existente; replantio apenas de falhas.",
            },
        )
        for farm_index, farm in enumerate(farms, 1):
            parent = None
            for key, kind, name in (
                ("raiz", "AREA_RURAL", "Área Rural"),
                ("gleba", "GLEBA", "Gleba Café"),
            ):
                area = await ensure_area(
                    session,
                    f"cafe/fazenda-{farm_index}/{key}",
                    {
                        "unidade_produtiva_id": farm.id,
                        "parent_id": parent,
                        "tipo": kind,
                        "nome": name,
                        "ativo": True,
                    },
                )
                parent = area.id
            for number in (1, 2):
                key = f"cafe/fazenda-{farm_index}/talhao-{number}"
                area = await ensure_area(
                    session,
                    key,
                    {
                        "unidade_produtiva_id": farm.id,
                        "parent_id": parent,
                        "tipo": "TALHAO",
                        "nome": f"Café {number:02d}",
                        "ativo": True,
                        "area_hectares_manual": 25,
                    },
                )
                ca = await ensure_model(
                    session,
                    CultivoArea,
                    demo_id(key + "/cultivo"),
                    {
                        "tenant_id": TENANT_ID,
                        "cultivo_id": crop.id,
                        "area_id": area.id,
                        "area_ha": 25,
                    },
                )
                await ensure_model(
                    session,
                    SafraTalhao,
                    demo_id(key + "/safra"),
                    {
                        "tenant_id": TENANT_ID,
                        "safra_id": season.id,
                        "area_id": area.id,
                        "area_ha": 25,
                        "principal": farm_index == 1 and number == 1,
                    },
                )
                await ensure_model(
                    session,
                    ProductionUnit,
                    demo_id(key + "/unidade"),
                    {
                        "tenant_id": TENANT_ID,
                        "safra_id": season.id,
                        "cultivo_id": crop.id,
                        "cultivo_area_id": ca.id,
                        "area_id": area.id,
                        "area_ha": 25,
                        "percentual_participacao": 100,
                        "status": "ATIVA",
                        "data_inicio": date(2026, 1, 5),
                    },
                )
        await create_plan(session, season, crop)
        # Phase history and final closure are inserted after all operational flows exist.
        await session.commit()
        print(f"Coffee season and plan verified; season status: {season.status}")


if __name__ == "__main__":
    asyncio.run(load())
