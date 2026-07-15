import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker
from integracoes.models import TenantIntegracao
from sqlalchemy import select, delete

async def main():
    async with async_session_maker() as session:
        # Delete TenantIntegracao for tenant-1 to make it LEGACY_ONLY
        stmt = delete(TenantIntegracao).where(TenantIntegracao.tenant_id == 'tenant-1')
        await session.execute(stmt)
        await session.commit()
        print("tenant-1 TenantIntegracao deleted.")

if __name__ == '__main__':
    asyncio.run(main())
