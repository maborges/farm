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
            res = await conn.execute(text("SHOW app.current_tenant_id;"))
            val = res.scalar()
            print("SHOW Value:", val)
        except Exception as e:
            print("SHOW Error:", type(e), e)
            
        try:
            res = await conn.execute(text("SELECT current_setting('app.current_tenant_id', true);"))
            val = res.scalar()
            print("current_setting Value:", val)
        except Exception as e:
            print("current_setting Error:", type(e), e)

asyncio.run(main())
