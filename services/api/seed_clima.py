import asyncio
import random
from datetime import date, timedelta
from loguru import logger
from uuid import UUID

from core.database import get_db_session
from sqlalchemy import select
from core.models.unidade_produtiva import UnidadeProdutiva
from agricola.climatico.models import RegistroClima

async def seed_clima_data():
    db = await get_db_session()
    try:
        # Obter a primeira UP do banco
        stmt = select(UnidadeProdutiva).limit(1)
        result = await db.execute(stmt)
        up = result.scalar_one_or_none()

        if not up:
            logger.error("Nenhuma Unidade Produtiva encontrada no banco.")
            return

        logger.info(f"Gerando 30 dias de dados climáticos fictícios para a UP {up.nome} ({up.id})")
        
        hoje = date.today()
        
        # Apagar registros anteriores para essa UP, para evitar duplicidades
        # delete_stmt = sa.delete(RegistroClima).where(RegistroClima.unidade_produtiva_id == up.id)
        # await db.execute(delete_stmt)
        
        for i in range(30):
            data_reg = hoje - timedelta(days=30 - i)
            
            # Gerando dados baseados numa simulação de temperatura e chuvas
            # Vamos simular um clima de safra, com flutuações.
            base_temp = 25.0 + random.uniform(-3, 3)
            t_max = base_temp + random.uniform(2, 6)
            t_min = base_temp - random.uniform(2, 5)
            t_med = (t_max + t_min) / 2
            
            # 30% de chance de chuva
            choveu = random.random() < 0.3
            chuva = random.uniform(5, 45) if choveu else 0.0
            
            umidade = random.uniform(40, 85)
            if choveu:
                umidade = random.uniform(70, 95)
                
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
                gdu_calculado=round(max(0, t_med - 10), 2), # Exemplo de Graus-dia
                fonte="OPENWEATHER_SIMULATION"
            )
            
            # Vamos checar se já existe e atualizar ou inserir
            check_stmt = select(RegistroClima).where(
                RegistroClima.unidade_produtiva_id == up.id,
                RegistroClima.data_registro == data_reg
            )
            existing = (await db.execute(check_stmt)).scalar_one_or_none()
            
            if not existing:
                db.add(registro)

        await db.commit()
        logger.info(f"Dados climáticos gerados com sucesso para a Unidade Produtiva {up.id}")
        
    except Exception as e:
        logger.error(f"Erro ao gerar seed de clima: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(seed_clima_data())
