from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from pydantic import ValidationError
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
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.measurements.models import UnidadeMedida
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito, EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.producao.models import ProducaoLeite
from pecuaria.schemas.lote_schema import LoteBovinoCreate, LoteBovinoUpdate
from pecuaria.schemas.manejo_schema import ManejoLoteCreate
from pecuaria.services import cotacao_arroba_service
from pecuaria.services.arroba_utils import (
    EntradaEconomicaArroba,
    calcular_arrobas_carcaca,
    calcular_arrobas_produzidas,
    calcular_metricas_economicas_arroba,
)
from pecuaria.services.dashboard_resumo_service import PecuariaDashboardResumoService
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from pecuaria.services.lote_service import LoteBovinoService
from pecuaria.services.manejo_service import ManejoLoteService


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


def test_arroba_utils_calcula_carcaca_produzidas_e_metricas_economicas() -> None:
    assert calcular_arrobas_carcaca(900.0, 50.0) == pytest.approx(30.0)
    assert calcular_arrobas_carcaca(900.0, 54.0) == pytest.approx(32.4)
    assert calcular_arrobas_carcaca(0.0, 50.0) == 0.0

    with pytest.raises(ValueError):
        calcular_arrobas_carcaca(900.0, 0.0)
    with pytest.raises(ValueError):
        calcular_arrobas_carcaca(900.0, 105.0)

    assert calcular_arrobas_produzidas(1080.0, 900.0, 50.0) == pytest.approx(6.0)
    assert calcular_arrobas_produzidas(900.0, 950.0, 50.0) == 0.0
    assert calcular_arrobas_produzidas(900.0, None, 50.0) == 0.0

    metricas = calcular_metricas_economicas_arroba(
        EntradaEconomicaArroba(
            peso_vivo_kg=900.0,
            peso_inicial_kg=720.0,
            rendimento_carcaca_pct=50.0,
            quantidade_animais=2,
            custo_aquisicao=4500.0,
            custo_sanitario=120.0,
            custo_nutricao=480.0,
            custo_outros=0.0,
            cotacao_arroba=300.0,
        )
    )
    assert metricas.arrobas_totais == pytest.approx(30.0)
    assert metricas.arrobas_produzidas == pytest.approx(6.0)
    assert metricas.custo_total_operacional == pytest.approx(600.0)
    assert metricas.custo_sanitario_por_arroba == pytest.approx(4.0)
    assert metricas.custo_total_por_arroba == pytest.approx(20.0)
    assert metricas.custo_por_arroba_produzida == pytest.approx(100.0)
    assert metricas.custo_break_even_por_arroba == pytest.approx(170.0)
    assert metricas.valor_mercado_estimado == pytest.approx(9000.0)
    assert metricas.margem_bruta_estimada == pytest.approx(3900.0)
    assert metricas.margem_estimada_por_cabeca == pytest.approx(1950.0)

    sem_cotacao = calcular_metricas_economicas_arroba(
        EntradaEconomicaArroba(
            peso_vivo_kg=0.0,
            peso_inicial_kg=None,
            rendimento_carcaca_pct=50.0,
            quantidade_animais=0,
            custo_aquisicao=0.0,
            custo_sanitario=100.0,
            custo_nutricao=0.0,
            custo_outros=0.0,
            cotacao_arroba=None,
        )
    )
    assert sem_cotacao.custo_total_por_arroba == 0.0
    assert sem_cotacao.custo_break_even_por_arroba == 0.0
    assert sem_cotacao.valor_mercado_estimado is None
    assert sem_cotacao.margem_bruta_estimada is None
    assert sem_cotacao.margem_estimada_por_cabeca is None


