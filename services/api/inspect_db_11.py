import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT ''::uuid;"))
        except Exception as e:
            print("Error casting:", type(e), e)

asyncio.run(main())
