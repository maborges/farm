import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from loguru import logger

from agricola.cultivos.models import Cultivo  # noqa: F401 - registra relacionamentos do ORM
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


async def run_alerts_check():
    """Roda os dois motores de alertas automáticos, em sessões isoladas.

    Nenhum dos dois era chamado automaticamente antes (só via endpoint admin
    manual `POST /notificacoes/alertas/verificar` para o primeiro; o segundo
    nunca era chamado em lugar nenhum de produção). Ver memória do projeto
    project_tres_sistemas_alertas_mapeados para o histórico da duplicação.
    """
    from notificacoes.alertas_engine import AlertasEngine
    from alert_engine.scheduler import run_scheduled_alerts as run_alert_engine_scheduler

    db = await get_db_session()
    try:
        resultado = await AlertasEngine().verificar_todos_tenants()
        logger.info(f"AlertasEngine: {resultado}")
    except Exception as e:
        logger.error(f"Erro no AlertasEngine (notificacoes): {e}")

    try:
        # Domínio FIELD (campo_generator.py) desativado temporariamente: dados reais
        # têm tarefas de campo com unidade_produtiva_id órfão (FK violation),
        # confirmado em execução manual em 2026-08-14 — campo_generator.run() não
        # isola por item, uma tarefa corrompida derruba o generator inteiro e
        # repete a cada ciclo do worker (~10min) até virar incidente. Coberto pela
        # iniciativa TENANT-FK-REPAIR (memória do projeto), ainda não executada.
        # Reativar depois do repair, ou depois de blindar campo_generator por item.
        resultado_alert_engine = await run_alert_engine_scheduler(
            db, domains=["AGRICULTURE", "LIVESTOCK", "FINANCE", "SYSTEM"]
        )
        # run_scheduled_alerts não comita internamente — quem chama é responsável.
        # Sem isso, os inserts em operational_alerts ficam pendentes e são
        # descartados no db.close() (confirmado: 92 Notificacao criadas via
        # _notificar_usuarios, mas 0 operational_alerts persistidos na 1ª execução real).
        await db.commit()
        logger.info(f"alert_engine scheduler: {resultado_alert_engine}")
    except Exception as e:
        logger.error(f"Erro no alert_engine scheduler: {e}")
    finally:
        await db.close()


async def run_worker_loop(interval: int = 60, alerts_check_every_n_cycles: int = 10):
    """Ciclo padrão a cada `interval`s; alertas automáticos rodam a cada
    `alerts_check_every_n_cycles` ciclos (não precisam da mesma cadência de
    automações/follow-ups — são varreduras mais pesadas, diárias por natureza)."""
    logger.info(f"Iniciando Scheduler Worker de Automações. Ciclo: {interval}s")
    ciclo = 0
    while True:
        await process_automations()
        await run_followup_check()
        ciclo += 1
        if ciclo % alerts_check_every_n_cycles == 0:
            await run_alerts_check()
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
