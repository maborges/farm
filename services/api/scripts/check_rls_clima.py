import asyncio
import httpx
from sqlalchemy import text
from core.database import get_db_session

TENANT_ID = "7cff0925-417a-41f0-8aba-271b16052477"   # Fazenda Modelo
UP_ID     = "c5344dff-df09-41bf-a17c-181208801dde"   # Beira Rio

async def main():
    db = await get_db_session()
    try:
        # Simula o que o ClimaService faz: filter_by tenant_id + UP_ID
        from sqlalchemy.future import select
        import sys
        sys.path.insert(0, '/opt/lampp/htdocs/farm/services/api')
        from agricola.climatico.models import RegistroClima
        from uuid import UUID
        
        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{TENANT_ID}';"))
        
        stmt = select(RegistroClima).filter_by(
            tenant_id=UUID(TENANT_ID),
            unidade_produtiva_id=UUID(UP_ID)
        ).order_by(RegistroClima.data_registro.desc()).limit(1)
        
        result = await db.execute(stmt)
        registro = result.scalars().first()
        
        if registro:
            print(f"✅ ClimaService encontrou dado!")
            print(f"   data_registro    : {registro.data_registro}")
            print(f"   temp_media_c     : {registro.temp_media_c}")
            print(f"   tenant_id        : {registro.tenant_id}")
            print(f"   unidade_produtiva_id: {registro.unidade_produtiva_id}")
            print(f"   fonte            : {registro.fonte}")
        else:
            print("❌ ClimaService NÃO encontrou dado com filter_by!")
            # Testa sem o filter_by de tenant_id
            stmt2 = select(RegistroClima).filter_by(
                unidade_produtiva_id=UUID(UP_ID)
            ).order_by(RegistroClima.data_registro.desc()).limit(1)
            r2 = await db.execute(stmt2)
            reg2 = r2.scalars().first()
            if reg2:
                print(f"   Mas achei com apenas UP_ID! tenant_id no banco: {reg2.tenant_id}")
            else:
                print("   Também não achou com apenas UP_ID!")

    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

asyncio.run(main())