@pytest.mark.asyncio
async def test_lote_hibrido_create_update_e_regras_de_promocao(async_session: AsyncSession) -> None:
    tenant_id = uuid.uuid4()
    outro_tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    piquete_1 = uuid.uuid4()
    piquete_2 = uuid.uuid4()
    piquete_outro = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="T1", slug="t1", documento="11111111000101"),
        Tenant(id=outro_tenant_id, nome="T2", slug="t2", documento="22222222000102"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda 1"),
        AreaRural(id=piquete_1, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, tipo="PIQUETE", nome="P1", area_hectares=10.0, ativo=True),
        AreaRural(id=piquete_2, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, tipo="PIQUETE", nome="P2", area_hectares=15.0, ativo=True),
        AreaRural(id=piquete_outro, tenant_id=outro_tenant_id, unidade_produtiva_id=fazenda_id, tipo="PIQUETE", nome="P Outro", area_hectares=10.0, ativo=True),
    ])
    await async_session.commit()

    with pytest.raises(ValidationError):
        LoteBovinoCreate(
            unidade_produtiva_id=fazenda_id,
            identificacao="Inválido Rendimento",
            categoria="Novilhos",
            raca="Nelore",
            quantidade_cabecas=10,
            rendimento_carcaca_pct=75.0,
        )

    with pytest.raises(ValidationError):
        LoteBovinoCreate(
            unidade_produtiva_id=fazenda_id,
            modo_gestao="POR_LOTE",
            identificacao="Inválido Vazio",
            categoria="Novilhos",
            raca="Nelore",
            quantidade_cabecas=0,
        )

    service = LoteBovinoService(tenant_id)
    lote_ind = await service.create_lote(
        async_session,
        obj_in=LoteBovinoCreate(
            unidade_produtiva_id=fazenda_id,
            modo_gestao="INDIVIDUAL",
            identificacao="Lote Individual",
            categoria="Novilhas",
            raca="Angus",
            quantidade_cabecas=0,
        ),
    )
    assert lote_ind.modo_gestao == "INDIVIDUAL"
    assert lote_ind.quantidade_cabecas == 0

    lote = await service.create_lote(
        async_session,
        obj_in=LoteBovinoCreate(
            unidade_produtiva_id=fazenda_id,
            piquete_id=piquete_1,
            modo_gestao="POR_LOTE",
            identificacao="Lote Recria 01",
            categoria="Recria",
            raca="Nelore",
            quantidade_cabecas=20,
            peso_medio_kg=240.0,
            rendimento_carcaca_pct=52.0,
        ),
    )
    await async_session.commit()
    assert lote.peso_inicial_medio_kg == pytest.approx(240.0)
    assert lote.rendimento_carcaca_pct == pytest.approx(52.0)

    atualizado = await service.update_lote(
        async_session,
        lote.id,
        LoteBovinoUpdate(
            piquete_id=piquete_2,
            rendimento_carcaca_pct=54.0,
            valor_aquisicao_total=60000.0,
            cotacao_arroba_override=315.0,
            modo_gestao="INDIVIDUAL",
        ),
    )
    assert atualizado.area_id == piquete_2
    assert atualizado.rendimento_carcaca_pct == pytest.approx(54.0)
    assert atualizado.valor_aquisicao_total == pytest.approx(60000.0)
    assert atualizado.cotacao_arroba_override == pytest.approx(315.0)
    assert atualizado.modo_gestao == "INDIVIDUAL"

    with pytest.raises(BusinessRuleError):
        await service.update_lote(
            async_session,
            lote.id,
            LoteBovinoUpdate(piquete_id=piquete_outro),
        )

    async_session.add(
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote.id,
            numero_brinco="BR-01",
            categoria="NOVILHO",
            sexo="MACHO",
            status="ATIVO",
            peso_atual_kg=300.0,
        )
    )
    await async_session.commit()

    with pytest.raises(BusinessRuleError, match="animais individuais ativos"):
        await service.update_lote(
            async_session,
            lote.id,
            LoteBovinoUpdate(modo_gestao="POR_LOTE"),
        )

    with pytest.raises(EntityNotFoundError):
        await LoteBovinoService(outro_tenant_id).update_lote(
            async_session,
            lote.id,
            LoteBovinoUpdate(rendimento_carcaca_pct=51.0),
        )


