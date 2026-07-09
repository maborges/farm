import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('services/api'))
from core.database import SessionLocal
from sqlalchemy import text

async def main():
    async with SessionLocal() as session:
        try:
            res = await session.execute(text("SELECT polname, polqual, polwithcheck FROM pg_policy WHERE polrelid = 'wizard_implantacoes_operacionais'::regclass"))
            for row in res:
                print(row)
        except Exception as e:
            print("ERROR", e)

asyncio.run(main())
