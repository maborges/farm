import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())
from sqlalchemy import text
from core.database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Adicionando coluna 'escolhido'...")
        await conn.execute(text("ALTER TABLE financeiro_safra_cenarios ADD COLUMN IF NOT EXISTS escolhido BOOLEAN DEFAULT FALSE"))
        print("Adicionando coluna 'escolhido_at'...")
        await conn.execute(text("ALTER TABLE financeiro_safra_cenarios ADD COLUMN IF NOT EXISTS escolhido_at TIMESTAMPTZ"))
        print("Migração concluída.")

if __name__ == "__main__":
    asyncio.run(migrate())
