from datetime import date
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from agricola.beneficiamento.models import (
    LoteBeneficiamento,
    LoteBeneficiamentoCafeDetalhe,
)
from agricola.beneficiamento.service import BeneficiamentoService
from core.cadastros.commodities.models import Commodity
from agricola.safras.models import Safra
from core.database import Base
from core.models.tenant import Tenant
from financeiro.comercializacao.models import ComercializacaoCommodity


@pytest.fixture
async def cafe_session():
    """Cria sessão SQLite em memória para testes de qualidade × margem no café."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [
        Tenant.__table__,
        Safra.__table__,
        Commodity.__table__,
        LoteBeneficiamento.__table__,
        LoteBeneficiamentoCafeDetalhe.__table__,
        ComercializacaoCommodity.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_analise_qualidade_margem_calcula_premio_especial_e_margem_por_lote(cafe_session):
    """Valida cruzamento de SCA/ABIC, custo/saca da safra e preço de comercialização."""
    tenant_id = uuid.uuid4()
    outro_tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    commodity_id = uuid.uuid4()
    hoje = date.today()

    cafe_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Café A", ativo=True),
        Tenant(id=outro_tenant_id, nome="Fazenda Café B", ativo=True),
        Safra(
            id=safra_id,
            tenant_id=tenant_id,
            ano_safra="2026",
        ),
        Commodity(
            id=commodity_id,
            nome="Café Arábica",
            codigo="CAFE",
            tipo="AGRICOLA",
            unidade_padrao="SC60",
            ativo=True,
        ),
    ])

    lote_esp_id = uuid.uuid4()
    lote_conv_id = uuid.uuid4()
    lote_outro_id = uuid.uuid4()

    cafe_session.add_all([
        LoteBeneficiamento(
            id=lote_esp_id,
            tenant_id=tenant_id,
            safra_id=safra_id,
            numero_lote="LOT-ESP-01",
            status="VENDIDO",
            data_entrada=hoje,
            peso_entrada_kg=Decimal("10000"),
            peso_saida_kg=Decimal("3000"),
            sacas_beneficiadas=Decimal("50"),
        ),
        LoteBeneficiamento(
            id=lote_conv_id,
            tenant_id=tenant_id,
            safra_id=safra_id,
            numero_lote="LOT-CONV-02",
            status="VENDIDO",
            data_entrada=hoje,
            peso_entrada_kg=Decimal("10000"),
            peso_saida_kg=Decimal("3000"),
            sacas_beneficiadas=Decimal("50"),
        ),
        LoteBeneficiamento(
            id=lote_outro_id,
            tenant_id=outro_tenant_id,
            safra_id=safra_id,
            numero_lote="LOT-B-01",
            status="VENDIDO",
            data_entrada=hoje,
            peso_entrada_kg=Decimal("5000"),
            peso_saida_kg=Decimal("1200"),
            sacas_beneficiadas=Decimal("20"),
        ),
    ])

    cafe_session.add_all([
        LoteBeneficiamentoCafeDetalhe(
            tenant_id=tenant_id,
            lote_id=lote_esp_id,
            metodo="HONEY",
            peneira_principal="17+",
            bebida="ESTRITAMENTE_MOLE",
            pontuacao_scaa=Decimal("86.50"),
        ),
        LoteBeneficiamentoCafeDetalhe(
            tenant_id=tenant_id,
            lote_id=lote_conv_id,
            metodo="NATURAL",
            peneira_principal="15/16",
            bebida="DURA",
            pontuacao_scaa=Decimal("77.00"),
        ),
    ])

    cafe_session.add_all([
        ComercializacaoCommodity(
            tenant_id=tenant_id,
            commodity_id=commodity_id,
            comprador_id=uuid.uuid4(),
            numero_contrato="CTR-001",
            quantidade=Decimal("50"),
            unidade="SC60",
            preco_unitario=Decimal("1800.00"),
            valor_total=Decimal("90000.00"),
            status="FECHADO",
            dados_extras={"lote_beneficiamento_id": str(lote_esp_id)},
        ),
        ComercializacaoCommodity(
            tenant_id=tenant_id,
            commodity_id=commodity_id,
            comprador_id=uuid.uuid4(),
            numero_contrato="CTR-002",
            quantidade=Decimal("50"),
            unidade="SC60",
            preco_unitario=Decimal("1200.00"),
            valor_total=Decimal("60000.00"),
            status="FECHADO",
            dados_extras={"lote_beneficiamento_id": str(lote_conv_id)},
        ),
        ComercializacaoCommodity(
            tenant_id=outro_tenant_id,
            commodity_id=commodity_id,
            comprador_id=uuid.uuid4(),
            numero_contrato="CTR-B-999",
            quantidade=Decimal("20"),
            unidade="SC60",
            preco_unitario=Decimal("5000.00"),
            valor_total=Decimal("100000.00"),
            status="FECHADO",
            dados_extras={"lote_beneficiamento_id": str(lote_outro_id)},
        ),
    ])
    await cafe_session.commit()

    svc = BeneficiamentoService(cafe_session, tenant_id)
    with patch.object(svc, "_obter_custo_total_safra", AsyncMock(return_value=80000.0)):
        res = await svc.analise_qualidade_margem(safra_id)

    assert len(res.lotes) == 2
    assert res.total_sacas_safra == 100.0
    assert res.custo_medio_saca_safra == 800.0
    assert res.preco_medio_saca_especial == 1800.0
    assert res.preco_medio_saca_convencional == 1200.0
    assert res.premio_qualidade_pct == 50.0

    esp = next(i for i in res.lotes if i.numero_lote == "LOT-ESP-01")
    assert esp.especial is True
    assert esp.margem_por_saca == 1000.0
    assert esp.receita_estimada == 90000.0
    assert len(res.por_bebida) == 2
