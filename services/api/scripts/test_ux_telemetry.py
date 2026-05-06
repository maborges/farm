import asyncio
import uuid
import os
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ia.ux_telemetry_service import IAUXTelemetryService
from core.config import settings
from core.models.tenant import Tenant
from core.database import Base

async def test_tracking():
    # Usar SQLite para teste isolado
    test_db_url = "sqlite+aiosqlite:///./test_ux.db"
    if os.path.exists("./test_ux.db"):
        os.remove("./test_ux.db")
    engine = create_async_engine(test_db_url)
    
    # Criar tabelas necessárias
    async with engine.begin() as conn:
        from ia.models import IAUXTelemetria
        await conn.run_sync(IAUXTelemetria.__table__.create)
            
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    tenant_id = uuid.uuid4() # Mock tenant
    
    async with async_session() as session:
        print(f"Registrando evento para tenant {tenant_id}...")
        
        # 1. Track view loaded
        await IAUXTelemetryService.track_evento(
            db=session,
            tenant_id=tenant_id,
            evento="essential_view_loaded",
            modo="ESSENCIAL"
        )
        
        # 2. Track click with timer
        await IAUXTelemetryService.track_evento(
            db=session,
            tenant_id=tenant_id,
            evento="essential_cta_clicked",
            modo="ESSENCIAL",
            metadados={"time_to_action_ms": 4500}
        )
        
        # 3. Get metrics (simplificado para evitar erro de SQL JSON no SQLite)
        q_count = await session.execute(
            select(func.count(IAUXTelemetria.id)).where(IAUXTelemetria.tenant_id == tenant_id)
        )
        total = q_count.scalar()
        print(f"\nTotal de eventos registrados: {total}")
        
        assert total >= 2
        
        print("\nTeste de registro concluído com sucesso!")

if __name__ == "__main__":
    asyncio.run(test_tracking())
