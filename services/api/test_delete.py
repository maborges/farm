import asyncio
from sqlalchemy import select
from core.database import async_session_maker
from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import ImovelRural
from core.cadastros.propriedade_imovel.models import PropriedadeImovel

async def main():
    print("Compiling query...")
    try:
        async with async_session_maker() as session:
            stmt_imovel = (
                select(ImovelRural)
                .join(
                    PropriedadeImovel,
                    PropriedadeImovel.imovel_rural_id == ImovelRural.id,
                )
                .where(
                    PropriedadeImovel.tenant_id == '54c57ec3-6c13-42a8-8630-26424c8dad09',
                    PropriedadeImovel.propriedade_id == '54c57ec3-6c13-42a8-8630-26424c8dad09',
                    PropriedadeImovel.ativo.is_(True),
                    PropriedadeImovel.vinculo_principal.is_(True),
                    ImovelRural.deleted_at.is_(None),
                )
                .limit(1)
            )
            print("Query:", stmt_imovel)
            print("Executing...")
            res = await session.execute(stmt_imovel)
            print("Result:", res.scalar_one_or_none())
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
