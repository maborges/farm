import asyncio
from sqlalchemy import text
from core.database import async_session_maker

async def main():
    async with async_session_maker() as session:
        await session.execute(text("SET row_security = off"))
        r = await session.execute(text("SELECT count(*) FROM propriedade_imovel"))
        print(f"Count with row_security=off: {r.scalar()}")
        
asyncio.run(main())
