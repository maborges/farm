import pytest
import uuid
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.cadastros.produtos.models import Produto, TipoProduto
from core.measurements.models import UnidadeMedida
from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal
from pecuaria.services.manejo_sync_service import ManejoSyncService
from operacional.models.estoque import Deposito, EstoqueMovimento, SaldoEstoque
from test_operational_workflow_governance_step02 import _criar_production_unit, _garantir_unidade_ha
from test_operational_workflow_governance_step03 import _criar_area, _criar_cultivo, _criar_safra, _criar_unidade_produtiva, _garantir_tenant

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def sync_service(session: AsyncSession, tenant_id: uuid.UUID) -> ManejoSyncService:
    return ManejoSyncService(session, tenant_id)

async def _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=None, brinc="100", peso=100.0, ultima_pesagem=None):
    a = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        lote_id=lote_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco=brinc,
        data_entrada=date.today(),
        peso_atual_kg=peso,
        data_ultima_pesagem=ultima_pesagem
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


async def _criar_lote(session, tenant_id, unidade_produtiva_id, identificacao="Lote Sync"):
    from pecuaria.animal.models import LoteAnimal

    lote = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao=identificacao,
        especie="BOVINO",
        categoria="BEZERRO",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date.today(),
        ativo=True,
    )
    session.add(lote)
    await session.commit()
    await session.refresh(lote)
    return lote


async def _criar_produto_vacina(session, tenant_id, nome="Vacina Teste", *, preco_medio: float | None = None):
    produto = Produto(
        tenant_id=tenant_id,
        nome=nome,
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        preco_medio=preco_medio if preco_medio is not None else 0.0,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_deposito_com_saldo(
    session,
    tenant_id,
    unidade_produtiva_id,
    produto_id,
    *,
    quantidade=100.0,
    nome="Depósito Vacinas",
):
    await _garantir_unidade_medida(session, "ML", "Mililitro")
    await _garantir_unidade_medida(session, "UN", "Unidade")
    deposito = Deposito(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=nome,
        tipo="GERAL",
        ativo=True,
    )
    session.add(deposito)
    await session.flush()
    saldo = SaldoEstoque(
        deposito_id=deposito.id,
        produto_id=produto_id,
        quantidade_atual=quantidade,
        quantidade_reservada=0.0,
    )
    session.add(saldo)
    await session.commit()
    await session.refresh(deposito)
    await session.refresh(saldo)
    return deposito, saldo


async def _garantir_unidade_medida(session, codigo: str, nome: str):
    unidade = (
        await session.execute(
            select(UnidadeMedida).where(
                UnidadeMedida.tenant_id.is_(None),
                UnidadeMedida.codigo == codigo,
            )
        )
    ).scalars().first()
    if unidade:
        return unidade
    unidade = UnidadeMedida(
        tenant_id=None,
        codigo=codigo,
        nome=nome,
        dimensao="VOLUME" if codigo == "ML" else "CONTAGEM",
        codigo_canonico=codigo,
        fator_canonico=1,
        sistema=True,
        ativo=True,
        casas_decimais=2,
        eh_canonica=True,
    )
    session.add(unidade)
    await session.flush()
    return unidade

async def _criar_tarefa(
    session,
    tenant_id,
    module="pecuaria",
    type_="PESAGEM",
    status="CONCLUIDA",
    status_execucao="CONCLUIDA",
    dados=None,
    unidade_produtiva_id=None,
    area_rural_id=None,
):
    if dados is None:
        dados = {}
    
    t = TarefaCampo(
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        module=module,
        type=type_,
        status=status,
        status_execucao=status_execucao,
        client_id=str(uuid.uuid4()),
        dados=dados,
        origem="MANUAL",
        prioridade="NORMAL",
        unidade_produtiva_id=unidade_produtiva_id,
        area_rural_id=area_rural_id,
        localizacao_status="INDISPONIVEL",
        concluida_em=datetime.now(),
        client_created_at=datetime.now(),
        client_updated_at=datetime.now()
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def _criar_tarefa_vacinacao(session, tenant_id, produto_id, animais_ids, lote_id=None, area_id=None, dose=2.0, unidade_medida="ML", via_aplicacao="SUBCUTANEA", status="CONCLUIDA", status_execucao="CONCLUIDA"):
    dados = {
        "lote_id": str(lote_id) if lote_id else None,
        "area_id": str(area_id) if area_id else None,
        "tipo": "VACINACAO",
        "data_evento": "2026-06-23T00:00:00Z",
        "produto_id": str(produto_id),
        "dose": dose,
        "unidade_medida": unidade_medida,
        "via_aplicacao": via_aplicacao,
        "observacoes": "Vacinação teste",
        "animais_ids": [str(animal_id) for animal_id in animais_ids],
    }
    return await _criar_tarefa(
        session,
        tenant_id,
        module="pecuaria",
        type_="VACINACAO",
        status=status,
        status_execucao=status_execucao,
        dados=dados,
        unidade_produtiva_id=(await session.get(Animal, animais_ids[0])).unidade_produtiva_id if animais_ids else None,
        area_rural_id=area_id,
    )


async def test_sync_1_animal_valido(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="001", peso=100.0)
    
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [
            {
                "animal_id": str(animal.id),
                "peso_kg": 150.0,
                "data_evento": "2026-06-23"
            }
        ]
    })
    
    result = await sync_service.processar_tarefa_campo(tarefa.id)
    assert result.status == "SUCCESS"
    assert result.total_recebido == 1
    assert result.total_processado == 1
    assert result.total_ignorados == 0
    assert len(result.erros) == 0

    # Verifica BD
    await session.refresh(animal)
    assert animal.peso_atual_kg == 150.0
    assert animal.data_ultima_pesagem == date(2026, 6, 23)

    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id)
    evt = (await session.execute(stmt)).scalars().first()
    assert evt is not None
    assert evt.peso_kg == 150.0
    assert evt.tipo == "PESAGEM"


