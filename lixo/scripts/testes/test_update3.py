import asyncio
from core.database import async_session_maker
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
from sqlalchemy import select
from imoveis.models.imovel import ImovelRural
from core.models.unidade_produtiva import UnidadeProdutiva

async def test():
    async with async_session_maker() as session:
        # Pega qualquer tenant com unidades
        from core.models.tenant import Tenant
        tenant = (await session.execute(select(Tenant))).scalars().first()
        if not tenant:
            print("No tenant")
            return
            
        svc = UnidadeProdutivaService(session, tenant.id)
        unidades = await svc.list_all()
        if not unidades:
            print("No unidades")
            return
            
        u = unidades[0]
        
        # Primeiro, mostra o estado atual
        print(f"Original UP matricula: {u.numero_matricula}")
        stmt = select(ImovelRural).where(ImovelRural.unidade_produtiva_id == u.id)
        im = (await session.execute(stmt)).scalars().first()
        print(f"Original Imovel matricula: {im.numero_matricula if im else 'No imovel'}")
        
        print("\nUpdating UP...")
        dados = UnidadeProdutivaUpdate(numero_matricula="99999-TEST", nirf="7654322")
        
        try:
            # Temos que usar o router logic
            # update na UP
            updated_u = await svc.update(u.id, dados)
            # sync
            await svc._sincronizar_vinculo_fundiario(updated_u, dados)
            await session.commit()
            print("Commit success!")
        except Exception as e:
            print(f"Commit failed: {e}")
            await session.rollback()
            
        # Pega de volta do banco SEM overlay para ver o que salvou na UP real
        stmt2 = select(UnidadeProdutiva).where(UnidadeProdutiva.id == u.id)
        u_db = (await session.execute(stmt2)).scalars().first()
        print(f"\nAfter DB UP matricula: {u_db.numero_matricula}")
        
        im2 = (await session.execute(stmt)).scalars().first()
        print(f"After DB Imovel matricula: {im2.numero_matricula if im2 else 'No imovel'}")
        
        # Agora com overlay
        u_overlay = await svc.get(u.id)
        print(f"After Overlay UP matricula: {u_overlay.numero_matricula}")

asyncio.run(test())
