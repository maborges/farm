import asyncio
import os
import sys

# Add services/api to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/api')))

from core.database import async_session_maker
from sqlalchemy import text

async def check():
    async with async_session_maker() as session:
        orphan = await session.scalar(text("SELECT count(*) FROM imoveis_rurais ir LEFT JOIN propriedade_imovel pi ON ir.id = pi.imovel_rural_id WHERE pi.id IS NULL"))
        print(f"ORPHAN = {orphan}")
        
        tenant_mismatch = await session.scalar(text("SELECT count(*) FROM propriedade_imovel pi JOIN imoveis_rurais ir ON pi.imovel_rural_id = ir.id WHERE pi.tenant_id != ir.tenant_id"))
        print(f"TENANT_MISMATCH = {tenant_mismatch}")
        
        ambiguous = await session.scalar(text("SELECT count(*) FROM (SELECT propriedade_id FROM propriedade_imovel WHERE vinculo_principal = true GROUP BY propriedade_id HAVING count(*) > 1) AS sub"))
        print(f"AMBIGUOUS = {ambiguous}")
        
        divergent = await session.scalar(text("SELECT count(*) FROM propriedade_imovel WHERE ativo = true AND data_fim IS NOT NULL"))
        print(f"DIVERGENT = {divergent}")

asyncio.run(check())