async def test_sync_multiplos_animais(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="002", peso=200.0)
    a2 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="003", peso=250.0)

    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [
            {"animal_id": str(a1.id), "peso_kg": 210.0},
            {"animal_id": str(a2.id), "peso_kg": 260.0}
        ]
    })

    result = await sync_service.processar_tarefa_campo(tarefa.id)
    assert result.status == "SUCCESS"
    assert result.total_processado == 2

    # Verifica BD
    await session.refresh(a1)
    await session.refresh(a2)
    assert a1.peso_atual_kg == 210.0
    assert a2.peso_atual_kg == 260.0


async def test_sync_pesagem_coletiva_lote_balanca_materializa_todos_animais_ativos(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    sync_service: ManejoSyncService,
):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, identificacao="Lote Coletivo")
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="P001", peso=180.0)
    a2 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="P002", peso=190.0)

    tarefa = await _criar_tarefa(
        session,
        tenant_id,
        type_="PESAGEM",
        dados={
            "lote_id": str(lote.id),
            "tipo_pesagem": "LOTE_BALANCA",
            "peso_medio_kg": 222.4,
            "quantidade_animais": 2,
            "observacoes": "Pesagem coletiva",
        },
        unidade_produtiva_id=unidade_produtiva_id,
    )

    result = await sync_service.processar_tarefa_campo(tarefa.id)
    assert result.status == "SUCCESS"
    assert result.total_processado == 2

    await session.refresh(a1)
    await session.refresh(a2)
    assert a1.peso_atual_kg == 222.4
    assert a2.peso_atual_kg == 222.4


async def test_sync_pesagem_nao_cria_movimento_estoque(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="002A", peso=200.0)
    tarefa = await _criar_tarefa(
        session,
        tenant_id,
        dados={"animais": [{"animal_id": str(animal.id), "peso_kg": 210.0}]},
    )

    result = await sync_service.processar_tarefa_campo(tarefa.id)
    assert result.status == "SUCCESS"

    movimentos = (await session.execute(select(EstoqueMovimento).where(EstoqueMovimento.origem_id == tarefa.id))).scalars().all()
    assert movimentos == []
    allocations = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source_id == tarefa.id,
            )
        )
    ).scalars().all()
    assert allocations == []


