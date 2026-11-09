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

from core.constants import ALL_MODULES
from core.database import async_session_maker
from core.models.billing import PlanoAssinatura

# Snapshot oficial dos 5 pacotes liberados para venda (Política All-In: todos os módulos inclusos).
# O valor varia pela soma do tamanho produtivo das propriedades (Hectares Equivalentes)
# e pela quantidade de acessos simultâneos na Web (App Campo é isento de simultaneidade).
PLANOS_INICIAIS = (
    {
        "id": UUID("11e51b0f-b2ca-4142-9efc-81034226a001"),
        "nome": "Familiar",
        "descricao": "100% dos módulos liberados (Agrícola, Pecuária, Financeiro, Fiscal, Estoque, Frota, RH, Ambiental e IA; extensões IoT e ERP contratadas à parte). Ideal para agricultura familiar e sítios até 100 ha equivalentes (ou 25 ha Café/HF; até 150 cabeças). App Campo offline ilimitado sem consumir acesso simultâneo.",
        "modulos_inclusos": list(ALL_MODULES),
        "limite_usuarios_minimo": 1,
        "limite_usuarios_maximo": 3,
        "limite_hectares": Decimal("100.00"),
        "preco_mensal": Decimal("197.00"),
        "preco_anual": Decimal("1970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": 1,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": "1 propriedade • Até 100 ha • 1 acesso simultâneo incluso (máx. 3) • App Campo livre",
        "destaque": False,
        "ordem": 1,
        "is_default": False,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("88e51b0f-b2ca-4142-9efc-81034226a072"),
        "nome": "Pequeno Produtor",
        "descricao": "100% dos módulos liberados para propriedades em crescimento até 500 ha equivalentes (ou 120 ha Café/HF; até 600 cabeças). Inclui 2 acessos simultâneos na Web e uso livre no aplicativo Campo.",
        "modulos_inclusos": list(ALL_MODULES),
        "limite_usuarios_minimo": 2,
        "limite_usuarios_maximo": 6,
        "limite_hectares": Decimal("500.00"),
        "preco_mensal": Decimal("497.00"),
        "preco_anual": Decimal("4970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": 2,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": "Até 2 propriedades • Até 500 ha • 2 acessos simultâneos inclusos (máx. 6) • App Campo livre",
        "destaque": False,
        "ordem": 2,
        "is_default": False,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("17c1f95a-9805-4736-821b-60fc28db1d5b"),
        "nome": "Médio Produtor",
        "descricao": "100% dos módulos liberados para fazendas estruturadas até 2.000 ha equivalentes (ou 500 ha Café/HF; até 2.500 cabeças). Inclui 5 acessos simultâneos na Web e uso livre no aplicativo Campo.",
        "modulos_inclusos": list(ALL_MODULES),
        "limite_usuarios_minimo": 5,
        "limite_usuarios_maximo": 15,
        "limite_hectares": Decimal("2000.00"),
        "preco_mensal": Decimal("1197.00"),
        "preco_anual": Decimal("11970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": 5,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": "Até 5 propriedades • Até 2.000 ha • 5 acessos simultâneos inclusos (máx. 15) • App Campo livre",
        "destaque": True,
        "ordem": 3,
        "is_default": True,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("33c1f95a-9805-4736-821b-60fc28db1d04"),
        "nome": "Grande Produtor",
        "descricao": "100% dos módulos liberados para operações de alta escala até 6.000 ha equivalentes (ou 1.500 ha Café/HF; até 8.000 cabeças). Inclui 10 acessos simultâneos na Web e uso livre no aplicativo Campo.",
        "modulos_inclusos": list(ALL_MODULES),
        "limite_usuarios_minimo": 10,
        "limite_usuarios_maximo": 30,
        "limite_hectares": Decimal("6000.00"),
        "preco_mensal": Decimal("2497.00"),
        "preco_anual": Decimal("24970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": 10,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": "Até 10 propriedades • Até 6.000 ha • 10 acessos simultâneos inclusos (máx. 30) • App Campo livre",
        "destaque": False,
        "ordem": 4,
        "is_default": False,
        "ativo": True,
        "disponivel_site": True,
        "disponivel_crm": True,
    },
    {
        "id": UUID("4aedd496-bc60-4155-a10e-732911f1c2cd"),
        "nome": "Grupo",
        "descricao": "100% dos módulos liberados para holdings, grupos agrícolas, usinas e cooperativas sem limite de área ou propriedades. Inclui 20 acessos simultâneos na Web, expansão ilimitada e uso livre no aplicativo Campo.",
        "modulos_inclusos": list(ALL_MODULES),
        "limite_usuarios_minimo": 20,
        "limite_usuarios_maximo": None,
        "limite_hectares": None,
        "preco_mensal": Decimal("4997.00"),
        "preco_anual": Decimal("49970.00"),
        "plan_tier": "ENTERPRISE",
        "max_fazendas": -1,
        "max_categorias_plano": 200,
        "tem_trial": True,
        "dias_trial": 15,
        "is_free": False,
        "descricao_marketing": "Propriedades e Hectares ilimitados • 20 acessos simultâneos inclusos (expansão ilimitada) • App Campo livre",
        "destaque": False,
        "ordem": 5,
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
    """Insere IDs do snapshot que ainda não existem e migra registros legados (Básico/Profissional/Empresa)."""
    plan_ids = [plan["id"] for plan in PLANOS_INICIAIS]
    result = await session.execute(
        select(PlanoAssinatura).where(PlanoAssinatura.id.in_(plan_ids))
    )
    existing_by_id = {row.id: row for row in result.scalars().all()}

    nomes_legados = {"básico", "basico", "profissional", "empresa"}
    alterados = 0

    for plan_data in PLANOS_INICIAIS:
        existing = existing_by_id.get(plan_data["id"])
        if existing is None:
            session.add(PlanoAssinatura(**plan_data))
            alterados += 1
        elif (existing.nome or "").strip().lower() in nomes_legados:
            for field, value in plan_data.items():
                if field != "id":
                    setattr(existing, field, value)
            alterados += 1

    if alterados == 0:
        return 0

    await session.commit()
    return alterados


if __name__ == "__main__":
    asyncio.run(seed_plans())
