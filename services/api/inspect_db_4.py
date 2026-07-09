import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
import os
import uuid
from dotenv import load_dotenv

load_dotenv('.env.local')

from wizard.models import ImplantacaoChecklistItem

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            implantacao_id = uuid.UUID('a3145f4f-ee61-4fc6-9ef9-8109a80e503a')
            stmt = (
                select(ImplantacaoChecklistItem)
                .where(ImplantacaoChecklistItem.implantacao_id == implantacao_id)
                .order_by(ImplantacaoChecklistItem.codigo_item.asc())
            )
            res = await session.execute(stmt)
            print("Rows:", len(res.fetchall()))
        except Exception as e:
            print("Error on ORM execution:", type(e), e)

asyncio.run(main())