@pytest.mark.asyncio
async def test_manejo_por_lote_atualiza_saldos_e_calcula_gmd_coletivo(
    async_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        cotacao_arroba_service,
        "obter_cotacao_boi_gordo_referencia",
        lambda _session=None: _async_const((None, None)),
    )
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    hoje = date(2026, 11, 20)

    async_session.add_all([
        Tenant(id=tenant_id, nome="T Manejo", slug="t-manejo", documento="33333333000103"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda M"),
        LoteAnimal(
            id=lote_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            identificacao="Lote Pasto A",
            modo_gestao="POR_LOTE",
            categoria="Recria",
            raca="Nelore",
            quantidade_cabecas=10,
            peso_medio_kg=250.0,
            peso_inicial_medio_kg=250.0,
            rendimento_carcaca_pct=50.0,
            valor_aquisicao_total=20000.0,
            data_formacao=hoje - timedelta(days=60),
            ativo=True,
        ),
    ])
    await async_session.commit()

    manejo_svc = ManejoLoteService(tenant_id)
    await manejo_svc.registrar_evento(
        async_session,
        obj_in=ManejoLoteCreate(
            lote_id=lote_id,
            tipo_evento="NASCIMENTO",
            data_evento=hoje - timedelta(days=40),
            quantidade_cabecas=2,
        ),
    )
    await manejo_svc.registrar_evento(
        async_session,
        obj_in=ManejoLoteCreate(
            lote_id=lote_id,
            tipo_evento="COMPRA",
            data_evento=hoje - timedelta(days=35),
            quantidade_cabecas=3,
            custo_total=6000.0,
        ),
    )
    await manejo_svc.registrar_evento(
        async_session,
        obj_in=ManejoLoteCreate(
            lote_id=lote_id,
            tipo_evento="MORTE",
            data_evento=hoje - timedelta(days=32),
            quantidade_cabecas=1,
        ),
    )
    await manejo_svc.registrar_evento(
        async_session,
        obj_in=ManejoLoteCreate(
            lote_id=lote_id,
            tipo_evento="PESAGEM",
            data_evento=hoje - timedelta(days=30),
            quantidade_cabecas=14,
            peso_total_kg=3920.0,  # 280 kg/cab
        ),
    )
    await manejo_svc.registrar_evento(
        async_session,
        obj_in=ManejoLoteCreate(
            lote_id=lote_id,
            tipo_evento="PESAGEM",
            data_evento=hoje,
            quantidade_cabecas=14,
            peso_total_kg=4340.0,  # 310 kg/cab -> +30 kg em 30d = 1.0 kg/dia
        ),
    )
    await async_session.commit()

    lote = await async_session.get(LoteAnimal, lote_id)
    assert lote is not None
    assert lote.quantidade_cabecas == 14
    assert lote.peso_medio_kg == pytest.approx(310.0)
    assert lote.valor_aquisicao_total == pytest.approx(26000.0)

    with pytest.raises(BusinessRuleError, match="Saldo insuficiente"):
        await manejo_svc.registrar_evento(
            async_session,
            obj_in=ManejoLoteCreate(
                lote_id=lote_id,
                tipo_evento="VENDA",
                data_evento=hoje,
                quantidade_cabecas=99,
            ),
        )
    await async_session.rollback()

    ind = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_id)
    assert ind.modo_gestao == "POR_LOTE"
    assert ind.quantidade_animais == 14
    assert ind.peso_total_kg == pytest.approx(4340.0)
    assert ind.peso_medio_kg == pytest.approx(310.0)
    assert ind.ultima_pesagem == hoje
    assert ind.gmd_medio_kg_dia == pytest.approx(1.0)
    # ganho = (310 - 250) * 14 = 840 kg PV -> 840 / 30 = 28.0 @ produzidas
    assert ind.arrobas_produzidas == pytest.approx(28.0)


