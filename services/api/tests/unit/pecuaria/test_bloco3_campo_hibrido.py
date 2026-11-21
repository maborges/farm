from __future__ import annotations

import json
import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import event, select
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
from core.cadastros.produtos.models import Produto, ProdutoEstoque, TipoProduto
from core.cadastros.propriedades.models import AreaRural
from core.measurements.models import UnidadeMedida
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from events.outbox_model import DomainEventOutbox
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito, EstoqueMovimento, LoteEstoque, SaldoEstoque
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.producao.models import ProducaoLeite
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from pecuaria.services.manejo_sync_service import ManejoSyncService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _serialize_list_params(
        _conn, _cursor, statement, parameters, _context, executemany
    ):
        def _conv(val: object) -> object:
            return json.dumps(val) if isinstance(val, list) else val

        if executemany:
            parameters = [
                tuple(_conv(v) for v in row) if isinstance(row, tuple) else _conv(row)
                for row in parameters
            ]
        elif isinstance(parameters, tuple):
            parameters = tuple(_conv(v) for v in parameters)
        elif isinstance(parameters, list):
            parameters = [_conv(v) for v in parameters]
        return statement, parameters

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
                    ProdutoEstoque.__table__,
                    Deposito.__table__,
                    LoteEstoque.__table__,
                    SaldoEstoque.__table__,
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
                    DomainEventOutbox.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _criar_base_pecuaria(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    outro_tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    piquete_a_id = uuid.uuid4()
    piquete_b_id = uuid.uuid4()
    session.add_all([
        Tenant(id=tenant_id, nome="T Campo", slug="t-campo", documento="11111111000101"),
        Tenant(id=outro_tenant_id, nome="T Outro", slug="t-outro", documento="22222222000102"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda Campo"),
        AreaRural(
            id=piquete_a_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            tipo="PIQUETE",
            nome="Piquete A",
            area_hectares=20.0,
            ativo=True,
        ),
        AreaRural(
            id=piquete_b_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            tipo="PIQUETE",
            nome="Piquete B",
            area_hectares=30.0,
            ativo=True,
        ),
    ])
    await session.commit()
    return tenant_id, outro_tenant_id, fazenda_id, piquete_a_id, piquete_b_id


def _nova_tarefa(
    *,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    tipo: str,
    lote_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    dados: dict | None = None,
) -> TarefaCampo:
    return TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        origem="MANUAL",
        status="CONCLUIDA",
        status_execucao="CONCLUIDA",
        type=tipo,
        module="pecuaria",
        unidade_produtiva_id=fazenda_id,
        area_rural_id=area_id,
        lote_id=lote_id,
        concluida_em=datetime(2026, 11, 20, 10, 0, 0),
        dados=dados or {},
    )


@pytest.mark.asyncio
async def test_campo_pesagem_coletiva_por_lote_e_idempotencia(
    async_session: AsyncSession,
) -> None:
    tenant_id, _, fazenda_id, piquete_a_id, _ = await _criar_base_pecuaria(async_session)
    lote = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Engorda Coletivo",
        modo_gestao="POR_LOTE",
        categoria="Novilhos",
        raca="Nelore",
        quantidade_cabecas=10,
        peso_medio_kg=400.0,
        peso_inicial_medio_kg=None,
        ativo=True,
    )
    async_session.add(lote)
    await async_session.flush()

    tarefa = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="PESAGEM",
        lote_id=lote.id,
        dados={
            "lote_id": str(lote.id),
            "tipo_pesagem": "LOTE_BALANCA",
            "peso_medio_kg": 430.0,
            "quantidade_animais": 10,
            "animais": [],
            "observacoes": "Pesagem curral balança",
        },
    )
    async_session.add(tarefa)
    await async_session.commit()

    sync_svc = ManejoSyncService(async_session, tenant_id)
    resultado = await sync_svc.processar_tarefa_campo(tarefa.id)
    assert resultado.status == "SUCCESS"
    assert resultado.total_processado == 10

    manejos = (
        await async_session.execute(
            select(ManejoLote).where(ManejoLote.lote_id == lote.id, ManejoLote.tipo_evento == "PESAGEM")
        )
    ).scalars().all()
    assert len(manejos) == 1
    assert manejos[0].quantidade_cabecas == 10
    assert manejos[0].peso_total_kg == pytest.approx(4300.0)

    await async_session.refresh(lote)
    assert lote.peso_medio_kg == pytest.approx(430.0)
    assert lote.peso_inicial_medio_kg == pytest.approx(430.0)

    reproc = await sync_svc.processar_tarefa_campo(tarefa.id)
    assert reproc.status == "IGNORED"
    manejos_apos = (
        await async_session.execute(select(ManejoLote).where(ManejoLote.lote_id == lote.id))
    ).scalars().all()
    assert len(manejos_apos) == 1


