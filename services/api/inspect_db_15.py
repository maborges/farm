import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(
            text("""
                SELECT tablename, policyname, qual, with_check 
                FROM pg_policies 
                WHERE tablename = 'wizard_implantacoes_operacionais'
            """)
        )
        print("Policies:")
        for row in res:
            print(row)

from sqlalchemy import text
asyncio.run(main())
