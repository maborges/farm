import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import uuid
from dotenv import load_dotenv

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            implantacao_id = uuid.UUID('a3145f4f-ee61-4fc6-9ef9-8109a80e503a')
            stmt = text("SELECT * FROM wizard_implantacoes_checklist_itens WHERE implantacao_id = :implantacao_id ORDER BY codigo_item ASC")
            res = await session.execute(stmt, {"implantacao_id": implantacao_id})
            print("Rows:", len(res.fetchall()))
        except Exception as e:
            print("Error on direct text execution:", type(e), e)

from sqlalchemy import text
asyncio.run(main())
