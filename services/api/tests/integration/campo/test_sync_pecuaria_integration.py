import pytest
import uuid
from datetime import datetime, timedelta, date, timezone
from jose import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from core.config import settings
from core.cadastros.produtos.models import Produto, TipoProduto
from core.cadastros.propriedades.models import AreaRural
from core.models.auth import Usuario
from core.measurements.models import UnidadeMedida
from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from campo.models import DispositivoCampo, TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal
from pecuaria.services.manejo_sync_service import ManejoSyncService
from operacional.models.estoque import Deposito, EstoqueMovimento, SaldoEstoque
from core.database import async_session_maker

pytestmark = pytest.mark.asyncio

async def _criar_tenant_user_device_animal(session: AsyncSession, tenant_id: uuid.UUID):
    # User
    user = Usuario(
        id=uuid.uuid4(),
        email=f"device-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"device_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.flush()

    # Unidade Produtiva
    from core.models.unidade_produtiva import UnidadeProdutiva
    unidade_produtiva_id = uuid.uuid4()
    unidade = UnidadeProdutiva(
        id=unidade_produtiva_id,
        tenant_id=tenant_id,
        nome="Fazenda Sync Test",
        ativo=True
    )
    session.add(unidade)
    await session.flush()

    # Device
    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Sync",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola", "pecuaria"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)

    # Animal
    animal = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        numero_brinco="SYNC123",
        data_entrada=date.today(),
        peso_atual_kg=100.0,
    )
    session.add(animal)
    await session.commit()
    
    await session.refresh(device)
    await session.refresh(animal)

    return user, device, animal, unidade_produtiva_id


async def _criar_deposito_com_saldo(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    produto_id: uuid.UUID,
    *,
    quantidade: float = 100.0,
):
    await _garantir_unidade_medida(session, "ML", "Mililitro")
    await _garantir_unidade_medida(session, "UN", "Unidade")
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Depósito Vacinas Integração",
        tipo="GERAL",
        ativo=True,
    )
    saldo = SaldoEstoque(
        id=uuid.uuid4(),
        deposito_id=deposito.id,
        produto_id=produto_id,
        quantidade_atual=quantidade,
        quantidade_reservada=0.0,
    )
    session.add_all([deposito, saldo])
    await session.commit()
    await session.refresh(deposito)
    await session.refresh(saldo)
    return deposito, saldo


async def _criar_area_rural_piquete(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> AreaRural:
    area = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="PIQUETE",
        nome="Piquete Integração",
        ativo=True,
    )
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area


async def _criar_safra(session: AsyncSession, tenant_id: uuid.UUID) -> Safra:
    safra = Safra(
        tenant_id=tenant_id,
        ano_safra=f"{date.today().year}/{date.today().year + 1}",
        status="PLANEJADA",
    )
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    return safra


async def _criar_cultivo(session: AsyncSession, tenant_id: uuid.UUID, safra_id: uuid.UUID) -> Cultivo:
    cultivo = Cultivo(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultura="BOVINOCULTURA",
        status="PLANEJADO",
        consorciado=False,
    )
    session.add(cultivo)
    await session.commit()
    await session.refresh(cultivo)
    return cultivo


async def _criar_production_unit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    cultivo_id: uuid.UUID,
    area_id: uuid.UUID,
) -> ProductionUnit:
    await _garantir_status_consorcio_area_constraint(session)
    pu = ProductionUnit(
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo_id,
        area_id=area_id,
        percentual_participacao=100,
        area_ha=10.0,
        status="ATIVA",
    )
    session.add(pu)
    await session.commit()
    await session.refresh(pu)
    return pu


async def _garantir_status_consorcio_area_constraint(session: AsyncSession) -> None:
    existente = (
        await session.execute(
            text(
                "SELECT 1 FROM pg_constraint WHERE conname = 'uq_status_consorcio_area_safra_area' LIMIT 1"
            )
        )
    ).scalar_one_or_none()
    if existente:
        return
    await session.execute(
        text(
            "ALTER TABLE status_consorcio_area "
            "ADD CONSTRAINT uq_status_consorcio_area_safra_area UNIQUE (tenant_id, safra_id, area_id)"
        )
    )
    await session.commit()


async def _criar_lote(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    area_id: uuid.UUID,
    identificacao: str,
) -> object:
    from pecuaria.animal.models import LoteAnimal

    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_id=area_id,
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


