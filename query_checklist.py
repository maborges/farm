import asyncio
from core.database import async_session_maker
from sqlalchemy import select
from wizard.models import ImplantacaoChecklistItem

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(ImplantacaoChecklistItem.codigo_item, ImplantacaoChecklistItem.descricao).limit(5))
        for row in result.all():
            print(f"Codigo: {row.codigo_item}, Desc: {row.descricao}")

asyncio.run(main())
