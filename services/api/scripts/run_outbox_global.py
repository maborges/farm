import asyncio
import logging
import sys
from sqlalchemy import text
from core.database import get_db_session
from events.outbox_worker import run_outbox_relay_once

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox_global")

async def run_global_outbox() -> int:
    logger.info("Iniciando varredura global do Outbox para todos os tenants...")
    db = await get_db_session()
    
    try:
        # Busca todos os tenants ativos no sistema
        result = await db.execute(text("SELECT id FROM tenants WHERE ativo = true;"))
        tenants = result.scalars().all()
    except Exception as e:
        logger.error(f"Erro ao buscar tenants: {e}")
        await db.close()
        return 1
        
    if not tenants:
        logger.info("Nenhum tenant ativo encontrado.")
        await db.close()
        return 0

    logger.info(f"Encontrados {len(tenants)} tenants ativos. Verificando eventos pendentes...")
    
    # Suprime logs verbosos do relay
    import logging as py_logging
    py_logging.getLogger("events.outbox_worker").setLevel(py_logging.WARNING)
    py_logging.getLogger("events.outbox_relay").setLevel(py_logging.WARNING)

    total_processed = 0
    tenants_with_events = 0
    tenants_failed = 0

    try:
        for tenant_id in tenants:
            tid_str = str(tenant_id)
            try:
                # Verifica há eventos pendentes usando o contexto RLS do tenant.
                await db.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                    {"tid": tid_str},
                )
                check_stmt = text("SELECT 1 FROM domain_event_outbox WHERE status = 'PENDING' LIMIT 1")
                has_pending = await db.execute(check_stmt)
                if not has_pending.first():
                    continue

                tenants_with_events += 1
                result_relay = await run_outbox_relay_once(
                    session_factory=get_db_session,
                    batch_size=50,
                    tenant_id=tid_str,
                    locked_by="global-outbox-cron",
                )

                if result_relay.total_claimed > 0:
                    total_processed += result_relay.total_processed
                    logger.info(
                        f"Tenant {tid_str}: Processados {result_relay.total_processed} eventos "
                        f"(Total Claimed: {result_relay.total_claimed})"
                    )
            except Exception:
                tenants_failed += 1
                await db.rollback()
                logger.exception(f"Falha ao processar Outbox do tenant {tid_str}")
    finally:
        await db.close()
            
    logger.info(
        f"Varredura global concluída. {tenants_with_events} tenants tinham eventos. "
        f"Total de eventos processados: {total_processed}. Falhas: {tenants_failed}"
    )
    return 1 if tenants_failed else 0

if __name__ == "__main__":
    sys.exit(asyncio.run(run_global_outbox()))
