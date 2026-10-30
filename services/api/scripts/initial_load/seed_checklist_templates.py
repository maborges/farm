"""
Seed de templates de checklist agronômico por fase.
Uso: PYTHONPATH=. python scripts/initial_load/seed_checklist_templates.py
"""
import asyncio

from sqlalchemy import select

from agricola.models.templates import PhaseTemplate, PhaseTemplateChecklistItem
from core.database import async_session_maker

# (fase, cultura, titulo, obrigatorio)
TEMPLATES = [
    # ─── PLANEJADA ────────────────────────────────────────────────────────────
    ("PLANEJADA", None,    "Definir área e talhões da safra",              True),
    ("PLANEJADA", None,    "Elaborar orçamento e custo previsto por ha",    True),
    ("PLANEJADA", None,    "Escolher cultivar / híbrido",                   True),
    ("PLANEJADA", None,    "Verificar disponibilidade de insumos",          False),
    ("PLANEJADA", None,    "Solicitar análise de solo (se não recente)",    False),
    ("PLANEJADA", None,    "Revisar histórico fitossanitário do talhão",    False),
    ("PLANEJADA", "SOJA",  "Verificar necessidade de inoculante e cobalt",  False),
    ("PLANEJADA", "MILHO", "Definir densidade de plantio e espaçamento",    False),

    # ─── PREPARO_SOLO ─────────────────────────────────────────────────────────
    ("PREPARO_SOLO", None,    "Realizar calagem conforme laudo de solo",     True),
    ("PREPARO_SOLO", None,    "Efetuar subsolagem ou escarificação se necessário", False),
    ("PREPARO_SOLO", None,    "Aplicar corretivos de solo (gesso, etc.)",    False),
    ("PREPARO_SOLO", None,    "Nivelar e preparar o leito de semeadura",     False),
    ("PREPARO_SOLO", None,    "Verificar e corrigir drenagem do talhão",     False),
    ("PREPARO_SOLO", None,    "Eliminar plantas daninhas pré-semeadura",     True),
    ("PREPARO_SOLO", "SOJA",  "Aplicar glifosato de pré-plantio se necessário", False),

    # ─── PLANTIO ──────────────────────────────────────────────────────────────
    ("PLANTIO", None,    "Verificar qualidade e poder germinativo das sementes", True),
    ("PLANTIO", None,    "Tratar sementes (fungicida + inseticida)",              True),
    ("PLANTIO", None,    "Calibrar plantadeira / semeadora",                      True),
    ("PLANTIO", None,    "Registrar data de plantio e estande inicial",            True),
    ("PLANTIO", None,    "Aplicar adubação de base conforme análise de solo",      True),
    ("PLANTIO", None,    "Verificar umidade do solo antes do plantio",             False),
    ("PLANTIO", "SOJA",  "Inocular sementes com Bradyrhizobium spp.",             True),
    ("PLANTIO", "MILHO", "Aplicar inseticida de solo (Diabrotica) se histórico",  False),

    # ─── DESENVOLVIMENTO ─────────────────────────────────────────────────────
    ("DESENVOLVIMENTO", None,    "Realizar avaliação de estande e replantio se necessário", True),
    ("DESENVOLVIMENTO", None,    "Monitorar pragas e doenças semanalmente",                  True),
    ("DESENVOLVIMENTO", None,    "Aplicar herbicida de pós-emergência conforme infestação",  False),
    ("DESENVOLVIMENTO", None,    "Registrar estágio fenológico atual",                        True),
    ("DESENVOLVIMENTO", None,    "Aplicar adubação de cobertura",                             True),
    (
        "DESENVOLVIMENTO", None,
        "Avaliar necessidade de fungicida preventivo", False,
    ),
    (
        "DESENVOLVIMENTO", "SOJA",
        "Aplicar fungicida para ferrugem asiática (V6–R1)", True,
    ),
    (
        "DESENVOLVIMENTO", "SOJA",
        "Monitorar percevejo marrom (a partir de R3)", True,
    ),
    (
        "DESENVOLVIMENTO", "MILHO",
        "Aplicar N em cobertura (V4–V6)", True,
    ),
    (
        "DESENVOLVIMENTO", "MILHO",
        "Monitorar lagarta-do-cartucho", True,
    ),

    # ─── COLHEITA ────────────────────────────────────────────────────────────
    ("COLHEITA", None,    "Verificar umidade dos grãos antes da colheita",  True),
    ("COLHEITA", None,    "Calibrar colheitadeira (perdas < 1 sc/ha)",       True),
    ("COLHEITA", None,    "Registrar produtividade por talhão",               True),
    ("COLHEITA", None,    "Verificar qualidade dos grãos (impureza, avariados)", True),
    ("COLHEITA", None,    "Emitir romaneio de entrega",                       False),
    ("COLHEITA", None,    "Registrar custo de colheita e logística",          False),
    ("COLHEITA", "SOJA",  "Verificar dessecação pré-colheita se necessário",  False),

    # ─── POS_COLHEITA ─────────────────────────────────────────────────────────
    ("POS_COLHEITA", None, "Fechar balanço financeiro da safra (custo × receita)", True),
    ("POS_COLHEITA", None, "Registrar produtividade final e meta realizada",        True),
    ("POS_COLHEITA", None, "Analisar causas de desvio de custo/produtividade",      False),
    ("POS_COLHEITA", None, "Destruir restos culturais ou incorporar palha",         False),
    ("POS_COLHEITA", None, "Realizar manutenção preventiva de máquinas e equipamentos", False),
    ("POS_COLHEITA", None, "Elaborar relatório da safra para próximo planejamento", False),
    ("POS_COLHEITA", None, "Fazer análise de solo para próxima safra",              False),
]


