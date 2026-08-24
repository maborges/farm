import asyncio
from core.database import async_session_maker
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def raw_query():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT id, tenant_id FROM unidades_produtivas LIMIT 1"))
        farm = res.fetchone()
        farm_id = str(farm[0])
        
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{str(farm[1])}'"))
        
        print(f"Buscando RAW SQL para farm_id: {farm_id}")
        
        # Raw query
        res2 = await session.execute(text(f"SELECT data_registro, temp_media_c, umidade_rel_pct FROM registros_clima WHERE unidade_produtiva_id = '{farm_id}' ORDER BY data_registro DESC"))
        rows = res2.fetchall()
        
        print(f"Linhas encontradas: {len(rows)}")
        for r in rows:
            print(f"- Data: {r[0]}, Temp: {r[1]}, Umi: {r[2]}")

if __name__ == "__main__":
    asyncio.run(raw_query())
