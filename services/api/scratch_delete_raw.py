import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

async def main():
    engine = create_engine(os.getenv("DATABASE_URL").replace("+asyncpg", ""))
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM integracoes_tenant WHERE tenant_id = 'tenant-1'"))
        print("Raw DELETE executed.")

if __name__ == '__main__':
    asyncio.run(main())
