import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session_maker
from sqlalchemy import text, select
from datetime import date, timedelta
from agricola.climatico.models import RegistroClima
from pecuaria.climatico.service import InteligenciaPecuariaService

async def side_by_side():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT id, tenant_id FROM unidades_produtivas LIMIT 1"))
        farm = res.fetchone()
        farm_id = farm[0]
        tenant_id = farm[1]
        
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
        
        hoje = date.today()
        stmt_clima = select(RegistroClima).where(
            RegistroClima.tenant_id == tenant_id,
            RegistroClima.unidade_produtiva_id == farm_id,
            RegistroClima.data_registro >= hoje - timedelta(days=2)
        ).order_by(RegistroClima.data_registro.desc()).limit(1)
        
        clima1 = (await session.execute(stmt_clima)).scalars().first()
        print(f"TESTE 1 (Direto): {clima1}")
        
        svc = InteligenciaPecuariaService(session)
        resultado = await svc.analisar_estresse_termico(tenant_id, farm_id, "Bovino de Leite")
        print(f"TESTE 2 (API): {resultado}")

asyncio.run(side_by_side())
