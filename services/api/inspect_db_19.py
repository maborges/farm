import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os
import uuid
from dotenv import load_dotenv
from wizard.models import ImplantacaoChecklistItem

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        try:
            item = ImplantacaoChecklistItem(
                implantacao_id=uuid.uuid4(),
                etapa_id="",  # empty string!
                codigo_item="TEST",
                descricao="Test",
                obrigatorio=True,
                status="PENDENTE",
                severidade="INFO",
                evidencia_tipo="AUTOMATICA",
            )
            session.add(item)
            await session.flush()
        except Exception as e:
            print("Flush Error:", type(e), e)

asyncio.run(main())
