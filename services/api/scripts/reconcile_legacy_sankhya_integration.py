"""Reconcilia `SankhyaConfig` legado com o runtime canônico de Integrações."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

import core.models  # noqa: F401
from core.database import async_session_maker
from integracoes.sankhya.services.legacy_reconciliation import (
    LegacySankhyaReconciliationResult,
    SankhyaLegacyReconciliationService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconciliação idempotente de SankhyaConfig legado com TenantIntegracao"
    )
    parser.add_argument(
        "--tenant-id",
        action="append",
        dest="tenant_ids",
        help="Tenant alvo. Pode ser informado mais de uma vez.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Processa todos os tenants candidatos descobertos no banco.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Materializa o runtime canônico. Sem essa flag o comando roda em dry-run.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Interrompe na primeira reconciliação bloqueada.",
    )
    return parser.parse_args()


def _summarize(results: list[LegacySankhyaReconciliationResult], *, dry_run: bool) -> None:
    counts = Counter(result.state_before for result in results)
    logger.info("Resumo da reconciliação Sankhya")
    logger.info("Modo dry-run: {}", "sim" if dry_run else "nao")
    logger.info("Total processado: {}", len(results))
    logger.info("States: {}", dict(sorted(counts.items())))
    logger.info("Materializados: {}", sum(1 for result in results if result.changed))
    logger.info("Bloqueados: {}", sum(1 for result in results if result.blocked))


async def main() -> int:
    args = parse_args()
    dry_run = not args.execute

    async with async_session_maker() as session:
        service = SankhyaLegacyReconciliationService(session)
        tenant_ids = args.tenant_ids
        if args.all or not tenant_ids:
            tenant_ids = await service.list_candidate_tenant_ids()
        if not tenant_ids:
            logger.info("Nenhum tenant candidato encontrado.")
            return 0

        results = await service.reconcile_many(
            tenant_ids,
            dry_run=dry_run,
            stop_on_error=args.stop_on_error,
        )

    for result in results:
        logger.info(
            "tenant={} state_before={} state_after={} action={} blocked={} changed={}",
            result.tenant_id,
            result.state_before,
            result.state_after,
            result.action,
            result.blocked,
            result.changed,
        )
    _summarize(results, dry_run=dry_run)
    return 0 if all(not result.blocked for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