@pytest.mark.asyncio
async def test_campo_vacinacao_coletiva_por_lote_baixa_estoque(
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import operacional.services.estoque_ledger as ledger_mod

    orig_resolver = ledger_mod.resolver_unidade_medida_id

    async def _resolver_uuid(session: AsyncSession, produto_id: uuid.UUID) -> uuid.UUID:
        res = await orig_resolver(session, produto_id)
        return res if isinstance(res, uuid.UUID) else uuid.UUID(str(res))

    monkeypatch.setattr(ledger_mod, "resolver_unidade_medida_id", _resolver_uuid)

    tenant_id, _, fazenda_id, piquete_a_id, _ = await _criar_base_pecuaria(async_session)
    lote = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Sanidade Coletivo",
        modo_gestao="POR_LOTE",
        categoria="Bezerros",
        raca="Nelore",
        quantidade_cabecas=10,
        peso_medio_kg=220.0,
        ativo=True,
    )
    uom = UnidadeMedida(
        codigo="ML",
        nome="Mililitro",
        dimensao="VOLUME",
        codigo_referencia="L",
        fator_referencia=0.001,
        sistema=True,
        ativo=True,
    )
    produto = Produto(
        tenant_id=tenant_id,
        nome="Vacina Aftosa",
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        preco_medio=4.0,
        ativo=True,
    )
    deposito = Deposito(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        nome="Farmácia Sede",
        tipo="GERAL",
        ativo=True,
    )
    async_session.add_all([lote, uom, produto, deposito])
    await async_session.flush()

    saldo = SaldoEstoque(
        deposito_id=deposito.id,
        produto_id=produto.id,
        quantidade_atual=100.0,
        quantidade_reservada=0.0,
    )
    tarefa = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="VACINACAO",
        lote_id=lote.id,
        area_id=piquete_a_id,
        dados={
            "lote_id": str(lote.id),
            "area_id": str(piquete_a_id),
            "produto_id": str(produto.id),
            "dose": 5.0,
            "unidade_medida": "ML",
            "quantidade_animais": 10,
            "animais_ids": [],
            "observacoes": "Campanha aftosa",
        },
    )
    async_session.add_all([saldo, tarefa])
    await async_session.commit()

    resultado = await ManejoSyncService(async_session, tenant_id).processar_tarefa_campo(tarefa.id)
    assert resultado.status == "SUCCESS", f"Erros: {resultado.erros}"
    assert resultado.total_processado == 10

    await async_session.refresh(saldo)
    assert saldo.quantidade_atual == pytest.approx(50.0)

    manejos = (
        await async_session.execute(
            select(ManejoLote).where(ManejoLote.lote_id == lote.id, ManejoLote.tipo_evento == "VACINACAO")
        )
    ).scalars().all()
    assert len(manejos) == 1
    assert manejos[0].quantidade_cabecas == 10
    assert manejos[0].produto_id == produto.id