async def _garantir_unidade_medida(session: AsyncSession, codigo: str, nome: str):
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
        id=uuid.uuid4(),
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

def _gerar_device_token(device: DispositivoCampo) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "type": "device",
        "device_id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "sub": str(device.user_id),
        "user_name": "Operador Sync",
        "user_avatar_url": None,
        "fazenda_ids": [str(fid) for fid in device.fazenda_ids],
        "modulos": device.modulos,
        "iat": int(now.timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def test_sync_push_aciona_manejo_sync_service_corretamente(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    client_id = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "PESAGEM",
                    "status": "CONCLUIDA",
                    "dados": {
                        "animais": [
                            {"animal_id": str(animal.id), "peso_kg": 250.5}
                        ]
                    },
                    "fazenda_id": str(unidade_produtiva_id)
                }
            }
        ]
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "CREATED"
    server_id = data["results"][0]["server_id"]

    # Verify that the task was created
    tarefa_db = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id)))).scalar_one()
    assert tarefa_db.status_execucao == "CONCLUIDA"
    assert tarefa_db.module == "pecuaria"
    assert tarefa_db.type == "PESAGEM"

    # Verify that ManejoSyncService was triggered and updated the animal
    await session.refresh(animal)
    assert animal.peso_atual_kg == 250.5

    # Verify that the EventoAnimal was created
    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.animal_id == animal.id))).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].tipo == "PESAGEM"
    assert eventos[0].tarefa_campo_id == tarefa_db.id


async def test_sync_push_aciona_manejo_sync_service_para_alias_pesagem(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    client_id = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "PESAGEM_ANIMAL",
                    "status": "CONCLUIDA",
                    "dados": {
                        "animais": [
                            {"animal_id": str(animal.id), "peso_kg": 275.0}
                        ]
                    },
                    "fazenda_id": str(unidade_produtiva_id),
                },
            }
        ],
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    server_id = response.json()["results"][0]["server_id"]

    tarefa_db = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id)))).scalars().one()
    assert tarefa_db.type == "PESAGEM"

    await session.refresh(animal)
    assert animal.peso_atual_kg == 275.0

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa_db.id))).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].tipo == "PESAGEM"


async def test_sync_push_aciona_manejo_sync_service_para_alias_vacinacao(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)

    lote = uuid.uuid4()
    from pecuaria.animal.models import LoteAnimal

    lote_db = LoteAnimal(
        id=lote,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao="Lote Alias Vacinação",
        especie="BOVINO",
        categoria="BEZERRO",
        quantidade_cabecas=1,
        peso_medio_kg=100.0,
        data_formacao=date.today(),
        ativo=True,
    )
    produto = Produto(
        tenant_id=tenant_id,
        nome="Vacina Alias",
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        ativo=True,
    )
    animal.lote_id = lote_db.id
    session.add_all([lote_db, produto])
    await session.commit()
    await session.refresh(device)
    await session.refresh(animal)
    await session.refresh(produto)
    deposito, saldo = await _criar_deposito_com_saldo(
        session,
        tenant_id,
        unidade_produtiva_id,
        produto.id,
        quantidade=10.0,
    )

    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    client_id = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "VACINACAO_LOTE",
                    "status": "CONCLUIDA",
                    "dados": {
                        "lote_id": str(lote_db.id),
                        "produto_id": str(produto.id),
                        "dose": 2.5,
                        "unidade_medida": "ML",
                        "via_aplicacao": "SUBCUTANEA",
                        "animais_ids": [str(animal.id)],
                    },
                    "fazenda_id": str(unidade_produtiva_id),
                },
            }
        ],
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    server_id = response.json()["results"][0]["server_id"]

    tarefa_db = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id)))).scalars().one()
    assert tarefa_db.type == "VACINACAO"

    await session.refresh(animal)
    assert animal.peso_atual_kg == 100.0

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa_db.id))).scalars().all()
    assert len(eventos) == 1
    assert eventos[0].tipo == "VACINACAO"
    assert eventos[0].produto_id == produto.id

    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                EstoqueMovimento.origem_id == tarefa_db.id,
            )
        )
    ).scalars().one()
    await session.refresh(saldo)
    assert movimento.tipo_movimento == "SAIDA"
    assert float(movimento.quantidade) == pytest.approx(-2.5)
    assert movimento.produto_id == produto.id
    assert movimento.deposito_id == deposito.id
    assert deposito.unidade_produtiva_id == unidade_produtiva_id
    assert "PECUARIA_VACINACAO" in (movimento.observacoes or "")
    assert saldo.quantidade_atual == pytest.approx(7.5)


