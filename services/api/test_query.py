import asyncio
from uuid import UUID
from core.database import async_session_maker
from sqlalchemy import text
from datetime import date, timedelta

async def test_db():
    async with async_session_maker() as session:
        # Check first tenant and farm
        res = await session.execute(text("SELECT id, tenant_id FROM unidades_produtivas LIMIT 1"))
        farm = res.fetchone()
        if not farm:
            print("No farm found")
            return
        
        farm_id = farm[0]
        tenant_id = farm[1]
        print(f"Farm: {farm_id}, Tenant: {tenant_id}")
        
        # Test models
        res = await session.execute(text("SELECT id, especie, tenant_id, is_global FROM modelos_zoosanitarios"))
        models = res.fetchall()
        print(f"Models: {models}")
        
        # Test weather records
        hoje = date.today()
        dois_dias_atras = hoje - timedelta(days=2)
        print(f"Hoje: {hoje}, 2 dias atrás: {dois_dias_atras}")
        
        res = await session.execute(text(f"SELECT COUNT(*) FROM registros_clima WHERE tenant_id = '{tenant_id}' AND unidade_produtiva_id = '{farm_id}'"))
        total_clima = res.scalar()
        print(f"Total weather records for this farm: {total_clima}")
        
        res = await session.execute(text(f"SELECT data_registro FROM registros_clima WHERE tenant_id = '{tenant_id}' AND unidade_produtiva_id = '{farm_id}' ORDER BY data_registro DESC LIMIT 1"))
        latest_clima = res.scalar()
        print(f"Latest weather record date: {latest_clima}")
        
        # Test if it meets the condition
        if latest_clima:
            is_recent = latest_clima >= dois_dias_atras
            print(f"Is latest record recent (>= {dois_dias_atras})? {is_recent}")
            
asyncio.run(test_db())
