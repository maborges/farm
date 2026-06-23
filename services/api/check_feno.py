import asyncio
from core.database import SessionLocal
from sqlalchemy import text

async def main():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT id, safra_id, talhao_id, escala_id, data_observacao FROM safra_fenologia_registros"))
        rows = result.fetchall()
        print(f"Total de registros: {len(rows)}")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
