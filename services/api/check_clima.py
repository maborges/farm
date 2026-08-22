import asyncio
from core.database import get_db_session
from sqlalchemy import select
from core.models.unidade_produtiva import UnidadeProdutiva
from agricola.climatico.models import RegistroClima

async def main():
    db = await get_db_session()
    try:
        stmt = select(UnidadeProdutiva).where(UnidadeProdutiva.nome.ilike("%Beira Rio%"))
        ups = (await db.execute(stmt)).scalars().all()
        if not ups:
            print("Fazenda Beira Rio nao encontrada.")
            return
            
        for up in ups:
            print(f"Fazenda {up.nome} encontrada: ID = {up.id}")
            
            stmt_count = select(RegistroClima).where(RegistroClima.unidade_produtiva_id == up.id)
            registros = (await db.execute(stmt_count)).scalars().all()
            print(f"Total de registros na tabela registros_clima: {len(registros)}")
            if registros:
                print("Exemplo do primeiro registro:", registros[0].data_registro)
    finally:
        await db.close()

asyncio.run(main())
