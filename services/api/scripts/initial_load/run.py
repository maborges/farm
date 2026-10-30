"""Orquestra as cargas globais iniciais, sem criar schema ou dados de tenant."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
API_ROOT = Path(__file__).resolve().parents[2]
for import_root in (SCRIPTS_DIR, API_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="executa as cargas; sem esta opção, somente exibe o plano",
    )
    return parser.parse_args()


async def run_initial_load() -> None:
    from core.database import async_session_maker
    from initial_load import (
        seed_catalogos,
        seed_crm_estagios,
        seed_kb,
        seed_perfis,
        seed_plans,
    )

    print("[1/8] Catálogos globais revisados")
    await seed_catalogos.seed_catalogos()

    print("[2/8] Perfis globais")
    await seed_perfis.seed_perfis()

    print("[3/8] Planos de assinatura")
    await seed_plans.seed_plans()

    from initial_load import seed_culturas, seed_parametros_solo

    print("[4/8] Culturas globais")
    await seed_culturas.run_seed()

    print("[5/8] Parâmetros de interpretação de solo")
    await seed_parametros_solo.run_seed()

    print("[6/8] Estágios padrão do pipeline CRM")
    async with async_session_maker() as session:
        await seed_crm_estagios.seed_estagios_crm(session)

    print("[7/8] Base de Conhecimento pública")
    await seed_kb.seed_kb()

    from initial_load import seed_admin

    print("[8/8] Identidade administrativa e templates de e-mail")
    await seed_admin.seed_admin_user()
    await seed_admin.seed_email_templates()


def main() -> None:
    args = parse_args()
    if not args.execute:
        print("Plano de carga inicial (modo de visualização; nada foi gravado):")
        print("  1. initial_load/seed_catalogos.py (catálogos globais revisados)")
        print("  2. initial_load/seed_perfis.py")
        print("  3. initial_load/seed_plans.py (planos de assinatura)")
        print("  4. initial_load/seed_culturas.py")
        print("  5. initial_load/seed_parametros_solo.py (depende das culturas)")
        print("  6. initial_load/seed_crm_estagios.py (estágios padrão do pipeline CRM)")
        print(
            "  7. initial_load/seed_kb.py "
            "(categorias e artigos públicos da Base de Conhecimento)"
        )
        print("  8. initial_load/seed_admin.py (admin_users, usuarios e templates de e-mail)")
        print("Use --execute após confirmar o banco de destino e o schema.")
        return

    asyncio.run(run_initial_load())


if __name__ == "__main__":
    main()