async def test_sync_idempotencia_reprocessamento(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="004", peso=100.0)

    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })

    # Primeira execução
    res1 = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res1.status == "SUCCESS"
    assert res1.total_processado == 1

    # Altera peso para verificar que não será sobrescrito se já foi processado
    a1.peso_atual_kg = 200.0
    await session.commit()

    # Reprocessamento
    res2 = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res2.status == "SUCCESS"
    assert res2.total_processado == 0
    assert res2.total_ignorados == 1

    # Verifica Eventos: Deve haver apenas 1
    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id)
    evts = (await session.execute(stmt)).scalars().all()
    assert len(evts) == 1

    await session.refresh(a1)
    assert a1.peso_atual_kg == 200.0


async def test_sync_rejeitar_modulo_agricola(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="005")
    tarefa = await _criar_tarefa(session, tenant_id, module="agricola", dados={"animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]})
    
    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "IGNORED"


async def test_sync_rejeitar_tarefa_pendente(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="006")
    tarefa = await _criar_tarefa(session, tenant_id, status="PENDENTE", status_execucao="PENDENTE", dados={"animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]})
    
    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "IGNORED"


async def test_sync_rejeitar_outro_tenant(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    # Animal criado no OUTRO tenant
    a1 = await _criar_animal(session, outro_tenant_id, unidade_produtiva_id, brinc="007")
    tarefa = await _criar_tarefa(session, tenant_id, dados={"animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]})
    
    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("não encontrado neste tenant" in e for e in res.erros)


async def test_sync_rejeitar_peso_zero_negativo(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="008")
    tarefa = await _criar_tarefa(session, tenant_id, dados={"animais": [{"animal_id": str(a1.id), "peso_kg": -10.0}]})
    
    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("Peso inválido" in e for e in res.erros)


async def test_sync_processar_vacinacao_cria_eventos_por_animal(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Sync Vacinação 1")
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="200", peso=120.0)
    a2 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="201", peso=130.0)
    produto = await _criar_produto_vacina(session, tenant_id)
    deposito, saldo = await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=25.0)
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto.id, [a1.id, a2.id], lote_id=lote.id)

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "SUCCESS", res.erros
    assert res.total_recebido == 2
    assert res.total_processado == 2
    assert res.total_ignorados == 0

    await session.refresh(a1)
    await session.refresh(a2)
    assert a1.peso_atual_kg == 120.0
    assert a2.peso_atual_kg == 130.0
    assert a1.data_ultima_pesagem is None
    assert a2.data_ultima_pesagem is None

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert len(eventos) == 2
    assert {evt.tipo for evt in eventos} == {"VACINACAO"}
    assert {evt.produto_id for evt in eventos} == {produto.id}

    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                EstoqueMovimento.origem_id == tarefa.id,
                EstoqueMovimento.produto_id == produto.id,
            )
        )
    ).scalars().one()
    await session.refresh(saldo)
    assert movimento.tipo_movimento == "SAIDA"
    assert float(movimento.quantidade) == pytest.approx(-4.0)
    assert movimento.tenant_id == tenant_id
    assert movimento.deposito_id == deposito.id
    assert deposito.unidade_produtiva_id == unidade_produtiva_id
    assert movimento.origem == "PECUARIA_VACINACAO"
    assert movimento.origem_id == tarefa.id
    assert "PECUARIA_VACINACAO" in (movimento.observacoes or "")
    assert saldo.quantidade_atual == pytest.approx(21.0)


async def test_sync_vacinacao_alias_sem_animais_ids_resolve_animais_do_lote(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    sync_service: ManejoSyncService,
):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Vacina Alias")
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="V001", peso=120.0)
    a2 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="V002", peso=130.0)
    produto = await _criar_produto_vacina(session, tenant_id, nome="Vacina Alias")
    await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=25.0)

    tarefa = await _criar_tarefa(
        session,
        tenant_id,
        module="pecuaria",
        type_="VACINACAO",
        status="CONCLUIDA",
        status_execucao="CONCLUIDA",
        unidade_produtiva_id=unidade_produtiva_id,
        dados={
            "lote_id": str(lote.id),
            "vacina_id": str(produto.id),
            "vacina_nome": produto.nome,
            "dose_ml": 2.5,
            "observacoes": "Vacinação manual legada",
        },
    )

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "SUCCESS", res.erros
    assert res.total_processado == 2

    eventos = (
        await session.execute(
            select(EventoAnimal).where(
                EventoAnimal.tarefa_campo_id == tarefa.id,
                EventoAnimal.tipo == "VACINACAO",
            )
        )
    ).scalars().all()
    assert len(eventos) == 2
    assert {evento.animal_id for evento in eventos} == {a1.id, a2.id}


