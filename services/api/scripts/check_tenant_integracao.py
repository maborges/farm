import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        up_id = "c5344dff-df09-41bf-a17c-181208801dde"
        res = await db.execute(text(f"SELECT tenant_id FROM unidades_produtivas WHERE id = '{up_id}'"))
        tenant_id = res.scalar()
        
        # Check tenant_integracoes
        res2 = await db.execute(text(f"SELECT * FROM tenant_integracoes WHERE tenant_id = '{tenant_id}'"))
        print(f"Tenant Integrations for {tenant_id}: {res2.fetchall()}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
