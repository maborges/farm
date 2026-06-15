#!/usr/bin/env python3
"""
Job Diário: Geração de Snapshots do Mark-to-Market de Hedge V2.
EXECUTION-HEDGE-04A

Deve ser executado ao fim do dia (D-0) ou início do dia seguinte (D+1).
Exemplo Cron (00:30 BRT):
    30 0 * * * cd /opt/lampp/htdocs/farm/services/api && .venv/bin/python scripts/jobs/gerar_snapshots_mtm.py

Argumentos:
    --data: Forçar data de referência (YYYY-MM-DD). Padrão: Hoje.
"""
import sys
import asyncio
import argparse
from datetime import date
from loguru import logger

sys.path.insert(0, '.')

from core.config import settings


async def run(data_ref: date):
    import asyncpg
    from core.database import async_session_maker
    from financeiro.hedge.snapshot_service import HedgeSnapshotService

    url = str(settings.database_url).replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)

    # Buscar todos os tenants ativos
    tenants = await conn.fetch("SELECT id FROM tenants WHERE ativo = true")
    
    if not tenants:
        logger.warning("Nenhum tenant ativo encontrado.")
        await conn.close()
        return

    logger.info(f"📸 Gerando Snapshots de MtM (Hedge V2) para {len(tenants)} tenant(s) | Data: {data_ref.isoformat()}")

    total_snapshots = 0
    total_falhas = 0

    for tenant in tenants:
        tenant_id = tenant["id"]
        async with async_session_maker() as session:
            svc = HedgeSnapshotService(session)
            try:
                sucesso_count = await svc.processar_tenant(tenant_id, data_ref)
                alertas_count = await svc.processar_alertas_tenant(tenant_id, data_ref)
                await session.commit()
                total_snapshots += sucesso_count
                logger.info(f"Tenant {tenant_id}: {sucesso_count} snapshots, {alertas_count} alertas.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Falha ao processar tenant {tenant_id}: {e}")
                total_falhas += 1

    await conn.close()

    logger.info("=" * 60)
    logger.info(f"Resultado Final: {total_snapshots} Snapshots Sucesso | {total_falhas} Tenants com Falha")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar Snapshots MtM de Hedge Diários")
    parser.add_argument("--data", help="Data de referência no formato YYYY-MM-DD", type=str)
    args = parser.parse_args()

    try:
        data_referencia = date.fromisoformat(args.data) if args.data else date.today()
    except ValueError:
        logger.error("Data inválida. Use o formato YYYY-MM-DD.")
        sys.exit(1)

    asyncio.run(run(data_ref=data_referencia))
