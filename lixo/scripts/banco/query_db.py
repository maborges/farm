import asyncio
from core.database import async_session_maker
from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import ImovelRural
from sqlalchemy import select

async def test():
    async with async_session_maker() as session:
        # Pega a UP '678122a2-700d-4425-a779-043395c2246a' que o usuario mostrou no log
        stmt = select(UnidadeProdutiva).where(UnidadeProdutiva.id == '678122a2-700d-4425-a779-043395c2246a')
        u = (await session.execute(stmt)).scalars().first()
        if not u:
            print("UP not found")
            return
            
        print(f"UP na tabela unidades_produtivas: ID={u.id}, numero_matricula={u.numero_matricula}, nome={u.nome}")
        
        # Pega todos os ImovelRural dessa UP
        stmt_im = select(ImovelRural).where(ImovelRural.unidade_produtiva_id == u.id)
        imoveis = (await session.execute(stmt_im)).scalars().all()
        
        print(f"Encontrados {len(imoveis)} registros na tabela imoveis_rurais para essa UP.")
        for im in imoveis:
            print(f"- ImovelRural ID={im.id}, nome={im.nome}, numero_matricula={im.numero_matricula}, deleted_at={im.deleted_at}")

asyncio.run(test())
