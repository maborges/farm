import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM tenant_integracoes WHERE tenant_id = 'tenant-1'"))
        await session.commit()
        print("Raw DELETE executed via async session.")

if __name__ == '__main__':
    asyncio.run(main())