async def test_sync_vacinacao_calcula_custo_total_no_movimento(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    lote = await _criar_lote(session, tenant_id, unidade_id, "Lote Custo Vacinação")
    a1 = await _criar_animal(session, tenant_id, unidade_id, lote_id=lote.id, brinc="300", peso=180.0)
    a2 = await _criar_animal(session, tenant_id, unidade_id, lote_id=lote.id, brinc="301", peso=185.0)
    produto = await _criar_produto_vacina(session, tenant_id, "Vacina Custo", preco_medio=4.0)
    deposito, _ = await _criar_deposito_com_saldo(session, tenant_id, unidade_id, produto.id, quantidade=50.0)
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto.id, [a1.id, a2.id], lote_id=lote.id, dose=2.5)

    res = await ManejoSyncService(session, tenant_id).processar_tarefa_campo(tarefa.id)
    assert res.status == "SUCCESS", res.erros
    res_reprocessado = await ManejoSyncService(session, tenant_id).processar_tarefa_campo(tarefa.id)
    assert res_reprocessado.status == "SUCCESS"

    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                EstoqueMovimento.origem_id == tarefa.id,
                EstoqueMovimento.produto_id == produto.id,
            )
        )
    ).scalars().one()
    allocations = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "PECUARIA_VACINACAO",
                CostAllocation.source_id == tarefa.id,
                CostAllocation.inventory_movement_id == movimento.id,
            )
        )
    ).scalars().all()
    await session.refresh(movimento)
    assert float(movimento.quantidade) == pytest.approx(-5.0)
    assert float(movimento.custo_unitario) == pytest.approx(4.0)
    assert float(movimento.custo_total) == pytest.approx(20.0)
    assert allocations == []


async def test_registrar_custo_vacinacao_cria_allocation_quando_contexto_resolvido(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    tarefa = SimpleNamespace(
        id=uuid.uuid4(),
        area_rural_id=uuid.uuid4(),
        dados={"area_id": str(uuid.uuid4())},
        concluida_em=datetime.utcnow(),
    )
    movimento = SimpleNamespace(
        id=uuid.uuid4(),
        custo_total=20.0,
        custo_unitario=4.0,
        quantidade=-5.0,
    )
    service = ManejoSyncService(session, tenant_id)
    fake_pu_id = uuid.uuid4()
    chamado = {}

    async def _fake_resolver(_tarefa):
        return SimpleNamespace(id=fake_pu_id)

    async def _fake_registrar(*args, **kwargs):
        chamado.update(kwargs)
        return SimpleNamespace(**kwargs)

    import pecuaria.services.manejo_sync_service as manejo_module

    monkeypatch.setattr(service, "_resolver_production_unit_vacinacao", _fake_resolver)

    async def _fake_existente(*_args, **_kwargs):
        return False

    monkeypatch.setattr(service, "_custo_vacinacao_existente", _fake_existente)
    monkeypatch.setattr(manejo_module, "registrar_cost_allocation", _fake_registrar)

    allocation = await service._registrar_custo_vacinacao(tarefa, movimento, 2)

    assert allocation is not None
    assert chamado["tenant_id"] == tenant_id
    assert chamado["production_unit_id"] == fake_pu_id
    assert chamado["source"] == "PECUARIA_VACINACAO"
    assert chamado["source_id"] == tarefa.id
    assert chamado["inventory_movement_id"] == movimento.id
    assert chamado["cost_category"] == "SANITARIO"
    assert float(chamado["amount"]) == pytest.approx(20.0)

    async def _fake_existente_true(*_args, **_kwargs):
        return True

    monkeypatch.setattr(service, "_custo_vacinacao_existente", _fake_existente_true)
    chamado.clear()
    allocation_reprocessado = await service._registrar_custo_vacinacao(tarefa, movimento, 2)

    assert allocation_reprocessado is None
    assert chamado == {}


async def test_sync_vacinacao_idempotencia_reprocessamento(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Sync Vacinação 2")
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="202", peso=140.0)
    produto = await _criar_produto_vacina(session, tenant_id, "Vacina Idempotencia")
    _, saldo = await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=10.0)
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto.id, [animal.id], lote_id=lote.id)

    res1 = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res1.status == "SUCCESS", res1.erros
    assert res1.total_processado == 1

    res2 = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res2.status == "SUCCESS"
    assert res2.total_processado == 0
    assert res2.total_ignorados == 1

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert len(eventos) == 1
    movimentos = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                EstoqueMovimento.origem_id == tarefa.id,
            )
        )
    ).scalars().all()
    await session.refresh(saldo)
    assert len(movimentos) == 1
    assert float(movimentos[0].quantidade) == pytest.approx(-2.0)
    assert saldo.quantidade_atual == pytest.approx(8.0)
    allocations = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "PECUARIA_VACINACAO",
                CostAllocation.source_id == tarefa.id,
            )
        )
    ).scalars().all()
    assert allocations == []


