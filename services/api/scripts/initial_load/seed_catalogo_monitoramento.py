"""Carga do catálogo fitossanitário global para monitoramento.

Os limites de dano econômico dependem da cultura, fase, finalidade e método de
amostragem. Por isso, o catálogo inicial não publica NDEs sem validação técnica.
"""
import asyncio
from sqlalchemy import select
from core.database import async_session_maker
from agricola.monitoramento.catalogo_model import MonitoramentoCatalogo

# NDE padrão mantido como None enquanto os valores não tiverem contexto e
# validação técnica. unidade_medida informa apenas a forma de registrar a
# observação, não um limiar de controle.
ENTRADAS = [
    # PRAGAS — Soja
    dict(tipo="PRAGA", nome_popular="Lagarta-da-soja", nome_cientifico="Anticarsia gemmatalis", cultura="Soja", nde_padrao=None, unidade_medida="lagartas/pano"),
    dict(tipo="PRAGA", nome_popular="Lagarta-do-cartucho", nome_cientifico="Spodoptera frugiperda", cultura="Milho", nde_padrao=None, unidade_medida="lagartas/planta"),
    dict(tipo="PRAGA", nome_popular="Percevejo-marrom", nome_cientifico="Euschistus heros", cultura="Soja", nde_padrao=None, unidade_medida="percevejos/pano"),
    dict(tipo="PRAGA", nome_popular="Percevejo-verde", nome_cientifico="Nezara viridula", cultura="Soja", nde_padrao=None, unidade_medida="percevejos/pano"),
    dict(tipo="PRAGA", nome_popular="Mosca-branca", nome_cientifico="Bemisia tabaci", cultura=None, nde_padrao=None, unidade_medida="adultos/folha"),
    dict(tipo="PRAGA", nome_popular="Pulgão-do-trigo", nome_cientifico="Schizaphis graminum", cultura="Trigo", nde_padrao=None, unidade_medida="pulgões/afilho"),
    dict(tipo="PRAGA", nome_popular="Cigarrinha-das-raízes", nome_cientifico="Deois flavopicta", cultura=None, nde_padrao=None, unidade_medida="ninfas/m²"),
    dict(tipo="PRAGA", nome_popular="Spodoptera cosmioides", nome_cientifico="Spodoptera cosmioides", cultura="Soja", nde_padrao=None, unidade_medida="lagartas/pano"),
    dict(tipo="PRAGA", nome_popular="Helicoverpa armigera", nome_cientifico="Helicoverpa armigera", cultura=None, nde_padrao=None, unidade_medida="lagartas/pano"),
    dict(tipo="PRAGA", nome_popular="Ácaro-rajado", nome_cientifico="Tetranychus urticae", cultura=None, nde_padrao=None, unidade_medida="% folhas infestadas"),
    dict(tipo="PRAGA", nome_popular="Broca-da-soja", nome_cientifico="Epinotia aporema", cultura="Soja", nde_padrao=None, unidade_medida="% plantas atacadas"),
    dict(tipo="PRAGA", nome_popular="Tamanduá-da-soja", nome_cientifico="Sternechus subsignatus", cultura="Soja", nde_padrao=None, unidade_medida="adultos/m"),
    dict(tipo="PRAGA", nome_popular="Elasmo", nome_cientifico="Elasmopalpus lignosellus", cultura="Milho", nde_padrao=None, unidade_medida="% plantas atacadas"),

    # DOENÇAS — Soja
    dict(tipo="DOENCA", nome_popular="Ferrugem Asiática", nome_cientifico="Phakopsora pachyrhizi", cultura="Soja", nde_padrao=None, unidade_medida="% área foliar afetada"),
    dict(tipo="DOENCA", nome_popular="Mancha-alvo", nome_cientifico="Corynespora cassiicola", cultura="Soja", nde_padrao=None, unidade_medida="% área foliar afetada"),
    dict(tipo="DOENCA", nome_popular="Antracnose", nome_cientifico="Colletotrichum truncatum", cultura="Soja", nde_padrao=None, unidade_medida="% plantas afetadas"),
    dict(tipo="DOENCA", nome_popular="Mofo-branco", nome_cientifico="Sclerotinia sclerotiorum", cultura=None, nde_padrao=None, unidade_medida="% plantas afetadas"),
    dict(tipo="DOENCA", nome_popular="Oídio", nome_cientifico="Erysiphe diffusa", cultura="Soja", nde_padrao=None, unidade_medida="% área foliar afetada"),
    dict(tipo="DOENCA", nome_popular="Cercospora", nome_cientifico="Cercospora kikuchii", cultura="Soja", nde_padrao=None, unidade_medida="% área foliar afetada"),
    dict(tipo="DOENCA", nome_popular="Podridão-vermelha-da-raiz", nome_cientifico="Fusarium virguliforme", cultura="Soja", nde_padrao=None, unidade_medida="% plantas afetadas"),
    dict(tipo="DOENCA", nome_popular="Ferrugem-da-folha do Trigo", nome_cientifico="Puccinia triticina", cultura="Trigo", nde_padrao=None, unidade_medida="% área foliar afetada"),
    dict(tipo="DOENCA", nome_popular="Giberela", nome_cientifico="Fusarium graminearum", cultura="Trigo", nde_padrao=None, unidade_medida="% espigas afetadas"),
    dict(tipo="DOENCA", nome_popular="Mancha-de-turcicum", nome_cientifico="Exserohilum turcicum", cultura="Milho", nde_padrao=None, unidade_medida="% área foliar afetada"),

    # PLANTAS DANINHAS
    dict(tipo="PLANTA_DANINHA", nome_popular="Buva", nome_cientifico="Conyza spp.", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Capim-amargoso", nome_cientifico="Digitaria insularis", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Leiteiro", nome_cientifico="Euphorbia heterophylla", cultura="Soja", nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Capim-pé-de-galinha", nome_cientifico="Eleusine indica", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Picão-preto", nome_cientifico="Bidens pilosa", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Caruru", nome_cientifico="Amaranthus hybridus", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Nabiça", nome_cientifico="Raphanus raphanistrum", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
    dict(tipo="PLANTA_DANINHA", nome_popular="Trapoeraba", nome_cientifico="Commelina benghalensis", cultura=None, nde_padrao=None, unidade_medida="plantas/m²"),
]


async def _seed_catalogo(session) -> tuple[int, int]:
    result = await session.execute(
        select(
            MonitoramentoCatalogo.tipo,
            MonitoramentoCatalogo.nome_popular,
            MonitoramentoCatalogo.cultura,
        ).where(
            MonitoramentoCatalogo.tenant_id.is_(None),
            MonitoramentoCatalogo.is_system.is_(True),
        )
    )
    existing = {tuple(row) for row in result.all()}

    inseridos = 0
    for entrada in ENTRADAS:
        chave = (
            entrada["tipo"],
            entrada["nome_popular"],
            entrada["cultura"],
        )
        if chave in existing:
            continue

        session.add(MonitoramentoCatalogo(
            tenant_id=None,
            is_system=True,
            ativo=True,
            **entrada,
        ))
        existing.add(chave)
        inseridos += 1

    await session.commit()
    return inseridos, len(ENTRADAS) - inseridos


async def seed():
    async with async_session_maker() as session:
        inseridos, existentes = await _seed_catalogo(session)
    print(
        f"Carga concluída: {inseridos} entradas globais inseridas "
        f"({existentes} já existiam)."
    )


if __name__ == "__main__":
    asyncio.run(seed())
