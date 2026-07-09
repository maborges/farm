import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os
import uuid
from dotenv import load_dotenv
from wizard.services import ChecklistService, EtapaService, ImplantacaoService

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            tenant_id = uuid.UUID('e299b9cf-891f-44e2-9b27-01053457a419')
            # Mocking the dependency injection
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
            
            service = ImplantacaoService(session)
            
            # Use an existing owner_usuario_id and unidade_produtiva_id if possible
            # We'll just pass some random UUIDs for testing to see where it crashes
            owner_id = uuid.uuid4()
            unidade_id = uuid.uuid4()
            
            implantacao = await service.create_or_get_active(
                tenant_id=tenant_id,
                owner_usuario_id=owner_id,
                unidade_produtiva_id=unidade_id,
                modo_implantacao="ASSISTIDA",
                origem="NOVO_ASSINANTE",
            )
            print("Successfully executed create_or_get_active!")
            await session.rollback()
        except Exception as e:
            print("Error in create_or_get_active:", type(e), e)

asyncio.run(main())