async def test_sync_vacinacao_reprocessamento_reconhece_legado_manual(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    sync_service: ManejoSyncService,
):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Legado Vacinação")
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="203A", peso=150.0)
    produto = await _criar_produto_vacina(session, tenant_id, "Vacina Legada")
    deposito, saldo = await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=20.0)
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto.id, [animal.id], lote_id=lote.id)

    legado = EstoqueMovimento(
        tenant_id=tenant_id,
        produto_id=produto.id,
        deposito_id=deposito.id,
        quantidade=-2.0,
        unidade_medida_id=(await session.execute(
            select(UnidadeMedida.id).where(UnidadeMedida.tenant_id.is_(None), UnidadeMedida.codigo == "ML")
        )).scalar_one(),
        tipo_movimento="SAIDA",
        origem="MANUAL",
        origem_id=tarefa.id,
        observacoes=f"PECUARIA_VACINACAO - tarefa {tarefa.id}",
    )
    saldo.quantidade_atual = 18.0
    session.add(legado)
    await session.commit()

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "SUCCESS", res.erros

    movimentos = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem_id == tarefa.id,
                EstoqueMovimento.produto_id == produto.id,
            )
        )
    ).scalars().all()
    await session.refresh(saldo)
    assert len(movimentos) == 1
    assert movimentos[0].origem == "MANUAL"
    assert "PECUARIA_VACINACAO" in (movimentos[0].observacoes or "")
    assert saldo.quantidade_atual == pytest.approx(18.0)


async def test_sync_vacinacao_rollback_total_em_payload_invalido(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Sync Vacinação 3")
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="203", peso=150.0)
    animal_id = animal.id
    produto = await _criar_produto_vacina(session, tenant_id, "Vacina Rollback")
    _, saldo = await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=30.0)
    tarefa = await _criar_tarefa_vacinacao(
        session,
        tenant_id,
        produto.id,
        [animal.id],
        lote_id=lote.id,
        dose=0,
    )

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("dose" in erro.lower() or "validação" in erro.lower() for erro in res.erros)

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    movimentos = (await session.execute(select(EstoqueMovimento).where(EstoqueMovimento.origem_id == tarefa.id))).scalars().all()
    assert len(eventos) == 0
    assert movimentos == []
    animal_db = (await session.execute(select(Animal).where(Animal.id == animal_id))).scalars().first()
    await session.refresh(saldo)
    assert animal_db is not None
    assert animal_db.peso_atual_kg == 150.0
    assert animal_db.data_ultima_pesagem is None
    assert saldo.quantidade_atual == pytest.approx(30.0)


