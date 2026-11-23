import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    db_url = "postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms"
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT n.nspname, conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE conname = 'uq_cotacao_solicitacao_fornecedor'
        """))
        print("Constraint details:", res.all())

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
