import asyncio
from core.database import async_session_maker
from integracoes.models import IntegrationSyncPolicy
from sqlalchemy import select

async def main():
    async with async_session_maker() as session:
        try:
            stmt = select(IntegrationSyncPolicy).where(IntegrationSyncPolicy.id == 2029)
            result = await session.execute(stmt)
            policy = result.scalar_one_or_none()
            print("Policy tenant_id:", policy.tenant_id)
        except Exception as e:
            print("Error:", e)

asyncio.run(main())
