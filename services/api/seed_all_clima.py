import asyncio
import random
from datetime import date, timedelta
from loguru import logger

from core.database import get_db_session
from sqlalchemy import select
from core.models.unidade_produtiva import UnidadeProdutiva
from agricola.climatico.models import RegistroClima

async def seed_clima_data():
    db = await get_db_session()
    try:
        stmt = select(UnidadeProdutiva)
        result = await db.execute(stmt)
        ups = result.scalars().all()

        hoje = date.today()
        
        for up in ups:
            logger.info(f"Gerando dados para UP {up.id} ({up.nome})")
            for i in range(30):
                data_reg = hoje - timedelta(days=30 - i)
                base_temp = 25.0 + random.uniform(-3, 3)
                t_max = base_temp + random.uniform(2, 6)
                t_min = base_temp - random.uniform(2, 5)
                t_med = (t_max + t_min) / 2
                
                choveu = random.random() < 0.3
                chuva = random.uniform(5, 45) if choveu else 0.0
                
                umidade = random.uniform(70, 95) if choveu else random.uniform(40, 85)
                vento = random.uniform(5, 25)
                
                registro = RegistroClima(
                    tenant_id=up.tenant_id,
                    unidade_produtiva_id=up.id,
                    data_registro=data_reg,
                    precipitacao_mm=round(chuva, 2),
                    temp_max_c=round(t_max, 2),
                    temp_min_c=round(t_min, 2),
                    temp_media_c=round(t_med, 2),
                    umidade_rel_pct=round(umidade, 2),
                    evapotranspiracao_mm=round(random.uniform(2, 6), 2),
                    vento_kmh=round(vento, 2),
                    gdu_calculado=round(max(0, t_med - 10), 2),
                    fonte="OPENWEATHER_SIMULATION"
                )
                
                check_stmt = select(RegistroClima).where(
                    RegistroClima.unidade_produtiva_id == up.id,
                    RegistroClima.data_registro == data_reg
                )
                existing = (await db.execute(check_stmt)).scalar_one_or_none()
                if not existing:
                    db.add(registro)

        await db.commit()
        logger.info("FIM")
    except Exception as e:
        logger.error(e)
    finally:
        await db.close()

asyncio.run(seed_clima_data())
