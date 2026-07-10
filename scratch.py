import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from integracoes.sankhya.services.canonical_adapter import SankhyaIntegrationAdapter

async def main():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        adapter = SankhyaIntegrationAdapter(session)
        # Just calling the static parts to see if ProviderSchemaDefinition compiles correctly
        print("Schema loaded successfully!")

asyncio.run(main())
