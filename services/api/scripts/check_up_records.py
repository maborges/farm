import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        await db.execute(text("SET row_security = off;"))
        res = await db.execute(text("SELECT unidade_produtiva_id, count(*) FROM registros_clima GROUP BY unidade_produtiva_id"))
        print(f"Registros clima por UP: {res.fetchall()}")
        
        res_prev = await db.execute(text("SELECT unidade_produtiva_id, count(*) FROM previsoes_clima GROUP BY unidade_produtiva_id"))
        print(f"Previsoes clima por UP: {res_prev.fetchall()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
