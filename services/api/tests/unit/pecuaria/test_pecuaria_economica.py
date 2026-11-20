from datetime import date
import uuid

import pytest
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from campo.models import TarefaCampo
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.produtos.models import Produto
from core.cadastros.propriedades.models import AreaRural
from core.measurements.models import UnidadeMedida
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito, EstoqueMovimento
from pecuaria.advanced_service import PecuariaAdvancedService
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.producao.models import ProducaoLeite
from pecuaria.services.dashboard_resumo_service import PecuariaDashboardResumoService
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Animal.__table__.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    UnidadeProdutiva.__table__,
                    AreaRural.__table__,
                    Safra.__table__,
                    ProductionUnit.__table__,
                    Cultivo.__table__,
                    UnidadeMedida.__table__,
                    Produto.__table__,
                    Deposito.__table__,
                    Pessoa.__table__,
                    LoteAnimal.__table__,
                    ManejoLote.__table__,
                    Animal.__table__,
                    EventoAnimal.__table__,
                    ProducaoLeite.__table__,
                    TarefaCampo.__table__,
                    EstoqueMovimento.__table__,
                    CostAllocation.__table__,
                    LancamentoFinanceiro.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_leite_resumo_calcula_custo_por_litro_e_media_por_vaca(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    vaca_1 = uuid.uuid4()
    vaca_2 = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Leite", slug="faz-leite", documento="11111111000101"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade A"),
        Animal(
            id=vaca_1,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            categoria="VACA_LEITE",
            sexo="FEMEA",
            status="ATIVO",
        ),
        Animal(
            id=vaca_2,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            categoria="VACA_LEITE",
            sexo="FEMEA",
            status="ATIVO",
        ),
        ProducaoLeite(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            animal_id=vaca_1,
            data=date(2026, 11, 1),
            turno="MANHA",
            volume_litros=20.0,
            preco_litro=2.80,
        ),
        ProducaoLeite(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            animal_id=vaca_2,
            data=date(2026, 11, 1),
            turno="MANHA",
            volume_litros=30.0,
            preco_litro=2.80,
        ),
        LancamentoFinanceiro(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            descricao="Ração vacas em lactação",
            valor=75.0,
            data=date(2026, 11, 1),
            tipo="CUSTO",
            categoria="PECUARIA_LEITE",
            origem="PECUARIA_LEITE",
        ),
    ])
    await async_session.commit()

    resumo = await PecuariaAdvancedService(async_session, tenant_id).resumo_leite()

    assert resumo["volume_total_litros"] == pytest.approx(50.0, rel=1e-3)
    assert resumo["producao_media_por_vaca_dia"] == pytest.approx(25.0, rel=1e-3)
    assert resumo["custo_total_leite"] == pytest.approx(75.0, rel=1e-3)
    assert resumo["custo_por_litro"] == pytest.approx(1.5, rel=1e-3)
    assert resumo["preco_medio_litro"] == pytest.approx(2.8, rel=1e-3)
    assert resumo["margem_por_litro"] == pytest.approx(1.3, rel=1e-3)


@pytest.mark.asyncio
async def test_leite_resumo_sem_producao_nao_divide_por_zero(async_session: AsyncSession):
    resumo = await PecuariaAdvancedService(async_session, uuid.uuid4()).resumo_leite()

    assert resumo["volume_total_litros"] == 0.0
    assert resumo["producao_media_por_vaca_dia"] == 0.0
    assert resumo["custo_por_litro"] == 0.0
    assert resumo["margem_por_litro"] == 0.0


@pytest.mark.asyncio
async def test_corte_lote_indicadores_calcula_lotacao_arrobas_ha_e_custo_total_arroba(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    piquete_id = uuid.uuid4()
    lote_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Corte", slug="faz-corte", documento="22222222000102"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade B"),
        AreaRural(
            id=piquete_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            nome="Piquete 1",
            tipo="PIQUETE",
            area_hectares=10.0,
            ativo=True,
        ),
        LoteAnimal(
            id=lote_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            area_id=piquete_id,
            identificacao="Lote Engorda 01",
            ativo=True,
        ),
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote_id,
            categoria="BOI",
            sexo="CASTRADO",
            status="ATIVO",
            peso_atual_kg=450.0,
        ),
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote_id,
            categoria="BOI",
            sexo="CASTRADO",
            status="ATIVO",
            peso_atual_kg=450.0,
        ),
        LancamentoFinanceiro(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            descricao="Suplemento mineral lote 01",
            valor=600.0,
            data=date(2026, 11, 1),
            tipo="CUSTO",
            categoria="OPERACOES",
            origem="PECUARIA_NUTRICAO",
            origem_id=lote_id,
        ),
    ])
    await async_session.commit()

    indicadores = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_id)

    # 2 bois de 450 kg = 900 kg total = 2.0 UA; em 10 ha => 0.2 UA/ha
    # 900 kg * 50% / 15 = 30 @ totais; em 10 ha => 3.0 @/ha
    # Custo operacional = R$ 600; 600 / 30 @ = R$ 20,00/@
    assert indicadores.area_piquete_ha == pytest.approx(10.0, rel=1e-3)
    assert indicadores.lotacao_ua_ha == pytest.approx(0.2, rel=1e-3)
    assert indicadores.arrobas_por_hectare == pytest.approx(3.0, rel=1e-3)
    assert indicadores.custo_nutricao_total == pytest.approx(600.0, rel=1e-3)
    assert indicadores.custo_total_por_arroba == pytest.approx(20.0, rel=1e-3)

    resumo_fazenda = await PecuariaDashboardResumoService(async_session, tenant_id, fazenda_id).resumir()
    assert resumo_fazenda.area_pastagem_ha == pytest.approx(10.0, rel=1e-3)
    assert resumo_fazenda.lotacao_ua_ha == pytest.approx(0.2, rel=1e-3)
    assert resumo_fazenda.arrobas_totais == pytest.approx(30.0, rel=1e-3)
    assert resumo_fazenda.arrobas_por_hectare == pytest.approx(3.0, rel=1e-3)
    assert resumo_fazenda.custo_total_por_arroba == pytest.approx(20.0, rel=1e-3)


@pytest.mark.asyncio
async def test_corte_lote_sem_peso_e_sem_piquete_nao_divide_por_zero(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    lote_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Vazia", slug="faz-vazia", documento="33333333000103"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade C"),
        LoteAnimal(
            id=lote_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            identificacao="Lote Sem Pesagem",
            ativo=True,
        ),
    ])
    await async_session.commit()

    indicadores = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_id)
    assert indicadores.lotacao_ua_ha == 0.0
    assert indicadores.arrobas_por_hectare == 0.0
    assert indicadores.custo_total_por_arroba == 0.0
