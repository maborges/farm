import asyncio
import asyncpg
from core.config import settings

async def main():
    print(f"Connecting to {settings.database_url}")
    # Replace postgresql+asyncpg with postgresql for asyncpg direct connection if needed
    url = settings.database_url.replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(url)
    tables = await conn.fetch("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")
    print([t['tablename'] for t in tables if 'hedge' in t['tablename']])
    await conn.close()

asyncio.run(main())
