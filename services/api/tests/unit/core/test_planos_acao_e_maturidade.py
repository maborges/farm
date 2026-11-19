from datetime import date, timedelta
import uuid

import pytest
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from agricola.caderno.models import VisitaTecnica
from agricola.custos.models import CostAllocation
from agricola.safras.models import Safra
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import EntityNotFoundError
from core.models.auth import Usuario
from core.models.maturidade import MaturidadeSnapshot
from core.models.plano_acao import PlanoAcaoGerencial
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.schemas.plano_acao_schemas import PlanoAcaoCreate, PlanoAcaoUpdate
from core.services.maturidade_service import MaturidadeService
from core.services.plano_acao_service import PlanoAcaoService
from financeiro.models.lancamento import LancamentoFinanceiro
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.producao.models import ProducaoLeite


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
            lambda sync_conn: PlanoAcaoGerencial.__table__.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Usuario.__table__,
                    UnidadeProdutiva.__table__,
                    AreaRural.__table__,
                    Safra.__table__,
                    LoteAnimal.__table__,
                    Animal.__table__,
                    EventoAnimal.__table__,
                    ProducaoLeite.__table__,
                    TarefaCampo.__table__,
                    VisitaTecnica.__table__,
                    CostAllocation.__table__,
                    LancamentoFinanceiro.__table__,
                    PlanoAcaoGerencial.__table__,
                    MaturidadeSnapshot.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_planos_acao_ciclo_completo_e_isolamento_tenant(async_session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    async_session.add_all([
        Tenant(id=tenant_a, nome="Fazenda A", slug="faz-a", documento="11111111000101"),
        Tenant(id=tenant_b, nome="Fazenda B", slug="faz-b", documento="22222222000102"),
    ])
    await async_session.commit()

    svc_a = PlanoAcaoService(async_session, tenant_a)
    svc_b = PlanoAcaoService(async_session, tenant_b)

    plano = await svc_a.criar(
        PlanoAcaoCreate(
            titulo="Reduzir custo de adubação em 10%",
            origem_indicador="CUSTO_HECTARE_ACIMA_MEDIA",
            responsavel_nome="Eng. Marcos",
            meta="R$ 4.200/ha",
            prazo=date.today() + timedelta(days=15),
        )
    )
    assert plano.status == "ABERTO"

    # Plano com prazo vencido deve aparecer como ATRASADO
    atrasado = await svc_a.criar(
        PlanoAcaoCreate(
            titulo="Regularizar pesagem do lote",
            prazo=date.today() - timedelta(days=2),
        )
    )
    assert atrasado.status == "ATRASADO"

    lista_a = await svc_a.listar()
    assert len(lista_a) == 2
    assert await svc_b.listar() == []

    # Isolamento: tenant_b não consegue atualizar nem excluir plano do tenant_a
    with pytest.raises(EntityNotFoundError):
        await svc_b.atualizar(plano.id, PlanoAcaoUpdate(status="CONCLUIDO"))
    with pytest.raises(EntityNotFoundError):
        await svc_b.excluir(plano.id)

    atualizado = await svc_a.atualizar(
        plano.id,
        PlanoAcaoUpdate(status="CONCLUIDO", resultado_obtido="Meta atingida na compra antecipada"),
    )
    assert atualizado.status == "CONCLUIDO"
    assert atualizado.concluido_em is not None
    assert atualizado.resultado_obtido == "Meta atingida na compra antecipada"


@pytest.mark.asyncio
async def test_maturidade_calcula_score_com_dados_parciais_e_tendencia(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Mista", slug="faz-mista", documento="33333333000103"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade Principal"),
        AreaRural(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            nome="Talhão 01",
            tipo="TALHAO",
            area_hectares=50.0,
            ativo=True,
        ),
        Safra(id=uuid.uuid4(), tenant_id=tenant_id, ano_safra="2026", status="EM_ANDAMENTO"),
        LancamentoFinanceiro(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            descricao="Compra sementes",
            valor=12000.0,
            data=date(2026, 11, 1),
            tipo="CUSTO",
        ),
        MaturidadeSnapshot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            competencia="2026-10",
            score_geral=40.0,
            pilar_operacional=40.0,
            pilar_agronomico_zootecnico=40.0,
            pilar_economico=40.0,
            pilar_financeiro=40.0,
            detalhes={},
        ),
    ])
    await async_session.commit()

    resumo = await MaturidadeService(async_session, tenant_id, fazenda_id).calcular_e_registrar()

    # Operacional: 30 (unidade) + 30 (área) + 20 (sem tarefas mas com área) = 80.0
    # Agro/Zoo: 60 (safra) + 0 (sem visita) = 60.0
    # Econômico: 0.0 (sem alocações/leite/planos)
    # Financeiro: 50.0 (custo lançado, sem receita)
    # Geral = (80 + 60 + 0 + 50) / 4 = 47.5; Tendência = 47.5 - 40.0 = +7.5
    assert resumo["score_geral"] == pytest.approx(47.5, rel=1e-3)
    assert resumo["tendencia_mes_anterior"] == pytest.approx(7.5, rel=1e-3)
    assert len(resumo["pilares"]) == 4
    assert len(resumo["pontos_melhoria"]) == 3


