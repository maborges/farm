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
            item = ImplantacaoChecklistItem(
                implantacao_id=implantacao_id,
                etapa_id="",
                codigo_item="TEST",
                descricao="Test",
            )
            session.add(item)
            stmt = select(ImplantacaoChecklistItem).where(ImplantacaoChecklistItem.implantacao_id == implantacao_id)
            res = await session.execute(stmt)
        except Exception as e:
            print("Error on ORM execution with bad autoflush:")
            print(str(e))

asyncio.run(main())
