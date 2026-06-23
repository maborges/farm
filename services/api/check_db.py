import asyncio
from sqlalchemy import create_engine, text

# Using standard psycopg2/asyncpg to query
import os

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres" # default

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, safra_id, talhao_id, data_observacao, escala_id FROM safra_fenologia_registros LIMIT 10"))
        rows = result.fetchall()
        print(f"Total: {len(rows)}")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
