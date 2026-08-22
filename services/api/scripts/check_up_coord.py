import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        await db.execute(text("SET row_security = off;"))
        res = await db.execute(text("SELECT id, nome, coordenadas_sede FROM unidades_produtivas LIMIT 10"))
        ups = res.fetchall()
        for up in ups:
            print(f"UP: {up[1]} ({up[0]}) - Coords: {up[2]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
