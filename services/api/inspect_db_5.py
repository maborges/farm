import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import uuid
from dotenv import load_dotenv

load_dotenv('.env.local')

from wizard.services import ChecklistService

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            implantacao_id = uuid.UUID('a3145f4f-ee61-4fc6-9ef9-8109a80e503a')
            service = ChecklistService(session)
            items = await service.listar_itens(implantacao_id)
            print("Items:", len(items))
        except Exception as e:
            print("Error:", type(e), e)

asyncio.run(main())
