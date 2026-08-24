import asyncio
from sqlalchemy import select, text
from datetime import date, timedelta
import sys
import os

# Adiciona o diretório atual ao path para importar os módulos locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session_maker
from pecuaria.climatico.models import ModeloZoosanitario
from agricola.climatico.models import RegistroClima

async def diagnose():
    print("--- Diagnóstico de Inteligência Pecuária ---")
    async with async_session_maker() as session:
        # 1. Checar fazenda
        res = await session.execute(text("SELECT id, nome, tenant_id FROM unidades_produtivas LIMIT 1"))
        farm = res.fetchone()
        if not farm:
            print("Nenhuma fazenda encontrada no banco.")
            return
        
        farm_id, farm_nome, tenant_id = farm
        print(f"Fazenda Base: {farm_nome} (ID: {farm_id})")
        
        # 2. Checar registros de clima
        stmt_clima = select(RegistroClima).where(
            RegistroClima.unidade_produtiva_id == farm_id
        ).order_by(RegistroClima.data_registro.desc())
        
        climas = (await session.execute(stmt_clima)).scalars().all()
        print(f"Total de registros de clima para esta fazenda: {len(climas)}")
        
        if len(climas) > 0:
            latest = climas[0]
            print(f"Último registro de clima: {latest.data_registro} (Temp: {latest.temp_media_c}, Umi: {latest.umidade_rel_pct})")
            
            hoje = date.today()
            limite = hoje - timedelta(days=2)
            
            # Converter latest.data_registro para date se for datetime
            data_reg = latest.data_registro.date() if hasattr(latest.data_registro, 'date') else latest.data_registro
            
            if data_reg < limite:
                print(f"-> MOTIVO ENCONTRADO: O último registro ({data_reg}) é mais antigo que o limite de 2 dias atrás ({limite}).")
            elif latest.temp_media_c is None or latest.umidade_rel_pct is None:
                print("-> MOTIVO ENCONTRADO: O registro mais recente não possui Temperatura Média ou Umidade Relativa preenchidos.")
            else:
                print("-> Os dados de clima estão corretos e recentes!")
        else:
            print("-> MOTIVO ENCONTRADO: Não há NENHUM registro de clima associado a esta fazenda.")
            
        # 3. Checar modelos
        stmt_modelos = select(ModeloZoosanitario).where(
            ModeloZoosanitario.especie == "Bovino de Leite",
            ModeloZoosanitario.tipo_risco == "Estresse Térmico"
        )
        modelos = (await session.execute(stmt_modelos)).scalars().all()
        print(f"\nModelos encontrados para 'Bovino de Leite' - 'Estresse Térmico': {len(modelos)}")
        for m in modelos:
            print(f" - Modelo ID: {m.id}, Global: {m.is_global}, Tenant: {m.tenant_id}")

if __name__ == "__main__":
    asyncio.run(diagnose())