async def test_sync_push_vacinacao_cria_cost_allocation_com_production_unit_real(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID,
):
    user, device, animal_1, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    area = await _criar_area_rural_piquete(session, tenant_id, unidade_produtiva_id)
    safra = await _criar_safra(session, tenant_id)
    cultivo = await _criar_cultivo(session, tenant_id, safra.id)
    production_unit = await _criar_production_unit(session, tenant_id, safra.id, cultivo.id, area.id)
    lote = await _criar_lote(session, tenant_id, unidade_produtiva_id, area.id, "Lote Vacc Cost")

    animal_2 = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        lote_id=lote.id,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="FEMEA",
        status="ATIVO",
        numero_brinco="SYNC124",
        data_entrada=date.today(),
        peso_atual_kg=105.0,
    )
    animal_1.lote_id = lote.id
    session.add(animal_2)
    await session.commit()
    await session.refresh(animal_1)
    await session.refresh(animal_2)

    produto = Produto(
        tenant_id=tenant_id,
        nome="Vacina Cost Allocation",
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        preco_medio=4.0,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    deposito, saldo = await _criar_deposito_com_saldo(
        session,
        tenant_id,
        unidade_produtiva_id,
        produto.id,
        quantidade=50.0,
    )

    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}
    client_id = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "VACINACAO",
                    "status": "CONCLUIDA",
                    "lote_id": str(lote.id),
                    "talhao_id": str(area.id),
                    "dados": {
                        "lote_id": str(lote.id),
                        "area_id": str(area.id),
                        "produto_id": str(produto.id),
                        "dose": 2.5,
                        "unidade_medida": "ML",
                        "via_aplicacao": "SUBCUTANEA",
                        "animais_ids": [str(animal_1.id), str(animal_2.id)],
                    },
                    "fazenda_id": str(unidade_produtiva_id),
                },
            }
        ],
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    server_id = response.json()["results"][0]["server_id"]

    tarefa_db = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id)))).scalars().one()
    assert tarefa_db.type == "VACINACAO"
    assert tarefa_db.status_execucao == "CONCLUIDA"
    assert tarefa_db.area_rural_id == area.id
    assert tarefa_db.lote_id == lote.id

    resultado_materializacao = await ManejoSyncService(session, tenant_id).processar_tarefa_campo(tarefa_db.id)
    assert resultado_materializacao.status == "SUCCESS", resultado_materializacao.erros
    resultado_reprocesso = await ManejoSyncService(session, tenant_id).processar_tarefa_campo(tarefa_db.id)
    assert resultado_reprocesso.status == "SUCCESS"

    eventos = (
        await session.execute(
            select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa_db.id)
        )
    ).scalars().all()
    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                EstoqueMovimento.origem_id == tarefa_db.id,
                EstoqueMovimento.produto_id == produto.id,
            )
        )
    ).scalars().one()
    allocation = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.source == "PECUARIA_VACINACAO",
                CostAllocation.source_id == tarefa_db.id,
                CostAllocation.inventory_movement_id == movimento.id,
            )
        )
    ).scalars().one()

    await session.refresh(saldo)
    assert len(eventos) == 2
    assert {evt.animal_id for evt in eventos} == {animal_1.id, animal_2.id}
    assert {evt.tipo for evt in eventos} == {"VACINACAO"}
    assert {evt.produto_id for evt in eventos} == {produto.id}
    assert movimento.tipo_movimento == "SAIDA"
    assert movimento.production_unit_id == production_unit.id
    assert movimento.tenant_id == tenant_id
    assert float(movimento.quantidade) == pytest.approx(-5.0)
    assert float(movimento.custo_unitario) == pytest.approx(4.0)
    assert float(movimento.custo_total) == pytest.approx(20.0)
    assert movimento.deposito_id == deposito.id
    assert movimento.origem == "PECUARIA_VACINACAO"
    assert movimento.origem_id == tarefa_db.id
    assert allocation.production_unit_id == production_unit.id
    assert allocation.tenant_id == tenant_id
    assert allocation.source == "PECUARIA_VACINACAO"
    assert allocation.source_id == tarefa_db.id
    assert allocation.inventory_movement_id == movimento.id
    assert allocation.cost_category == "SANITARIO"
    assert float(allocation.amount) == pytest.approx(20.0)
    assert float(allocation.allocation_basis) == pytest.approx(2.0)


