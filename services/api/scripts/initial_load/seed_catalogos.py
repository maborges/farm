"""Executa os catálogos globais já revisados para a carga inicial."""

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from clean_install.seed_contract import apply_seeds  # noqa: E402
from core.database import engine  # noqa: E402

CATALOGOS_APROVADOS = (
    "units",
    "product_categories",
    "operation_phases",
    "relationship_types",
    "service_types",
)


async def seed_catalogos():
    async with engine.begin() as connection:
        inserted = await connection.run_sync(
            lambda sync_connection: apply_seeds(
                sync_connection,
                catalogs=CATALOGOS_APROVADOS,
            )
        )
    total = sum(inserted.values())
    print(
        "Catálogos globais verificados: "
        f"{inserted['units']} unidades e "
        f"{inserted['product_categories']} categorias e "
        f"{inserted['operation_phases']} tipos de operação e "
        f"{inserted['relationship_types']} tipos de relacionamento e "
        f"{inserted['service_types']} tipos de serviço inseridos; "
        f"total {total}."
    )
    return inserted


if __name__ == "__main__":
    asyncio.run(seed_catalogos())
