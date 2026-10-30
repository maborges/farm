import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from core.models.billing import PlanoAssinatura

# Snapshot dos planos liberados para venda no banco de referência.
# O campo `ativo` é o que o painel administrativo alterna ao pausar vendas;
# planos inativos no banco de referência não fazem parte da carga inicial.
PLANOS_INICIAIS = (
    {
        "id": UUID("88e51b0f-b2ca-4142-9efc-81034226a072"),
        "nome": "Básico",
        "descricao": "Controle essencial da propriedade: cadastro de imóveis, planejamento de safra, caderno de campo, rebanho básico, tesouraria e frota. Ideal para quem quer sair do caderno de papel e ter visibilidade das operações.",
        "modulos_inclusos": [
            "CORE", "IMOVEIS_CADASTRO", "A1_PLANEJAMENTO", "A2_CAMPO",
            "P1_REBANHO", "F1_TESOURARIA", "O1_FROTA", "O2_ESTOQUE",
            "RH1_REMUNERACAO", "AM1_COMPLIANCE", "O4_BALANCA",
        ],
        "limite_usuarios_minimo": 1,
        "limite_usuarios_maximo": 2,
        "limite_hectares": Decimal("500.00"),
        "preco_mensal": Decimal("497.00"),
        "preco_anual": Decimal("4970.00"),
        "plan_tier": "BASICO",
        "max_fazendas": 5,
        "max_categorias_plano": 10,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": None,
        "destaque": False,
        "ordem": 0,
        "is_default": False,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("4aedd496-bc60-4155-a10e-732911f1c2cd"),
        "nome": "Empresa",
        "descricao": "Tudo do Profissional + agricultura de precisão (NDVI/IoT), pecuária leiteira avançada, hedging e futuros, avaliação patrimonial, IA Copilot Agrônoma, integração IoT com maquinário e bridge ERP corporativo. Sem limites.",
        "modulos_inclusos": [
            "CORE", "IMOVEIS_CADASTRO", "IMOVEIS_ARRENDAMENTOS",
            "A1_PLANEJAMENTO", "A2_CAMPO", "A3_DEFENSIVOS", "A5_COLHEITA",
            "P1_REBANHO", "P2_GENETICA", "P3_CONFINAMENTO", "P4_LEITE",
            "F1_TESOURARIA", "F2_CUSTOS_ABC", "F3_FISCAL", "O1_FROTA",
            "O2_ESTOQUE", "O3_COMPRAS", "RH1_REMUNERACAO", "RH2_SEGURANCA",
            "AM1_COMPLIANCE", "AM2_CARBONO", "A4_PRECISAO", "F4_HEDGING",
            "IMOVEIS_AVALIACAO", "EXT_IA", "EXT_IOT", "EXT_ERP", "O4_BALANCA",
        ],
        "limite_usuarios_minimo": 1,
        "limite_usuarios_maximo": 10,
        "limite_hectares": None,
        "preco_mensal": Decimal("4997.00"),
        "preco_anual": Decimal("49970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": 10,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": None,
        "destaque": False,
        "ordem": 0,
        "is_default": True,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("17c1f95a-9805-4736-821b-60fc28db1d5b"),
        "nome": "Profissional",
        "descricao": "Tudo do Básico + defensivos, colheita, genética, custos ABC, fiscal, compras, segurança do trabalho e gestão de carbono. Para quem quer controle total de custos por safra/talhão e compliance fiscal.",
        "modulos_inclusos": [
            "CORE", "A1_PLANEJAMENTO", "A2_CAMPO", "A3_DEFENSIVOS",
            "A4_PRECISAO", "A5_COLHEITA", "P1_REBANHO", "P2_GENETICA",
            "P3_CONFINAMENTO", "P4_LEITE", "F1_TESOURARIA", "F2_CUSTOS_ABC",
            "F3_FISCAL", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS",
            "RH1_REMUNERACAO", "RH2_SEGURANCA", "AM1_COMPLIANCE",
            "IMOVEIS_CADASTRO", "IMOVEIS_ARRENDAMENTOS", "O4_BALANCA",
        ],
        "limite_usuarios_minimo": 1,
        "limite_usuarios_maximo": 5,
        "limite_hectares": Decimal("500.00"),
        "preco_mensal": Decimal("1497.00"),
        "preco_anual": Decimal("14970.00"),
        "plan_tier": "PROFISSIONAL",
        "max_fazendas": 10,
        "max_categorias_plano": 10,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": None,
        "destaque": False,
        "ordem": 0,
        "is_default": False,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
)


async def seed_plans():
    async with async_session_maker() as session:
        created = await seed_plans_with_session(session)
        if created:
            print(f"Sucesso: {created} planos iniciais criados.")
        else:
            print("Planos iniciais já existem no banco de dados.")


async def seed_plans_with_session(session: AsyncSession) -> int:
    """Insere somente IDs do snapshot que ainda não existem."""
    plan_ids = [plan["id"] for plan in PLANOS_INICIAIS]
    result = await session.execute(
        select(PlanoAssinatura.id).where(PlanoAssinatura.id.in_(plan_ids))
    )
    existing_ids = set(result.scalars().all())

    novos_planos = [
        PlanoAssinatura(**plan)
        for plan in PLANOS_INICIAIS
        if plan["id"] not in existing_ids
    ]
    if not novos_planos:
        return 0

    session.add_all(novos_planos)
    await session.commit()
    return len(novos_planos)


if __name__ == "__main__":
    asyncio.run(seed_plans())