async def seed_checklist_templates(session):
    """Cria os templates globais sem depender de tenants existentes."""
    try:
        return await _seed_checklist_templates(session)
    except Exception:
        await session.rollback()
        raise


async def _seed_checklist_templates(session):
    existing_items = {
        (fase, cultura, item.titulo): item
        for fase, cultura, item in (await session.execute(
            select(
                PhaseTemplate.fase,
                PhaseTemplate.cultura,
                PhaseTemplateChecklistItem,
            )
            .join(PhaseTemplate)
            .where(
                PhaseTemplate.tenant_id.is_(None),
                PhaseTemplate.is_system_default.is_(True),
            )
        )).tuples().all()
    }

    containers = {}
    ordens = {}
    inseridos = 0
    for fase, cultura, titulo, obrigatorio in TEMPLATES:
        container_key = (fase, cultura)
        ordem = ordens.get(container_key, 0)
        ordens[container_key] = ordem + 1

        key = (fase, cultura, titulo)
        if key in existing_items:
            if existing_items[key].ordem != ordem:
                existing_items[key].ordem = ordem
            continue

        container = containers.get(container_key)
        if container is None:
            container = (
                await session.execute(
                    select(PhaseTemplate).where(
                        PhaseTemplate.tenant_id.is_(None),
                        PhaseTemplate.cultura == cultura,
                        PhaseTemplate.fase == fase,
                        PhaseTemplate.is_system_default.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if container is None:
                container = PhaseTemplate(
                    tenant_id=None,
                    cultura=cultura,
                    fase=fase,
                    titulo=f"Template {fase}" + (f" - {cultura}" if cultura else ""),
                    is_system_default=True,
                    ativo=True,
                )
                session.add(container)
                await session.flush()
            containers[container_key] = container

        item = PhaseTemplateChecklistItem(
            phase_template_id=container.id,
            titulo=titulo,
            descricao=None,
            obrigatorio=obrigatorio,
            ordem=ordem,
            ativo=True,
        )
        session.add(item)
        existing_items[key] = item
        inseridos += 1

    await session.commit()
    return inseridos


async def seed():
    from sqlalchemy.orm import configure_mappers

    from core.model_registry import register_models

    register_models()
    configure_mappers()

    async with async_session_maker() as session:
        inseridos = await seed_checklist_templates(session)
        print(f"Seed concluído: {inseridos} itens de checklist inseridos.")


if __name__ == "__main__":
    asyncio.run(seed())
