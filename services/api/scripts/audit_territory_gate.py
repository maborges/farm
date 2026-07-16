import asyncio
import sys
from sqlalchemy import text
from core.database import async_session_maker
from loguru import logger

async def run_gate_audit():
    async with async_session_maker() as session:
        await session.execute(text("ALTER TABLE propriedade_imovel NO FORCE ROW LEVEL SECURITY;"))
        await session.execute(text("SET row_security = OFF;"))

        result = await session.execute(text("""
            SELECT count(DISTINCT ir.id)
            FROM imoveis_rurais ir
            LEFT JOIN propriedade_imovel pi ON pi.imovel_rural_id = ir.id
            WHERE pi.id IS NULL AND ir.unidade_produtiva_id IS NOT NULL
        """))
        direct_only = result.scalar()

        result = await session.execute(text("""
            SELECT count(DISTINCT ir.id)
            FROM imoveis_rurais ir
            JOIN propriedade_imovel pi ON pi.imovel_rural_id = ir.id
        """))
        canonical_only = result.scalar()

        result = await session.execute(text("""
            SELECT count(DISTINCT up.id)
            FROM unidades_produtivas up
            JOIN imoveis_rurais ir ON ir.unidade_produtiva_id = up.id
            LEFT JOIN cadastros_exploracoes_rurais er ON er.unidade_produtiva_id = up.id
            WHERE er.id IS NULL
        """))
        orphan = result.scalar()

        result = await session.execute(text("""
            SELECT count(*)
            FROM propriedade_imovel pi
            JOIN imoveis_rurais ir ON pi.imovel_rural_id = ir.id
            WHERE pi.tenant_id != ir.tenant_id
        """))
        tenant_mismatch = result.scalar()

        result = await session.execute(text("""
            SELECT count(*) FROM (
                SELECT propriedade_id
                FROM propriedade_imovel
                WHERE vinculo_principal = true
                GROUP BY propriedade_id
                HAVING count(*) > 1
            ) sub
        """))
        ambiguous = result.scalar()

        result = await session.execute(text("""
            SELECT count(*)
            FROM propriedade_imovel pi
            JOIN imoveis_rurais ir ON pi.imovel_rural_id = ir.id
            JOIN cadastros_propriedades p ON pi.propriedade_id = p.id
            WHERE ir.tenant_id != p.tenant_id
        """))
        divergent = result.scalar()
        
        await session.execute(text("ALTER TABLE propriedade_imovel FORCE ROW LEVEL SECURITY;"))

        logger.info("Gate de Elegibilidade (Fase 01H):")
        logger.info(f"  DIRECT_ONLY: {direct_only}")
        logger.info(f"  CANONICAL_ONLY: {canonical_only}")
        logger.info(f"  ORPHAN: {orphan}")
        logger.info(f"  TENANT_MISMATCH: {tenant_mismatch}")
        logger.info(f"  AMBIGUOUS: {ambiguous}")
        logger.info(f"  DIVERGENT: {divergent}")

        errors = []
        if direct_only > 0: errors.append(f"{direct_only} imóveis dependem de vínculo legado")
        if orphan > 0: errors.append(f"{orphan} unidades produtivas bloqueantes sem exploração")
        if tenant_mismatch > 0: errors.append(f"{tenant_mismatch} incompatibilidades de tenant")
        
        if errors:
            logger.error("VEREDICTO: NO-GO")
            for e in errors:
                logger.error(f" - {e}")
            sys.exit(1)
        else:
            logger.success("VEREDICTO: GO")
            logger.success("Todos os bloqueios fundiários foram resolvidos.")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_gate_audit())
