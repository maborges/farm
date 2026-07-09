import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os
import uuid
from dotenv import load_dotenv
from wizard.services import ChecklistService, ImplantacaoService

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            tenant_id = uuid.UUID('e299b9cf-891f-44e2-9b27-01053457a419')
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
            
            checklist_service = ChecklistService(session)
            await checklist_service._sanitize_legacy_nullable_uuid_columns()
            print("Successfully executed sanitize!")
        except Exception as e:
            print("Error in sanitize:", type(e), e)

asyncio.run(main())
