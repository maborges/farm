import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        await db.execute(text("SET row_security = off;"))
        res = await db.execute(text("SELECT id, tenant_id, scope_type, scope_id, configuracoes FROM tenant_integracoes WHERE configuracoes::text LIKE '%location_query%' OR configuracoes::text LIKE '%sync_interval%'"))
        for row in res.fetchall():
            print(f"Config: {row}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
