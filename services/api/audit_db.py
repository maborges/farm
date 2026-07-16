import asyncio
from sqlalchemy import select, text
from core.database import async_session_maker
from loguru import logger

async def run_audit():
    async with async_session_maker() as session:
        # Ambiente
        result = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        alembic_head = result.scalar()
        
        result = await session.execute(text("SELECT current_schema()"))
        current_schema = result.scalar()
        
        result = await session.execute(text("SELECT count(*) FROM tenants"))
        total_tenants = result.scalar()
        
        result = await session.execute(text("SELECT count(*) FROM unidades_produtivas"))
        total_ups = result.scalar()
        
        result = await session.execute(text("SELECT count(*) FROM cadastros_propriedades"))
        total_propriedades = result.scalar()
        
        result = await session.execute(text("SELECT count(*) FROM cadastros_exploracoes_rurais"))
        total_exploracoes = result.scalar()

        await session.execute(text("ALTER TABLE propriedade_imovel NO FORCE ROW LEVEL SECURITY;"))
        await session.execute(text("SET row_security = OFF;"))

        result = await session.execute(text("SELECT count(*) FROM propriedade_imovel"))
        total_propriedade_imovel = result.scalar()
        
        result = await session.execute(text("SELECT count(*) FROM imoveis_rurais"))
        total_imoveis = result.scalar()

        result = await session.execute(text("""
            SELECT count(DISTINCT ir.id)
            FROM imoveis_rurais ir
            JOIN propriedade_imovel pi ON pi.imovel_rural_id = ir.id
        """))
        canonical_imoveis = result.scalar()

        result = await session.execute(text("""
            SELECT count(DISTINCT ir.id)
            FROM imoveis_rurais ir
            LEFT JOIN propriedade_imovel pi ON pi.imovel_rural_id = ir.id
            WHERE pi.id IS NULL AND ir.unidade_produtiva_id IS NOT NULL
        """))
        direct_only_imoveis = result.scalar()

        result = await session.execute(text("""
            SELECT count(*)
            FROM unidades_produtivas up
            LEFT JOIN cadastros_exploracoes_rurais er ON er.unidade_produtiva_id = up.id
            WHERE er.id IS NULL
        """))
        ups_sem_exploracao = result.scalar()

        result = await session.execute(text("""
            SELECT count(*)
            FROM unidades_produtivas up
            LEFT JOIN imoveis_rurais ir ON ir.unidade_produtiva_id = up.id
            LEFT JOIN cadastros_exploracoes_rurais er ON er.unidade_produtiva_id = up.id
            WHERE ir.id IS NULL AND er.id IS NULL
            AND (up.nirf IS NOT NULL OR up.codigo_car IS NOT NULL OR up.numero_matricula IS NOT NULL)
        """))
        legacy_fields_only = result.scalar()

        result = await session.execute(text("""
            SELECT count(*) FROM (
                SELECT propriedade_id
                FROM propriedade_imovel
                WHERE vinculo_principal = true
                GROUP BY propriedade_id
                HAVING count(*) > 1
            ) sub
        """))
        conflitos_principal = result.scalar()

        result = await session.execute(text("""
            SELECT count(*)
            FROM propriedade_imovel
            WHERE vinculo_principal = false
        """))
        secundarios = result.scalar()
        
        result = await session.execute(text("""
            SELECT count(*)
            FROM propriedade_imovel pi
            JOIN imoveis_rurais ir ON pi.imovel_rural_id = ir.id
            JOIN cadastros_propriedades p ON pi.propriedade_id = p.id
            WHERE ir.tenant_id != p.tenant_id
        """))
        cross_tenant = result.scalar()

        logger.info(f"Ambiente:")
        logger.info(f"  Schema: {current_schema}")
        logger.info(f"  Alembic Head: {alembic_head}")
        logger.info(f"Counts Gerais:")
        logger.info(f"  Tenants: {total_tenants}")
        logger.info(f"  Unidades Produtivas: {total_ups}")
        logger.info(f"  Propriedades: {total_propriedades}")
        logger.info(f"  Exploracoes: {total_exploracoes}")
        logger.info(f"  Imoveis Rurais: {total_imoveis}")
        logger.info(f"  PropriedadeImovel (Vinculos): {total_propriedade_imovel}")
        logger.info(f"Status Fase 01G:")
        logger.info(f"  Canonical Imoveis: {canonical_imoveis}")
        logger.info(f"  DIRECT_ONLY (Imoveis Legados): {direct_only_imoveis}")
        logger.info(f"  UPS sem exploracao (Orfas): {ups_sem_exploracao}")
        logger.info(f"  LEGACY_FIELDS_ONLY: {legacy_fields_only}")
        logger.info(f"  Conflitos Principal: {conflitos_principal}")
        logger.info(f"  Vinculos Secundarios: {secundarios}")
        logger.info(f"  Cross-tenant anomalias: {cross_tenant}")

        await session.execute(text("ALTER TABLE propriedade_imovel FORCE ROW LEVEL SECURITY;"))

if __name__ == "__main__":
    asyncio.run(run_audit())
