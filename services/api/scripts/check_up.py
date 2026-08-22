import asyncio
from sqlalchemy import text
from core.database import get_db_session

async def main():
    db = await get_db_session()
    try:
        up_id = "c5344dff-df09-41bf-a17c-181208801dde"
        res = await db.execute(text(f"SELECT tenant_id FROM unidades_produtivas WHERE id = '{up_id}'"))
        tenant_id = res.scalar()
        print(f"UP: {up_id}, Tenant: {tenant_id}")
        
        from agricola.climatico.service import ClimaService
        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
        svc = ClimaService(db, tenant_id)
        
        print("Buscando resumo...")
        resumo = await svc.get_resumo_climatico(up_id)
        print(f"Resumo: {resumo}")
        
        print("Executando sync manual...")
        msg = await svc.sync_open_meteo(up_id)
        print(f"Sync msg: {msg}")
        
        print("Buscando resumo novamente...")
        resumo = await svc.get_resumo_climatico(up_id)
        print(f"Resumo: {resumo}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

asyncio.run(main())
