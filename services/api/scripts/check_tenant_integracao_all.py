import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        await db.execute(text("SET row_security = off;"))
        res = await db.execute(text("SELECT * FROM tenant_integracoes"))
        print(f"All Tenant Integrations: {res.fetchall()}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
