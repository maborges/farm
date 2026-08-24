import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session_maker
from pecuaria.climatico.service import InteligenciaPecuariaService
from sqlalchemy import text
from uuid import UUID

async def diagnose_final():
    print("--- Diagnosticando analisar_estresse_termico ---")
    async with async_session_maker() as session:
        # Pega a primeira fazenda
        res = await session.execute(text("SELECT id, tenant_id, nome FROM unidades_produtivas LIMIT 1"))
        farm = res.fetchone()
        if not farm:
            print("Nenhuma fazenda encontrada.")
            return
            
        farm_id = farm[0]
        tenant_id = farm[1]
        nome = farm[2]
        
        print(f"Testando Fazenda: {nome} (ID: {farm_id}) | Tenant: {tenant_id}")
        
        # Burlar RLS
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
        
        svc = InteligenciaPecuariaService(session)
        
        try:
            print("\nExecutando analisar_estresse_termico...")
            resultado = await svc.analisar_estresse_termico(tenant_id, farm_id, "Bovino de Leite")
            print(f"\nResultado da API: {resultado}")
            
            if resultado is None:
                print(">> A API RETORNOU None! Vamos descobrir o porquê:")
                
                # Check 1: Modelo
                modelo = await svc.model_svc.get_or_copy_model(tenant_id, "Bovino de Leite", "Estresse Térmico")
                print(f"Check Modelo: {modelo}")
                
                # Check 2: Clima
                from datetime import date, timedelta
                from agricola.climatico.models import RegistroClima
                from sqlalchemy import select
                
                hoje = date.today()
                stmt_clima = select(RegistroClima).where(
                    RegistroClima.tenant_id == tenant_id,
                    RegistroClima.unidade_produtiva_id == farm_id,
                    RegistroClima.data_registro >= hoje - timedelta(days=2)
                ).order_by(RegistroClima.data_registro.desc()).limit(1)
                
                clima = (await session.execute(stmt_clima)).scalars().first()
                print(f"Check Clima: {clima}")
                if clima:
                    print(f"  temp_media_c = {clima.temp_media_c}")
                    print(f"  umidade_rel_pct = {clima.umidade_rel_pct}")
        except Exception as e:
            print(f"ERRO DE EXCEÇÃO: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_final())