async def test_sync_vacinacao_saldo_insuficiente_faz_rollback_total(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Sync Vacinação 4")
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="204", peso=160.0)
    produto = await _criar_produto_vacina(session, tenant_id, "Vacina Estoque")
    _, saldo = await _criar_deposito_com_saldo(session, tenant_id, unidade_produtiva_id, produto.id, quantidade=1.0)
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto.id, [animal.id], lote_id=lote.id, dose=2.5)

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("saldo" in erro.lower() for erro in res.erros)

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    movimentos = (await session.execute(select(EstoqueMovimento).where(EstoqueMovimento.origem_id == tarefa.id))).scalars().all()
    await session.refresh(animal)
    await session.refresh(saldo)
    assert eventos == []
    assert movimentos == []
    assert animal.peso_atual_kg == 160.0
    assert saldo.quantidade_atual == pytest.approx(1.0)


async def test_sync_vacinacao_produto_de_outro_tenant_bloqueia(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, "Lote Sync Vacinação Tenant")
    animal = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=lote.id, brinc="205", peso=170.0)
    produto_outro_tenant = await _criar_produto_vacina(session, outro_tenant_id, "Vacina Outro Tenant")
    tarefa = await _criar_tarefa_vacinacao(session, tenant_id, produto_outro_tenant.id, [animal.id], lote_id=lote.id)

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("não encontrado neste tenant" in erro for erro in res.erros)

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert eventos == []


async def test_sync_rejeitar_animal_fora_lote(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    lote_certo_id = uuid.uuid4()
    
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, lote_id=None, brinc="009")
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "lote_id": str(lote_certo_id),
        "animais": [{"animal_id": str(a1.id), "peso_kg": 150.0}]
    })
    
    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "ERROR"
    assert any("não pertence ao lote" in e for e in res.erros)


async def test_sync_rollback_parcial(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    # A1 é valido. A2 não existe. Transação inteira deve falhar.
    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="010", peso=100.0)
    fake_id = uuid.uuid4()

    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [
            {"animal_id": str(a1.id), "peso_kg": 150.0},
            {"animal_id": str(fake_id), "peso_kg": 200.0}
        ]
    })
    
    tarefa_id = tarefa.id
    a1_id = a1.id

    res = await sync_service.processar_tarefa_campo(tarefa_id)
    assert res.status == "ERROR"

    # A1 não deve ter sido alterado (buscar de novo devido ao rollback expirar o obj)
    stmt_a1 = select(Animal).where(Animal.id == a1_id)
    a1_db = (await session.execute(stmt_a1)).scalars().first()
    assert a1_db.peso_atual_kg == 100.0
    
    # Eventos zerados
    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa_id)
    evts = (await session.execute(stmt)).scalars().all()
    assert len(evts) == 0


async def test_sync_peso_retroativo(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, sync_service: ManejoSyncService):
    # Animal tem peso no dia 20
    hoje = date.today()
    dia_20 = hoje - timedelta(days=5)
    dia_15 = hoje - timedelta(days=10)

    a1 = await _criar_animal(session, tenant_id, unidade_produtiva_id, brinc="011", peso=180.0, ultima_pesagem=dia_20)

    # Lança pesagem retroativa pro dia 15 (peso 160)
    tarefa = await _criar_tarefa(session, tenant_id, dados={
        "animais": [
            {"animal_id": str(a1.id), "peso_kg": 160.0, "data_evento": dia_15.strftime("%Y-%m-%d")}
        ]
    })

    res = await sync_service.processar_tarefa_campo(tarefa.id)
    assert res.status == "SUCCESS"

    await session.refresh(a1)
    # Peso atual não pode cair para 160, deve ficar em 180! E a data continua dia 20.
    assert a1.peso_atual_kg == 180.0
    assert a1.data_ultima_pesagem == dia_20

    # Evento foi criado com peso 160
    stmt = select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id)
    evt = (await session.execute(stmt)).scalars().first()
    assert evt.peso_kg == 160.0
    assert evt.data_evento == dia_15
