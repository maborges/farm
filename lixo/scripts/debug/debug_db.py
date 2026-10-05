import asyncio
import os
import sys

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath('services/api'))

from core.database import engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import text

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def main():
    async with SessionLocal() as session:
        try:
            res = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
            for row in res:
                print(row)
            print("SUCCESS")
        except Exception as e:
            print("ERROR", e)

asyncio.run(main())
