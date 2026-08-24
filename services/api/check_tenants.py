import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import async_session_maker
from sqlalchemy import text

async def check():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT id, nome FROM tenants"))
        tenants = res.fetchall()
        print(f"Total de tenants no banco: {len(tenants)}")
        for t in tenants:
            print(f" - {t[0]} : {t[1]}")
            
        res2 = await session.execute(text("SELECT id, nome, tenant_id FROM unidades_produtivas"))
        farms = res2.fetchall()
        print(f"\nTotal de fazendas: {len(farms)}")
        for f in farms:
            print(f" - {f[0]} : {f[1]} (Tenant: {f[2]})")

asyncio.run(check())
