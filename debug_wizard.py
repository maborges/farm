import asyncio
import os
import sys

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath('services/api'))

from uuid import UUID
from core.database import engine
from core.dependencies import get_session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from wizard.router import wizard_status
from core.models.auth import Usuario
from fastapi import Request

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def main():
    async with SessionLocal() as session:
        from core.models.tenant import Tenant
        from core.models.auth import Usuario
        from sqlalchemy import select, text
        res_t = await session.execute(select(Tenant.id).limit(1))
        tenant_id = res_t.scalar()
        res_u = await session.execute(select(Usuario.id).limit(1))
        user_id = res_u.scalar()
        
        user = Usuario(id=user_id)
        
        session.info["tenant_id"] = tenant_id
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
        
        # mock request
        class MockRequest:
            headers = {}
        request = MockRequest()
        
        print("Calling wizard_status...")
        try:
            res = await wizard_status(request, session, tenant_id, user)
            print("Success!")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
