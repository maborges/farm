import asyncio
from core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'imoveis_rurais' AND column_name = 'created_by'"))
        print(result.scalar())

asyncio.run(main())
