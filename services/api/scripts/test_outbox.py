import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        # Try to query domain_event_outbox without RLS context
        res = await db.execute(text("SELECT DISTINCT tenant_id FROM domain_event_outbox WHERE status IN ('PENDING', 'FAILED')"))
        print(res.scalars().all())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