@pytest.mark.asyncio
async def test_maturidade_fazenda_vazia_nao_falha(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    async_session.add(Tenant(id=tenant_id, nome="Fazenda Nova", slug="faz-nova", documento="44444444000104"))
    await async_session.commit()

    resumo = await MaturidadeService(async_session, tenant_id).calcular_e_registrar()
    assert resumo["score_geral"] == 0.0
    assert resumo["tendencia_mes_anterior"] is None
    assert len(resumo["pontos_melhoria"]) == 4
    assert resumo["governanca_financeira"]["status_governanca_esg"] == "SEM_CAPEX"


@pytest.mark.asyncio
async def test_plano_acao_com_capex_calcula_viabilidade_e_reflete_na_maturidade(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Governança", slug="faz-gov", documento="55555555000105"),
        LancamentoFinanceiro(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            descricao="Adubo",
            valor=10000.0,
            data=date(2026, 11, 1),
            tipo="CUSTO",
        ),
    ])
    await async_session.commit()

    svc_plano = PlanoAcaoService(async_session, tenant_id)
    plano_viavel = await svc_plano.criar(
        PlanoAcaoCreate(
            titulo="Instalar Pivô Leste",
            prazo=date.today() + timedelta(days=30),
            investimento_estimado=500_000.0,
            retorno_anual_estimado=200_000.0,
            horizonte_anos=5,
            tma_aa=12.0,
            prazo_maximo_payback_anos=4.0,
        )
    )
    assert getattr(plano_viavel, "viabilidade", None) is not None
    assert plano_viavel.viabilidade.vpl > 0
    assert plano_viavel.viabilidade.veredito_final == "VIAVEL"

    maturidade_solida = await MaturidadeService(async_session, tenant_id).calcular_e_registrar()
    fin_solido = next(p for p in maturidade_solida["pilares"] if p["chave"] == "financeiro")
    assert maturidade_solida["governanca_financeira"]["status_governanca_esg"] == "SOLIDA"
    assert fin_solido["score"] == 65.0  # 50.0 (custo) + 15.0 bônus governança CapEx

    # Adiciona plano inviável aberto e verifica penalização no pilar financeiro
    plano_inviavel = await svc_plano.criar(
        PlanoAcaoCreate(
            titulo="Armazém Superdimensionado",
            prazo=date.today() + timedelta(days=30),
            investimento_estimado=1_000_000.0,
            retorno_anual_estimado=120_000.0,
            horizonte_anos=5,
            tma_aa=15.0,
        )
    )
    assert plano_inviavel.viabilidade.vpl < 0
    assert plano_inviavel.viabilidade.veredito_final == "INVIAVEL"

    maturidade_atencao = await MaturidadeService(async_session, tenant_id).calcular_e_registrar()
    fin_atencao = next(p for p in maturidade_atencao["pilares"] if p["chave"] == "financeiro")
    assert maturidade_atencao["governanca_financeira"]["status_governanca_esg"] == "ATENCAO"
    assert maturidade_atencao["governanca_financeira"]["projetos_capex_inviaveis"] == 1
    assert fin_atencao["score"] == 35.0  # 50.0 (custo) - 15.0 penalidade CapEx inviável aberto
