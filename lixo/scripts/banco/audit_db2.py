import asyncio
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from imoveis.models.imovel import ImovelRural
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural

async def audit():
    async with async_session_maker() as session:
        # Total Unidades Produtivas com algum campo fundiário preenchido
        stmt = select(func.count(UnidadeProdutiva.id)).where(
            or_(
                UnidadeProdutiva.codigo_car.isnot(None),
                UnidadeProdutiva.nirf.isnot(None),
                UnidadeProdutiva.numero_matricula.isnot(None),
                UnidadeProdutiva.ccir.isnot(None),
                UnidadeProdutiva.sigef_codigo.isnot(None)
            )
        )
        r = await session.execute(stmt)
        print(f"UPs com campos fundiários legados preenchidos: {r.scalar()}")

        # Total ExploracaoRural
        stmt = select(func.count(ExploracaoRural.id))
        r = await session.execute(stmt)
        print(f"Total ExploracaoRural (ponte UP-Prop): {r.scalar()}")

        # UPs com ExploracaoRural
        stmt = select(func.count(func.distinct(ExploracaoRural.unidade_produtiva_id)))
        r = await session.execute(stmt)
        print(f"UPs associadas a Propriedades (via ExploracaoRural): {r.scalar()}")

        # ImovelRural com unidade_produtiva_id válido
        stmt = select(func.count(ImovelRural.id)).where(
            ImovelRural.unidade_produtiva_id.isnot(None)
        )
        r = await session.execute(stmt)
        print(f"ImovelRural com unidade_produtiva_id (vínculo direto): {r.scalar()}")
        
        # ImovelRural sem unidade_produtiva_id e sem PropriedadeImovel (órfão)
        stmt = select(func.count(ImovelRural.id)).where(
            ImovelRural.unidade_produtiva_id.is_(None),
            ImovelRural.id.not_in(select(PropriedadeImovel.imovel_rural_id))
        )
        r = await session.execute(stmt)
        print(f"ImovelRural 100% órfão: {r.scalar()}")

        # Imóveis múltiplos para a mesma UP (1 UP : N Imóveis)
        stmt = select(ImovelRural.unidade_produtiva_id).group_by(ImovelRural.unidade_produtiva_id).having(func.count(ImovelRural.id) > 1)
        r = await session.execute(stmt)
        multiplos = len(r.scalars().all())
        print(f"UPs com múltiplos ImovelRural diretos vinculados: {multiplos}")


if __name__ == "__main__":
    asyncio.run(audit())
