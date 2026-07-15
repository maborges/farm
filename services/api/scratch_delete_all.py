import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker
from integracoes.sankhya.models import SankhyaConfig
from integracoes.models import TenantIntegracao
from sqlalchemy import delete

async def main():
    async with async_session_maker() as session:
        await session.execute(delete(TenantIntegracao).where(TenantIntegracao.tenant_id == 'tenant-1'))
        await session.execute(delete(SankhyaConfig).where(SankhyaConfig.tenant_id == 'tenant-1'))
        await session.commit()
        print("tenant-1 completely removed.")

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