@pytest.mark.asyncio
async def test_hibrido_por_lote_e_misto_indicadores_dashboard_e_cotacao(
    async_session: AsyncSession, monkeypatch
) -> None:
    async def _fake_cotacao(_session=None):
        return (320.0, "DERAL/PR")

    monkeypatch.setattr(cotacao_arroba_service, "obter_cotacao_boi_gordo_referencia", _fake_cotacao)

    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    piquete_id = uuid.uuid4()
    lote_por_lote_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Híbrida", slug="faz-hib", documento="44444444000104"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade Principal"),
        AreaRural(
            id=piquete_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            nome="Piquete Brachiaria",
            tipo="PIQUETE",
            area_hectares=25.0,
            ativo=True,
        ),
        LoteAnimal(
            id=lote_por_lote_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            area_id=piquete_id,
            identificacao="Lote Extensivo 50",
            modo_gestao="POR_LOTE",
            categoria="Recria",
            raca="Nelore",
            quantidade_cabecas=50,
            peso_medio_kg=300.0,
            peso_inicial_medio_kg=240.0,
            rendimento_carcaca_pct=50.0,
            valor_aquisicao_total=150000.0,
            cotacao_arroba_override=310.0,
            ativo=True,
        ),
        LancamentoFinanceiro(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            descricao="Sal mineral lote 50",
            valor=1500.0,
            data=date(2026, 11, 10),
            tipo="CUSTO",
            categoria="NUTRICAO",
            origem="PECUARIA_NUTRICAO",
            origem_id=lote_por_lote_id,
        ),
        ManejoLote(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            lote_id=lote_por_lote_id,
            tipo_evento="VACINACAO",
            data_evento=date(2026, 11, 10),
            quantidade_cabecas=50,
            custo_total=500.0,
        ),
    ])
    await async_session.commit()

    ind = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_por_lote_id)
    assert ind.quantidade_animais == 50
    assert ind.peso_total_kg == pytest.approx(15000.0)
    assert ind.arrobas_totais == pytest.approx(500.0)
    assert ind.arrobas_produzidas == pytest.approx(100.0)
    assert ind.lotacao_ua_ha == pytest.approx(1.33, rel=1e-2)
    assert ind.custo_sanitario_total == pytest.approx(500.0)
    assert ind.custo_nutricao_total == pytest.approx(1500.0)
    assert ind.custo_total_operacional == pytest.approx(2000.0)
    assert ind.custo_total_por_arroba == pytest.approx(4.0)
    assert ind.custo_por_arroba_produzida == pytest.approx(20.0)
    assert ind.custo_break_even_por_arroba == pytest.approx(304.0)
    assert ind.cotacao_arroba_referencia == pytest.approx(310.0)
    assert ind.fonte_cotacao == "Personalizado"
    assert ind.valor_mercado_estimado == pytest.approx(155000.0)
    assert ind.margem_bruta_estimada == pytest.approx(3000.0)
    assert ind.margem_estimada_por_cabeca == pytest.approx(60.0)

    resumo = await PecuariaDashboardResumoService(async_session, tenant_id, fazenda_id).resumir()
    assert resumo.animais_ativos == 50
    assert resumo.peso_total_kg == pytest.approx(15000.0)
    assert resumo.arrobas_totais == pytest.approx(500.0)
    assert resumo.ua_total == pytest.approx(33.33, rel=1e-2)
    assert resumo.custo_operacional_acumulado == pytest.approx(2000.0)
    assert resumo.custo_total_por_arroba == pytest.approx(4.0)
    assert resumo.custo_break_even_por_arroba == pytest.approx(304.0)
    assert resumo.valor_mercado_estimado == pytest.approx(155000.0)
    assert resumo.margem_bruta_estimada == pytest.approx(3000.0)

    # Cenário misto: adiciona lote INDIVIDUAL com 2 animais + 1 animal avulso sem lote_id
    lote_ind_id = uuid.uuid4()
    async_session.add_all([
        LoteAnimal(
            id=lote_ind_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            identificacao="Lote Elite",
            modo_gestao="INDIVIDUAL",
            rendimento_carcaca_pct=50.0,
            ativo=True,
        ),
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote_ind_id,
            categoria="BOI",
            sexo="MACHO",
            status="ATIVO",
            peso_atual_kg=450.0,
        ),
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote_ind_id,
            categoria="BOI",
            sexo="MACHO",
            status="ATIVO",
            peso_atual_kg=450.0,
        ),
        Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=None,
            categoria="TOURO",
            sexo="MACHO",
            status="ATIVO",
            peso_atual_kg=600.0,
        ),
    ])
    await async_session.commit()

    resumo_misto = await PecuariaDashboardResumoService(async_session, tenant_id, fazenda_id).resumir()
    # 50 (POR_LOTE) + 2 (INDIVIDUAL) + 1 (sem lote) = 53 cabeças
    # Peso: 15000 + 900 + 600 = 16500 kg -> @: 500 + 30 + 20 = 550 @
    assert resumo_misto.animais_ativos == 53
    assert resumo_misto.peso_total_kg == pytest.approx(16500.0)
    assert resumo_misto.arrobas_totais == pytest.approx(550.0)
    # Valor mercado misto: 500@ * 310 (override lote 1) + 50@ * 320 (DERAL/PR) = 155000 + 16000 = 171000
    assert resumo_misto.cotacao_arroba_referencia == pytest.approx(320.0)
    assert resumo_misto.fonte_cotacao == "DERAL/PR"
    assert resumo_misto.valor_mercado_estimado == pytest.approx(171000.0)

    # Fallback seguro quando cotação pública falha/indisponível
    async def _sem_cotacao(_session=None):
        return (None, None)

    monkeypatch.setattr(cotacao_arroba_service, "obter_cotacao_boi_gordo_referencia", _sem_cotacao)
    ind_sem_pub = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_ind_id)
    assert ind_sem_pub.cotacao_arroba_referencia is None
    assert ind_sem_pub.fonte_cotacao is None
    assert ind_sem_pub.valor_mercado_estimado is None


async def _async_const(value):
    return value