async def test_sync_push_ignora_tarefas_agricolas(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    client_id = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "agricola",
                    "type": "APLICACAO_DEFENSIVO",
                    "status": "CONCLUIDA",
                    "dados": {},
                    "fazenda_id": str(unidade_produtiva_id)
                }
            }
        ]
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "CREATED"
    server_id = data["results"][0]["server_id"]

    # Verify that the task was created
    tarefa_db = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id)))).scalar_one()
    assert tarefa_db.status_execucao == "CONCLUIDA"
    assert tarefa_db.module == "agricola"

    # No evento pecuário
    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa_db.id))).scalars().all()
    assert len(eventos) == 0


async def test_sync_push_ignora_tarefas_nao_concluidas(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate sending a task that is "PENDENTE"
    client_id = str(uuid.uuid4())
    
    # ACTUALLY, if operation is CREATE, sync service forces task.status_execucao = "CONCLUIDA"! 
    # Let's test with UPDATE
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=device.id,
        user_id=user.id,
        client_id=client_id,
        origem="MANUAL",
        status_execucao="EM_EXECUCAO",
        type="PESAGEM",
        module="pecuaria",
        status="PENDENTE",
        dados={},
        unidade_produtiva_id=unidade_produtiva_id,
        localizacao_status="INDISPONIVEL",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    payload_sync_update = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id,
                "server_id": str(task.id),
                "operation": "UPDATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": (datetime.utcnow() + timedelta(seconds=1)).isoformat(),
                "payload": {
                    "status_execucao": "EM_EXECUCAO", # Not CONCLUIDA
                    "dados": {
                        "animais": [
                            {"animal_id": str(animal.id), "peso_kg": 300.0}
                        ]
                    }
                }
            }
        ]
    }
    
    response = await client.post("/api/v1/sync/push", json=payload_sync_update, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["status"] == "UPDATED"

    # Verify that the task was updated but ManejoSyncService was NOT triggered
    await session.refresh(task)
    assert task.status_execucao == "EM_EXECUCAO"

    await session.refresh(animal)
    assert animal.peso_atual_kg == 100.0 # Did not change

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == task.id))).scalars().all()
    assert len(eventos) == 0


async def test_sync_push_erro_pecuaria_nao_quebra_sincronizacao(
    client: AsyncClient,
    session: AsyncSession,
    tenant_id: uuid.UUID
):
    user, device, animal, unidade_produtiva_id = await _criar_tenant_user_device_animal(session, tenant_id)
    token = _gerar_device_token(device)
    headers = {"Authorization": f"Bearer {token}"}

    client_id1 = str(uuid.uuid4())
    client_id2 = str(uuid.uuid4())
    payload_sync = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": client_id1,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "PESAGEM",
                    "status": "CONCLUIDA",
                    "dados": {
                        "animais": [
                            {"animal_id": str(uuid.uuid4()), "peso_kg": 250.5} # Animal inexistent, will crash ManejoSyncService
                        ]
                    },
                    "fazenda_id": str(unidade_produtiva_id)
                }
            },
            {
                "local_id": client_id2,
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "agricola",
                    "type": "REGISTRO_CHUVA",
                    "status": "CONCLUIDA",
                    "dados": {},
                    "fazenda_id": str(unidade_produtiva_id)
                }
            }
        ]
    }

    response = await client.post("/api/v1/sync/push", json=payload_sync, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["status"] == "CREATED"
    assert data["results"][1]["status"] == "CREATED"

    # Both tasks were synced, but the first one failed silently during ManejoSyncService processing.
    server_id_1 = data["results"][0]["server_id"]
    server_id_2 = data["results"][1]["server_id"]

    tarefa_db_1 = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id_1)))).scalar_one()
    assert tarefa_db_1.status_execucao == "CONCLUIDA"

    tarefa_db_2 = (await session.execute(select(TarefaCampo).where(TarefaCampo.id == uuid.UUID(server_id_2)))).scalar_one()
    assert tarefa_db_2.status_execucao == "CONCLUIDA"
