import asyncio
from core.database import async_engine
from sqlalchemy import text

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='sankhya_config';"))
        columns = [row[0] for row in res]
        print(columns)

asyncio.run(main())
