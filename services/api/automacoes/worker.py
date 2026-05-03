import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from loguru import logger

from core.database import get_db_session
from automacoes.models import AutomacaoConfiguracao
from automacoes.service import AutomacoesService, _calcular_proxima_execucao
from automacoes.followup_worker import process_followups

async def process_automations():
    """Busca regras vencidas e executa automações, atualizando a próxima execução."""
    db = await get_db_session()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(AutomacaoConfiguracao).where(
            AutomacaoConfiguracao.ativa == True,
            AutomacaoConfiguracao.frequencia != "MANUAL",
            AutomacaoConfiguracao.proxima_execucao <= now
        )
        
        result = await db.execute(stmt)
        configs = result.scalars().all()
        
        if not configs:
            return

        logger.info(f"Encontradas {len(configs)} regras de automação agendadas para execução.")

        for cfg in configs:
            try:
                # O processamento deve ter tenant e safra definidos
                if not cfg.safra_id:
                    continue

                logger.info(f"Processando regra '{cfg.regra}' (Tenant: {cfg.tenant_id}, Safra: {cfg.safra_id})")
                
                # Executa a automação
                svc = AutomacoesService(db, cfg.tenant_id)
                res = await svc.executar(cfg.safra_id)
                
                # Recalcula e salva nova data
                nova_data = _calcular_proxima_execucao(cfg.frequencia)
                cfg.proxima_execucao = nova_data
                await db.commit()
                
                logger.info(
                    f"Sucesso na regra '{cfg.regra}'. Ações: {res.acoes_criadas}, "
                    f"Notificações: {res.notificacoes_criadas}. Próxima execução: {nova_data}"
                )

            except Exception as e:
                logger.error(f"Erro ao executar automação '{cfg.regra}' para safra {cfg.safra_id}: {e}")
                await db.rollback()

    except Exception as e:
        logger.error(f"Erro no loop do worker de automações: {e}")
    finally:
        await db.close()

async def run_followup_check():
    """Executa a verificação de follow-ups pendentes em sessão isolada."""
    db = await get_db_session()
    try:
        await process_followups(db)
    except Exception as e:
        logger.error(f"Erro no worker de follow-ups: {e}")
    finally:
        await db.close()


async def run_worker_loop(interval: int = 60):
    logger.info(f"Iniciando Scheduler Worker de Automações. Ciclo: {interval}s")
    while True:
        await process_automations()
        await run_followup_check()
        await asyncio.sleep(interval)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker de automações parado pelo usuário.")
    finally:
        # Garante limpeza da pool de conexões antes de sair
        from core.database import engine
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(engine.dispose())
            logger.info("Database engine disposed in worker.")
        except Exception as e:
            logger.error(f"Erro ao fechar engine no worker: {e}")
        finally:
            loop.close()
