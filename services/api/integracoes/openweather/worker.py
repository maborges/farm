import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from loguru import logger

from core.database import get_db_session
from integracoes.models import IntegrationScope, TenantIntegracao, MarketplaceIntegracao
from core.models.unidade_produtiva import UnidadeProdutiva
from integracoes.openweather.services import OpenWeatherService

async def process_openweather_sync():
    """Busca tenants com OpenWeather ativo e dispara a sincronização se necessário, respeitando a periodicidade e cotas."""
    db = await get_db_session()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Encontra configurações ativas do OpenWeather
        stmt = select(TenantIntegracao).join(
            MarketplaceIntegracao, TenantIntegracao.integracao_id == MarketplaceIntegracao.id
        ).where(
            TenantIntegracao.status == "ativa",
            TenantIntegracao.deleted_at.is_(None),
            MarketplaceIntegracao.slug == "openweather"
        )
        result = await db.execute(stmt)
        configs = result.scalars().all()

        for config in configs:
            try:
                tenant_id = str(config.tenant_id)
                unidade_produtiva_id = (
                    config.scope_id
                    if config.scope_type == IntegrationScope.UNIDADE_PRODUTIVA.value
                    else None
                )
                
                # Extrai preferências de config do credenciais ou configuracoes
                payload = config.configuracoes or {}
                conn_payload = config.credenciais or {}
                
                daily_quota = int(payload.get("daily_quota", conn_payload.get("daily_quota", 1000)))
                sync_freq = int(payload.get("sync_frequency_minutes", conn_payload.get("sync_frequency_minutes", 60)))
                
                # Conta UPs ativas para o tenant
                up_stmt = select(func.count(UnidadeProdutiva.id)).where(
                    UnidadeProdutiva.tenant_id == tenant_id,
                    UnidadeProdutiva.deleted_at.is_(None)
                )
                up_result = await db.execute(up_stmt)
                ups_count = max(1, up_result.scalar() or 1)
                
                # Calcula a frequência segura
                calls_per_up = max(1, daily_quota // ups_count)
                min_safe_freq = max(15, 1440 // calls_per_up)
                
                # Frequência final a ser usada
                actual_freq = max(sync_freq, min_safe_freq)
                
                last_sync = config.ultima_sincronizacao
                
                if not last_sync or (now - last_sync).total_seconds() >= (actual_freq * 60):
                    logger.info(f"Executando sync OpenWeather para tenant {tenant_id}. Frequência aplicada: {actual_freq} min")
                    
                    svc = OpenWeatherService(db)
                    if unidade_produtiva_id:
                        await svc.sincronizar_clima_unidade(tenant_id, unidade_produtiva_id)
                    else:
                        await svc.sincronizar_clima_atual(tenant_id)
                    
                    # Verifica última previsão do tempo (6 horas de carência)
                    from agricola.climatico.models import PrevisaoClima
                    from sqlalchemy import desc
                    
                    stmt_prev = select(PrevisaoClima.atualizado_em).where(
                        PrevisaoClima.tenant_id == tenant_id
                    ).order_by(desc(PrevisaoClima.atualizado_em)).limit(1)
                    
                    last_prev = (await db.execute(stmt_prev)).scalar()
                    
                    if not last_prev or (now - last_prev).total_seconds() >= (6 * 3600):
                        logger.info(f"Executando sync de previsão OpenWeather para tenant {tenant_id}.")
                        if unidade_produtiva_id:
                            await svc.sincronizar_previsao_unidade(tenant_id, unidade_produtiva_id)
                        else:
                            await svc.sincronizar_previsao_atual(tenant_id)
                    
            except Exception as e:
                await db.rollback()
                logger.error(f"Erro ao sincronizar OpenWeather para o tenant {config.tenant_id}: {e}")
                
    except Exception as e:
        logger.error(f"Erro no loop do worker OpenWeather: {e}")
    finally:
        await db.close()
