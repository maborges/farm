import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker
from integracoes.models import TenantIntegracao
from sqlalchemy import select

async def main():
    async with async_session_maker() as session:
        ti_stmt = select(TenantIntegracao).where(TenantIntegracao.tenant_id == 'tenant-1')
        ti = (await session.execute(ti_stmt)).scalar_one_or_none()
        if ti:
            await session.delete(ti)
            await session.commit()
            print("tenant-1 TenantIntegracao deleted.")
        else:
            print("Not found.")

if __name__ == '__main__':
    asyncio.run(main())
