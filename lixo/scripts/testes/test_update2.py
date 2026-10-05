import asyncio
import uuid
import json
from httpx import AsyncClient

async def test():
    # Login or get token if needed, but wait!
    # I can just bypass auth by calling the service method directly!
    from core.database import async_session_maker
    from core.services.unidade_produtiva_service import UnidadeProdutivaService
    from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
    
    async with async_session_maker() as session:
        # Get any tenant
        from core.models.tenant import Tenant
        from sqlalchemy import select
        tenant = (await session.execute(select(Tenant))).scalars().first()
        if not tenant:
            print("No tenant")
            return
            
        svc = UnidadeProdutivaService(session, tenant.id)
        unidades = await svc.list_all()
        if not unidades:
            print("No unidades")
            return
            
        u = unidades[0]
        print(f"Original: {u.numero_matricula}")
        
        # Try to update
        dados = UnidadeProdutivaUpdate(numero_matricula="12345-TEST")
        updated = await svc.update(u.id, dados)
        await session.commit()
        print(f"Updated (from update return): {updated.numero_matricula}")
        
        # Get it back
        u2 = await svc.get(u.id)
        print(f"Get (after commit): {u2.numero_matricula}")

asyncio.run(test())
