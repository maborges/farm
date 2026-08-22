import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        await db.execute(text("SET row_security = off;"))
        res = await db.execute(text("SELECT count(*) FROM registros_clima"))
        print(f"Total registros clima: {res.scalar()}")
        res_prev = await db.execute(text("SELECT count(*) FROM previsoes_clima"))
        print(f"Total previsoes clima: {res_prev.scalar()}")
        
        # Check outbox events count
        out = await db.execute(text("SELECT status, count(*) FROM domain_event_outbox GROUP BY status"))
        print(f"Outbox events: {out.all()}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
