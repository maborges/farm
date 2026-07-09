import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'wizard_implantacoes_checklist_itens'")
        )
        print("Columns:")
        for row in res:
            print(row)
            
        res = await conn.execute(text("SELECT id FROM wizard_implantacoes_checklist_itens WHERE etapa_id = '' OR checked_by_usuario_id = '' LIMIT 1"))
        rows = res.fetchall()
        print("Rows with '':", rows)

from sqlalchemy import text
asyncio.run(main())