@pytest.mark.asyncio
async def test_campo_morte_hibrida_por_lote_e_individual(
    async_session: AsyncSession,
) -> None:
    tenant_id, _, fazenda_id, _, _ = await _criar_base_pecuaria(async_session)
    lote_col = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Morte Coletivo",
        modo_gestao="POR_LOTE",
        categoria="Recria",
        raca="Nelore",
        quantidade_cabecas=12,
        peso_medio_kg=300.0,
        ativo=True,
    )
    lote_ind = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Morte Individual",
        modo_gestao="INDIVIDUAL",
        categoria="BOI",
        raca="Angus",
        quantidade_cabecas=2,
        peso_medio_kg=450.0,
        ativo=True,
    )
    async_session.add_all([lote_col, lote_ind])
    await async_session.flush()

    animal_1 = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        lote_id=lote_ind.id,
        numero_brinco="BR-M1",
        categoria="BOI",
        sexo="CASTRADO",
        peso_atual_kg=400.0,
        status="ATIVO",
    )
    animal_2 = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        lote_id=lote_ind.id,
        numero_brinco="BR-M2",
        categoria="BOI",
        sexo="CASTRADO",
        peso_atual_kg=500.0,
        status="ATIVO",
    )
    async_session.add_all([animal_1, animal_2])
    await async_session.flush()

    tarefa_col = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MORTE_REGISTRO",
        lote_id=lote_col.id,
        dados={"lote_id": str(lote_col.id), "quantidade_cabecas": 2, "causa_morte": "Raio"},
    )
    tarefa_excesso = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MORTE_REGISTRO",
        lote_id=lote_col.id,
        dados={"lote_id": str(lote_col.id), "quantidade_cabecas": 99, "causa_morte": "Erro"},
    )
    tarefa_ind = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MORTE_REGISTRO",
        lote_id=lote_ind.id,
        dados={"lote_id": str(lote_ind.id), "animal_id": str(animal_1.id), "causa_morte": "Acidente"},
    )
    async_session.add_all([tarefa_col, tarefa_excesso, tarefa_ind])
    await async_session.commit()
    tarefa_col_id = tarefa_col.id
    tarefa_excesso_id = tarefa_excesso.id
    tarefa_ind_id = tarefa_ind.id

    sync_svc = ManejoSyncService(async_session, tenant_id)
    res_col = await sync_svc.processar_tarefa_campo(tarefa_col_id)
    assert res_col.status == "SUCCESS"
    await async_session.refresh(lote_col)
    assert lote_col.quantidade_cabecas == 10

    res_exc = await sync_svc.processar_tarefa_campo(tarefa_excesso_id)
    assert res_exc.status == "ERROR"
    await async_session.refresh(lote_col)
    assert lote_col.quantidade_cabecas == 10

    res_ind = await sync_svc.processar_tarefa_campo(tarefa_ind_id)
    assert res_ind.status == "SUCCESS"
    await async_session.refresh(animal_1)
    await async_session.refresh(lote_ind)
    assert animal_1.status == "MORTO"
    assert lote_ind.quantidade_cabecas == 1
    assert lote_ind.peso_medio_kg == pytest.approx(500.0)


@pytest.mark.asyncio
async def test_campo_nascimento_coletivo_e_movimentacao_hibrida(
    async_session: AsyncSession,
) -> None:
    tenant_id, outro_tenant_id, fazenda_id, piquete_a_id, piquete_b_id = await _criar_base_pecuaria(
        async_session
    )
    fazenda_outro = uuid.uuid4()
    piquete_outro = uuid.uuid4()
    lote_col = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Cria Coletivo",
        modo_gestao="POR_LOTE",
        categoria="Bezerros",
        raca="Nelore",
        quantidade_cabecas=15,
        peso_medio_kg=180.0,
        ativo=True,
    )
    lote_ind = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Destino Individual",
        modo_gestao="INDIVIDUAL",
        categoria="BOI",
        raca="Angus",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        ativo=True,
    )
    lote_origem_ind = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Origem Individual",
        modo_gestao="INDIVIDUAL",
        categoria="BOI",
        raca="Angus",
        quantidade_cabecas=1,
        peso_medio_kg=420.0,
        ativo=True,
    )
    async_session.add_all([
        UnidadeProdutiva(id=fazenda_outro, tenant_id=outro_tenant_id, nome="Outra Fazenda"),
        AreaRural(
            id=piquete_outro,
            tenant_id=outro_tenant_id,
            unidade_produtiva_id=fazenda_outro,
            tipo="PIQUETE",
            nome="Piquete Outro Tenant",
            area_hectares=10.0,
            ativo=True,
        ),
        lote_col,
        lote_ind,
        lote_origem_ind,
    ])
    await async_session.flush()

    boi = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        lote_id=lote_origem_ind.id,
        numero_brinco="BR-MOV-1",
        categoria="BOI",
        sexo="CASTRADO",
        peso_atual_kg=420.0,
        status="ATIVO",
    )
    async_session.add(boi)
    await async_session.flush()

    t_nasc = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="NASCIMENTO_LOTE",
        lote_id=lote_col.id,
        dados={"lote_id": str(lote_col.id), "quantidade_cabecas": 3},
    )
    t_nasc_ind_err = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="NASCIMENTO_LOTE",
        lote_id=lote_origem_ind.id,
        dados={"lote_id": str(lote_origem_ind.id), "quantidade_cabecas": 1},
    )
    t_mov_piq = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MOVIMENTACAO_LOTE",
        lote_id=lote_col.id,
        dados={"lote_id": str(lote_col.id), "area_destino_id": str(piquete_b_id)},
    )
    t_mov_cross = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MOVIMENTACAO_LOTE",
        lote_id=lote_col.id,
        dados={"lote_id": str(lote_col.id), "area_destino_id": str(piquete_outro)},
    )
    t_mov_ind = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MOVIMENTACAO_LOTE",
        lote_id=lote_origem_ind.id,
        dados={
            "lote_id": str(lote_origem_ind.id),
            "animal_id": str(boi.id),
            "lote_destino_id": str(lote_ind.id),
        },
    )
    async_session.add_all([t_nasc, t_nasc_ind_err, t_mov_piq, t_mov_cross, t_mov_ind])
    await async_session.commit()

    sync_svc = ManejoSyncService(async_session, tenant_id)
    assert (await sync_svc.processar_tarefa_campo(t_nasc.id)).status == "SUCCESS"
    assert (await sync_svc.processar_tarefa_campo(t_nasc_ind_err.id)).status == "ERROR"
    assert (await sync_svc.processar_tarefa_campo(t_mov_piq.id)).status == "SUCCESS"
    assert (await sync_svc.processar_tarefa_campo(t_mov_cross.id)).status == "ERROR"
    assert (await sync_svc.processar_tarefa_campo(t_mov_ind.id)).status == "SUCCESS"

    await async_session.refresh(lote_col)
    await async_session.refresh(boi)
    await async_session.refresh(lote_origem_ind)
    await async_session.refresh(lote_ind)
    assert lote_col.quantidade_cabecas == 18
    assert lote_col.area_id == piquete_b_id
    assert boi.lote_id == lote_ind.id
    assert lote_origem_ind.quantidade_cabecas == 0
    assert lote_ind.quantidade_cabecas == 1
    assert lote_ind.peso_medio_kg == pytest.approx(420.0)


