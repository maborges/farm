"""
Guardrails: verifica que as FKs compostas de proteção cross-tenant estão
presentes e validadas no catálogo do PostgreSQL.

Fase: TENANT-INTEGRITY-REPAIR-01C
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


DATABASE_URL = "postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms"


@pytest.fixture(scope="module")
async def catalog_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("constraint_name,tabela", [
    ("fk_car_tenant_unidade_produtiva",  "cadastros_areas_rurais"),
    ("fk_ed_tenant_unidade_produtiva",   "estoque_depositos"),
    ("fk_ce_tenant_unidade_produtiva",   "cadastros_equipamentos"),
    ("fk_cp_tenant_deposito",            "compras_pedidos"),
    ("fk_fje_tenant_unidade_produtiva",  "frota_jornadas_equipamento"),
    ("fk_fau_tenant_jornada",            "frota_apontamentos_uso"),
    ("fk_fa_tenant_equipamento",         "frota_abastecimentos"),
])
async def test_fk_composta_presente_e_valida(
    catalog_session: AsyncSession,
    constraint_name: str,
    tabela: str,
) -> None:
    result = await catalog_session.execute(text("""
        SELECT COUNT(*) FROM pg_constraint
        WHERE contype = 'f'
          AND conname = :name
          AND conrelid = ('farms.' || :tabela)::regclass
          AND convalidated = true
    """), {"name": constraint_name, "tabela": tabela})
    count = result.scalar()
    assert count == 1, (
        f"FK composta '{constraint_name}' ausente ou NOT VALID em farms.{tabela}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("constraint_name,tabela", [
    ("uq_estoque_depositos_tenant_id",      "estoque_depositos"),
    ("uq_frota_jornadas_tenant_id",         "frota_jornadas_equipamento"),
    ("uq_cadastros_equipamentos_tenant_id", "cadastros_equipamentos"),
    ("uq_unidades_produtivas_tenant_id_id", "unidades_produtivas"),
])
async def test_unique_composto_pai_presente(
    catalog_session: AsyncSession,
    constraint_name: str,
    tabela: str,
) -> None:
    result = await catalog_session.execute(text("""
        SELECT COUNT(*) FROM pg_constraint
        WHERE contype IN ('u', 'p')
          AND conname = :name
          AND conrelid = ('farms.' || :tabela)::regclass
    """), {"name": constraint_name, "tabela": tabela})
    count = result.scalar()
    assert count == 1, (
        f"UNIQUE composto '{constraint_name}' ausente em farms.{tabela}"
    )
