
import asyncio
from sqlalchemy import text
from core.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'compras_cotacoes'"))
        for row in res:
            print(f"{row[0]}: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())
