import asyncio
from core.database import async_session_maker
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
from sqlalchemy import select
from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import ImovelRural
from core.models.tenant import Tenant

async def test():
    async with async_session_maker() as session:
        # Pega a UP '678122a2-700d-4425-a779-043395c2246a'
        stmt = select(UnidadeProdutiva).where(UnidadeProdutiva.id == '678122a2-700d-4425-a779-043395c2246a')
        u = (await session.execute(stmt)).scalars().first()
        if not u:
            print("UP not found")
            return

        tenant_id = u.tenant_id
        svc = UnidadeProdutivaService(session, tenant_id)
        
        # Estado atual na UP
        print(f"Original UP matricula no BD: {u.numero_matricula}")
        
        # Estado atual no Imovel
        stmt_im = select(ImovelRural).where(ImovelRural.unidade_produtiva_id == u.id)
        im = (await session.execute(stmt_im)).scalars().first()
        print(f"Original Imovel matricula no BD: {im.numero_matricula if im else 'No imovel'}")
        
        print("\nAtualizando UP via Service...")
        dados = UnidadeProdutivaUpdate(numero_matricula="12349")
        try:
            updated_u = await svc.update(u.id, dados)
            await session.commit()
            print("Commit success!")
        except Exception as e:
            print(f"Commit failed: {e}")
            await session.rollback()
            return
            
        # Pega de volta do banco SEM overlay para ver o que salvou na UP real
        stmt2 = select(UnidadeProdutiva).where(UnidadeProdutiva.id == u.id)
        u_db = (await session.execute(stmt2)).scalars().first()
        print(f"\nAfter DB UP matricula: {u_db.numero_matricula}")
        
        im2 = (await session.execute(stmt_im)).scalars().first()
        print(f"After DB Imovel matricula: {im2.numero_matricula if im2 else 'No imovel'}")
        
        # Agora com overlay (como o GET faz)
        u_overlay = await svc.get(u.id)
        print(f"After Overlay UP matricula (GET output): {u_overlay.numero_matricula}")

asyncio.run(test())