@pytest.mark.asyncio
async def test_campo_medicacao_hibrida_e_reflexo_economico(
    async_session: AsyncSession,
) -> None:
    tenant_id, _, fazenda_id, piquete_a_id, _ = await _criar_base_pecuaria(async_session)
    lote_col = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        area_id=piquete_a_id,
        identificacao="Lote Med Coletivo",
        modo_gestao="POR_LOTE",
        categoria="Novilhos",
        raca="Nelore",
        quantidade_cabecas=10,
        peso_medio_kg=300.0,
        ativo=True,
    )
    lote_ind = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Med Individual",
        modo_gestao="INDIVIDUAL",
        categoria="BOI",
        raca="Angus",
        quantidade_cabecas=1,
        peso_medio_kg=450.0,
        ativo=True,
    )
    med = Produto(
        tenant_id=tenant_id,
        nome="Vermífugo Ivermectina",
        tipo=TipoProduto.MEDICAMENTO.value,
        unidade_medida="ML",
        ativo=True,
    )
    async_session.add_all([lote_col, lote_ind, med])
    await async_session.flush()

    boi = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        lote_id=lote_ind.id,
        numero_brinco="BR-MED-1",
        categoria="BOI",
        sexo="CASTRADO",
        peso_atual_kg=450.0,
        status="ATIVO",
    )
    async_session.add(boi)
    await async_session.flush()

    t_med_col = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MEDICACAO_ANIMAL",
        lote_id=lote_col.id,
        dados={
            "lote_id": str(lote_col.id),
            "produto_id": str(med.id),
            "dose": 6.0,
            "unidade_medida": "ML",
            "custo_total": 250.0,
            "observacoes": "Vermífugo",
        },
    )
    t_med_ind = _nova_tarefa(
        tenant_id=tenant_id,
        fazenda_id=fazenda_id,
        tipo="MEDICACAO_ANIMAL",
        lote_id=lote_ind.id,
        dados={
            "lote_id": str(lote_ind.id),
            "animal_id": str(boi.id),
            "produto_id": str(med.id),
            "dose": 10.0,
            "unidade_medida": "ML",
            "custo_total": 35.0,
            "observacoes": "Tratamento individual",
        },
    )
    async_session.add_all([t_med_col, t_med_ind])
    await async_session.commit()

    sync_svc = ManejoSyncService(async_session, tenant_id)
    assert (await sync_svc.processar_tarefa_campo(t_med_col.id)).status == "SUCCESS"
    assert (await sync_svc.processar_tarefa_campo(t_med_ind.id)).status == "SUCCESS"

    indicadores = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_col.id)
    assert indicadores.custo_sanitario_total == pytest.approx(250.0)

    ev_ind = await async_session.scalar(
        select(EventoAnimal).where(
            EventoAnimal.animal_id == boi.id,
            EventoAnimal.tipo == "MEDICACAO",
        )
    )
    assert ev_ind is not None
    assert ev_ind.produto_id == med.id
    assert ev_ind.valor == pytest.approx(35.0)
