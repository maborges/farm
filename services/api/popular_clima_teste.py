import asyncio
from sqlalchemy import select, text
from datetime import date, timedelta
import random
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session_maker
from agricola.climatico.models import RegistroClima

async def seed_clima():
    print("--- Gerando Dados Climáticos ---")
    async with async_session_maker() as session:
        # Pega a primeira fazenda
        res = await session.execute(text("SELECT id, tenant_id FROM unidades_produtivas"))
        farms = res.fetchall()
        if not farms:
            print("Nenhuma fazenda encontrada.")
            return
            
        hoje = date.today()
        for farm in farms:
            farm_id = str(farm[0])
            tenant_id = str(farm[1])
            novos_registros = []
            
            # Burlar o RLS definindo o tenant ativo na sessão do banco
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
            
            # Deletar dados antigos da mesma data para evitar duplicação
            await session.execute(text(f"DELETE FROM registros_clima WHERE unidade_produtiva_id = '{farm_id}' AND data_registro >= '{hoje - timedelta(days=7)}'"))
            
            for i in range(7):
                data_atual = hoje - timedelta(days=i)
                temp = random.uniform(25.0, 34.0)
                umi = random.uniform(50.0, 85.0)
                
                registro = RegistroClima(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    unidade_produtiva_id=farm_id,
                    data_registro=data_atual,
                    temp_media_c=temp,
                    temp_min_c=temp - 5,
                    temp_max_c=temp + 5,
                    umidade_rel_pct=umi,
                    precipitacao_mm=random.uniform(0, 15),
                    vento_kmh=random.uniform(5, 20)
                )
                novos_registros.append(registro)
            
            session.add_all(novos_registros)
            await session.commit()
        
        print(f"Sucesso! 7 dias de registros climáticos gerados para {len(farms)} fazendas.")
        print("Volte para a tela de Inteligência Pecuária na interface Web para ver os painéis.")

if __name__ == "__main__":
    asyncio.run(seed_clima())
