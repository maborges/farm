import asyncio
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from imoveis.models.imovel import ImovelRural
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural

async def audit():
    async with async_session_maker() as session:
        # 1. Total Unidades Produtivas
        r1 = await session.execute(select(func.count(UnidadeProdutiva.id)))
        print(f"Total Unidades Produtivas: {r1.scalar()}")

        # 2. Total Imóveis
        r2 = await session.execute(select(func.count(ImovelRural.id)))
        print(f"Total Imóveis Rurais: {r2.scalar()}")

        # 3. Total Propriedades
        r3 = await session.execute(select(func.count(Propriedade.id)))
        print(f"Total Propriedades: {r3.scalar()}")

        # 4. Total PropriedadeImovel
        r4 = await session.execute(select(func.count(PropriedadeImovel.id)))
        print(f"Total Vínculos PropriedadeImovel: {r4.scalar()}")

        # 5. Imóvel Rural com unidade_produtiva_id, mas sem PropriedadeImovel
        stmt = select(func.count(ImovelRural.id)).where(
            ImovelRural.id.not_in(select(PropriedadeImovel.imovel_rural_id))
        )
        r5 = await session.execute(stmt)
        print(f"Imóveis sem PropriedadeImovel: {r5.scalar()}")
        
        # 6. PropriedadeImovel existente sem caminho válido até Unidade Produtiva
        #    Isso significa que o Propriedade não tem ExploracaoRural ligando à UP.
        stmt = select(func.count(PropriedadeImovel.id)).where(
            PropriedadeImovel.propriedade_id.not_in(select(ExploracaoRural.propriedade_id))
        )
        r6 = await session.execute(stmt)
        print(f"PropriedadeImovel sem ExploracaoRural: {r6.scalar()}")

        # 7. NIRF divergente
        stmt = select(func.count(ImovelRural.id)).join(
            UnidadeProdutiva, ImovelRural.unidade_produtiva_id == UnidadeProdutiva.id
        ).where(
            and_(
                ImovelRural.nirf.isnot(None),
                UnidadeProdutiva.nirf.isnot(None),
                ImovelRural.nirf != UnidadeProdutiva.nirf
            )
        )
        r7 = await session.execute(stmt)
        print(f"NIRF divergente (UP vs ImovelRural direto): {r7.scalar()}")

if __name__ == "__main__":
    asyncio.run(audit())
