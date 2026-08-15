import asyncio

from loguru import logger


async def run_suspender_vencidos_loop() -> None:
    from core.database import async_session_maker
    from core.services.assinatura_service import suspender_trials_expirados, suspender_vencidos

    while True:
        try:
            await asyncio.sleep(3600)
            async with async_session_maker() as session:
                vencidos = await suspender_vencidos(session)
                trials = await suspender_trials_expirados(session)
                if vencidos or trials:
                    logger.info(f"[job] suspendidos: {vencidos} vencidos, {trials} trials")
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[job] suspender_vencidos erro: {exc}")


async def run_resumo_diario_loop() -> None:
    from notificacoes.resumo_diario_envio_service import EnvioResumoDiarioService

    while True:
        try:
            await EnvioResumoDiarioService.enviar_resumos_agendados()
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[job] resumo_diario erro: {exc}")
            await asyncio.sleep(60)


async def run_erp_sync_loop() -> None:
    """Executar políticas ERP agendadas no worker oficial de background."""
    from integracoes.erp.scheduler import run_scheduled_erp_cycle

    while True:
        try:
            executed = await run_scheduled_erp_cycle()
            if executed:
                logger.info(f"[job] sincronizações ERP executadas: {executed}")
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[job] sincronização ERP erro: {exc}")
        await asyncio.sleep(60)


async def run_marcar_vencidos_loop() -> None:
    """Marca receituários agronômicos e devoluções de embalagens vencidos por data.

    Sem esse job, `status` ficava indefinidamente em EMITIDO/PENDENTE mesmo com a
    data de validade/prazo já ultrapassada — o vencimento só era percebido em
    checagens de runtime pontuais, nunca refletido no dado persistido
    (OPERATIONS-GAP-01 §21.25).
    """
    from core.database import async_session_maker
    from agricola.receituario_agronomico.vencimento_service import marcar_receituarios_vencidos
    from agricola.logistica_reversa_embalagens.vencimento_service import marcar_devolucoes_vencidas

    while True:
        try:
            await asyncio.sleep(3600)
            async with async_session_maker() as session:
                receituarios = await marcar_receituarios_vencidos(session)
                embalagens = await marcar_devolucoes_vencidas(session)
                if receituarios or embalagens:
                    logger.info(
                        f"[job] vencidos marcados: {receituarios} receituário(s), {embalagens} devolução(ões)"
                    )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"[job] marcar_vencidos erro: {exc}")


async def run_recommendation_scheduler_loop() -> None:
    """Execute the canonical recommendation scheduler through the shared worker."""
    from recommendations.scheduler import run_scheduled_recommendation_cycle

    while True:
        try:
            executed = await run_scheduled_recommendation_cycle()
            logger.bind(component="background_jobs", tenants_executed=executed).info(
                "recommendation_scheduler_cycle_finished"
            )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.bind(component="background_jobs").exception(
                "recommendation_scheduler_cycle_failed",
                exception_type=exc.__class__.__name__,
            )
        await asyncio.sleep(300)


async def run_background_jobs() -> None:
    tasks = [
        asyncio.create_task(run_suspender_vencidos_loop()),
        asyncio.create_task(run_resumo_diario_loop()),
        asyncio.create_task(run_erp_sync_loop()),
        asyncio.create_task(run_recommendation_scheduler_loop()),
        asyncio.create_task(run_marcar_vencidos_loop()),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
