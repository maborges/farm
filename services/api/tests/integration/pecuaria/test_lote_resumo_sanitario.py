from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.cadastros.propriedades.models import AreaRural
from core.cadastros.produtos.models import Produto, TipoProduto
from core.config import settings
from core.measurements.models import UnidadeMedida
from core.models.auth import Usuario
from campo.models import DispositivoCampo, TarefaCampo
from operacional.models.estoque import Deposito, EstoqueMovimento, SaldoEstoque
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from tests.integration.conftest import FAZENDA_ID, TENANT_ID, _gerar_token
from tests.integration.helpers import garantir_assinatura

pytestmark = pytest.mark.asyncio


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    token = _gerar_token(tenant_id, ["CORE", "P1_REBANHO"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")),
    }


def _device_headers(device: DispositivoCampo) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    payload = {
        "type": "device",
        "device_id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "sub": str(device.user_id),
        "user_name": "Operador Smoke Homolog",
        "user_avatar_url": None,
        "fazenda_ids": [str(fid) for fid in device.fazenda_ids],
        "modulos": device.modulos,
        "iat": int(now.timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


async def _garantir_unidade_medida(session: AsyncSession) -> UnidadeMedida:
    unidade = await session.scalar(select(UnidadeMedida).where(UnidadeMedida.codigo == "ML"))
    if unidade:
        return unidade
    unidade = UnidadeMedida(
        id=uuid.uuid4(),
        tenant_id=None,
        codigo="ML",
        nome="Mililitro",
        dimensao="VOLUME",
        codigo_canonico="ML",
        fator_canonico=1,
        sistema=True,
        ativo=True,
        casas_decimais=2,
        eh_canonica=True,
    )
    session.add(unidade)
    await session.commit()
    return unidade


async def _garantir_tenant_com_assinatura(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(tenant_id),
            "nome": f"Tenant {tenant_id.hex[:8]}",
            "documento": tenant_id.hex[:11],
        },
    )
    await garantir_assinatura(session, tenant_id)
    await session.commit()


async def _criar_contexto_base(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    user_id = uuid.uuid4()
    area_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    production_unit_id = uuid.uuid4()
    device_id = uuid.uuid4()

    session.add(
        Usuario(
            id=user_id,
            email=f"resumo-{user_id.hex[:8]}@example.com",
            username=f"resumo_{user_id.hex[:8]}",
            nome_completo="Usuario Resumo",
            senha_hash="hash",
            is_superuser=False,
            ativo=True,
        )
    )
    await session.commit()

    session.add_all(
        [
            AreaRural(
                id=area_id,
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                tipo="PIQUETE",
                nome="Piquete Resumo",
                ativo=True,
            ),
            Safra(
                id=safra_id,
                tenant_id=tenant_id,
                ano_safra="2026/27",
                cultura="BOVINOCULTURA",
                status="PLANEJADA",
            ),
        ]
    )
    await session.commit()

    session.add(
        Cultivo(
            id=cultivo_id,
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultura="BOVINOCULTURA",
            status="PLANEJADO",
            consorciado=False,
        )
    )
    await session.commit()

    session.add(
        ProductionUnit(
            id=production_unit_id,
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultivo_id=cultivo_id,
            area_id=area_id,
            percentual_participacao=100,
            area_ha=10.0,
            status="ATIVA",
        )
    )
    session.add(
        DispositivoCampo(
            id=device_id,
            tenant_id=tenant_id,
            user_id=user_id,
            nome="Tablet Resumo",
            status="ATIVO",
            fazenda_ids=[unidade_produtiva_id],
            modulos=["agricola", "pecuaria"],
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    await session.commit()

    return {
        "area_id": area_id,
        "safra_id": safra_id,
        "cultivo_id": cultivo_id,
        "production_unit_id": production_unit_id,
        "device_id": device_id,
        "user_id": user_id,
    }


async def _criar_lote_animais(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    area_id: uuid.UUID,
    quantidade: int,
    *,
    identificacao: str,
) -> tuple[LoteAnimal, list[Animal]]:
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_id=area_id,
        identificacao=identificacao,
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=quantidade,
        peso_medio_kg=120.0,
        data_formacao=date(2026, 6, 24),
        ativo=True,
    )
    session.add(lote)
    await session.commit()

    animais: list[Animal] = []
    for index in range(quantidade):
        animal = Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            lote_id=lote.id,
            numero_brinco=f"{identificacao[:4]}-{index + 1}",
            especie="BOVINO",
            categoria="BEZERRO",
            sexo="MACHO" if index % 2 == 0 else "FEMEA",
            status="ATIVO",
            data_entrada=date(2026, 6, 24),
            peso_atual_kg=120.0 + index,
        )
        session.add(animal)
        animais.append(animal)
    await session.commit()
    return lote, animais


async def _criar_produto_estoque(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    nome: str,
    *,
    preco_medio: float = 4.0,
    saldo_inicial: float = 100.0,
) -> tuple[Produto, Deposito, SaldoEstoque]:
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=nome,
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        preco_medio=preco_medio,
        ativo=True,
    )
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Deposito {nome}",
        tipo="GERAL",
        ativo=True,
    )
    saldo = SaldoEstoque(
        id=uuid.uuid4(),
        deposito_id=deposito.id,
        produto_id=produto.id,
        quantidade_atual=saldo_inicial,
        quantidade_reservada=0.0,
    )
    session.add_all([produto, deposito, saldo])
    await session.commit()
    await session.refresh(produto)
    await session.refresh(deposito)
    await session.refresh(saldo)
    return produto, deposito, saldo


async def _criar_vacinacao_manual(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lote: LoteAnimal,
    animais: list[Animal],
    produto: Produto,
    deposito: Deposito,
    production_unit_id: uuid.UUID,
    quantidade_animais: int,
    custo_unitario: float,
    data_vacinacao: date,
) -> TarefaCampo:
    dose = 2.5
    quantidade_consumida = dose * quantidade_animais
    custo_total = quantidade_consumida * custo_unitario
    tarefa = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        module="pecuaria",
        type="VACINACAO",
        status="CONCLUIDA",
        status_execucao="CONCLUIDA",
        client_id=str(uuid.uuid4()),
        origem="MANUAL",
        prioridade="NORMAL",
        localizacao_status="INDISPONIVEL",
        unidade_produtiva_id=lote.unidade_produtiva_id,
        area_rural_id=lote.area_id,
        lote_id=lote.id,
        dados={
            "lote_id": str(lote.id),
            "area_id": str(lote.area_id),
            "produto_id": str(produto.id),
            "dose": dose,
            "unidade_medida": "ML",
            "via_aplicacao": "SUBCUTANEA",
            "animais_ids": [str(animal.id) for animal in animais[:quantidade_animais]],
        },
        concluida_em=datetime.combine(data_vacinacao, datetime.min.time()),
        client_created_at=datetime.combine(data_vacinacao, datetime.min.time()),
        client_updated_at=datetime.combine(data_vacinacao, datetime.min.time()),
    )
    session.add(tarefa)
    await session.commit()

    eventos = []
    for animal in animais[:quantidade_animais]:
        eventos.append(
            EventoAnimal(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                animal_id=animal.id,
                tarefa_campo_id=tarefa.id,
                tipo="VACINACAO",
                data_evento=data_vacinacao,
                produto_id=produto.id,
                observacoes="Resumo sanitário",
                dados_extras={"dose": dose, "unidade_medida": "ML", "via_aplicacao": "SUBCUTANEA"},
            )
        )
    session.add_all(eventos)
    await session.commit()

    unidade_medida = await _garantir_unidade_medida(session)
    movimento = EstoqueMovimento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        data_movimento=datetime.combine(data_vacinacao, datetime.min.time(), tzinfo=timezone.utc),
        tipo_movimento="SAIDA",
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        quantidade=-quantidade_consumida,
        unidade_medida_id=unidade_medida.id,
        custo_unitario=custo_unitario,
        custo_total=custo_total,
        origem="PECUARIA_VACINACAO",
        origem_id=tarefa.id,
        production_unit_id=production_unit_id,
        observacoes=f"PECUARIA_VACINACAO - tarefa {tarefa.id}",
    )
    session.add(movimento)
    await session.commit()

    session.add(
        CostAllocation(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            production_unit_id=production_unit_id,
            source="PECUARIA_VACINACAO",
            source_id=tarefa.id,
            inventory_movement_id=movimento.id,
            cost_category="SANITARIO",
            amount=custo_total,
            currency="BRL",
            allocation_date=data_vacinacao,
            allocation_method="DIRECT",
            allocation_basis=float(quantidade_animais),
        )
    )
    await session.commit()
    return tarefa


async def _obter_resumo(client: AsyncClient, lote_id: uuid.UUID, headers: dict[str, str]):
    response = await client.get(f"/api/v1/pecuaria/lotes/{lote_id}/resumo-sanitario", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_resumo_sem_vacinacao_retorna_zero(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, _ = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        2,
        identificacao="LoteVazio",
    )

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["lote_id"] == str(lote.id)
    assert body["quantidade_animais"] == 2
    assert body["eventos_sanitarios"] == 0
    assert body["vacinacoes"] == 0
    assert body["custo_sanitario_total"] == 0
    assert body["custo_sanitario_por_animal"] == 0
    assert body["ultima_vacinacao"] is None
    assert body["produtos_utilizados"] == []


async def test_resumo_com_vacinacao_e_custo_agrega_total(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, animais = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        2,
        identificacao="LoteResumo",
    )
    produto, deposito, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina Resumo", preco_medio=4.0)
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais,
        produto=produto,
        deposito=deposito,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=2,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 24),
    )

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["eventos_sanitarios"] == 2
    assert body["vacinacoes"] == 1
    assert body["custo_sanitario_total"] == 20.0
    assert body["custo_sanitario_por_animal"] == 10.0
    assert body["ultima_vacinacao"] == "2026-06-24"
    assert body["produto_mais_usado"]["produto_id"] == str(produto.id)
    assert body["produto_mais_usado"]["quantidade_eventos"] == 2
    assert body["produtos_utilizados"][0]["produto_id"] == str(produto.id)
    assert body["produtos_utilizados"][0]["quantidade_eventos"] == 2
    assert body["produtos_utilizados"][0]["custo_total"] == 20.0


async def test_resumo_custo_por_animal_zero_quando_lote_sem_animais(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        unidade_produtiva_id=FAZENDA_ID,
        area_id=contexto["area_id"],
        identificacao="Lote Sem Animais",
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 24),
        ativo=True,
    )
    session.add(lote)
    await session.commit()

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 0
    assert body["custo_sanitario_por_animal"] == 0


async def test_resumo_bloqueia_lote_de_outro_tenant(
    client: AsyncClient,
    session: AsyncSession,
    outro_tenant_id: uuid.UUID,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, _ = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        1,
        identificacao="Lote A",
    )

    await _garantir_tenant_com_assinatura(session, outro_tenant_id)
    response = await client.get(f"/api/v1/pecuaria/lotes/{lote.id}/resumo-sanitario", headers=_headers(outro_tenant_id))

    assert response.status_code == 404


async def test_resumo_ignora_pesagem_no_custo_sanitario(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, animais = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        1,
        identificacao="Lote Pesagem",
    )
    produto, deposito, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina Pesagem", preco_medio=4.0)
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais,
        produto=produto,
        deposito=deposito,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=1,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 24),
    )
    pesagem = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        user_id=uuid.uuid4(),
        module="pecuaria",
        type="PESAGEM",
        status="CONCLUIDA",
        status_execucao="CONCLUIDA",
        client_id=str(uuid.uuid4()),
        origem="MANUAL",
        prioridade="NORMAL",
        localizacao_status="INDISPONIVEL",
        unidade_produtiva_id=FAZENDA_ID,
        area_rural_id=contexto["area_id"],
        lote_id=lote.id,
        dados={},
        concluida_em=datetime(2026, 6, 24),
        client_created_at=datetime(2026, 6, 24),
        client_updated_at=datetime(2026, 6, 24),
    )
    session.add(pesagem)
    await session.commit()

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["eventos_sanitarios"] == 1
    assert body["custo_sanitario_total"] == 10.0


async def test_resumo_agrupar_produtos_por_vacinacao(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, animais = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        3,
        identificacao="Lote Produtos",
    )
    produto_a, deposito_a, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina A", preco_medio=4.0)
    produto_b, deposito_b, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina B", preco_medio=4.0)
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais[:2],
        produto=produto_a,
        deposito=deposito_a,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=2,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 23),
    )
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais[2:],
        produto=produto_b,
        deposito=deposito_b,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=1,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 24),
    )

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 3
    assert body["eventos_sanitarios"] == 3
    assert body["vacinacoes"] == 2
    produtos = {item["produto_id"]: item for item in body["produtos_utilizados"]}
    assert produtos[str(produto_a.id)]["quantidade_eventos"] == 2
    assert produtos[str(produto_a.id)]["custo_total"] == 20.0
    assert produtos[str(produto_b.id)]["quantidade_eventos"] == 1
    assert produtos[str(produto_b.id)]["custo_total"] == 10.0
    assert body["produto_mais_usado"]["produto_id"] == str(produto_a.id)
    assert body["produto_mais_usado"]["quantidade_eventos"] == 2
    assert body["ultima_vacinacao"] == "2026-06-24"


async def test_resumo_idempotencia_nao_inflaciona(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, animais = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        2,
        identificacao="Lote Idem",
    )
    produto, _, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina Idem", preco_medio=4.0)

    device = await session.scalar(select(DispositivoCampo).where(DispositivoCampo.id == contexto["device_id"]))
    assert device is not None
    headers = _device_headers(device)
    payload = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": str(uuid.uuid4()),
                "operation": "CREATE",
                "entity_type": "task",
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": datetime.utcnow().isoformat(),
                "payload": {
                    "module": "pecuaria",
                    "type": "VACINACAO_LOTE",
                    "status": "CONCLUIDA",
                    "lote_id": str(lote.id),
                    "talhao_id": str(contexto["area_id"]),
                    "dados": {
                        "lote_id": str(lote.id),
                        "area_id": str(contexto["area_id"]),
                        "produto_id": str(produto.id),
                        "dose": 2.5,
                        "unidade_medida": "ML",
                        "via_aplicacao": "SUBCUTANEA",
                        "animais_ids": [str(animal.id) for animal in animais],
                    },
                    "fazenda_id": str(FAZENDA_ID),
                },
            }
        ],
    }

    response1 = await client.post("/api/v1/sync/push", json=payload, headers=headers)
    assert response1.status_code == 200, response1.text
    server_id = uuid.UUID(response1.json()["results"][0]["server_id"])
    payload_update = {
        "device_id": str(device.id),
        "items": [
            {
                "local_id": str(uuid.uuid4()),
                "operation": "UPDATE",
                "entity_type": "task",
                "server_id": str(server_id),
                "client_created_at": datetime.utcnow().isoformat(),
                "client_updated_at": (datetime.utcnow() + timedelta(seconds=5)).isoformat(),
                "payload": {
                    "status": "CONCLUIDA",
                    "dados": {
                        "lote_id": str(lote.id),
                        "area_id": str(contexto["area_id"]),
                        "produto_id": str(produto.id),
                        "dose": 2.5,
                        "unidade_medida": "ML",
                        "via_aplicacao": "SUBCUTANEA",
                        "animais_ids": [str(animal.id) for animal in animais],
                    },
                },
            }
        ],
    }
    response2 = await client.post("/api/v1/sync/push", json=payload_update, headers=headers)
    assert response2.status_code == 200, response2.text

    body = await _obter_resumo(client, lote.id, _headers(TENANT_ID))
    assert body["eventos_sanitarios"] == 2
    assert body["vacinacoes"] == 1
    assert body["custo_sanitario_total"] == 20.0


async def test_resumo_indica_produto_mais_usado(
    client: AsyncClient,
    session: AsyncSession,
    headers_admin: dict[str, str],
) -> None:
    contexto = await _criar_contexto_base(session, TENANT_ID, FAZENDA_ID)
    lote, animais = await _criar_lote_animais(
        session,
        TENANT_ID,
        FAZENDA_ID,
        contexto["area_id"],
        3,
        identificacao="Lote Ranking",
    )
    produto_a, deposito_a, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina A", preco_medio=4.0)
    produto_b, deposito_b, _ = await _criar_produto_estoque(session, TENANT_ID, FAZENDA_ID, "Vacina B", preco_medio=4.0)
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais[:2],
        produto=produto_a,
        deposito=deposito_a,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=2,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 23),
    )
    await _criar_vacinacao_manual(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        animais=animais[2:],
        produto=produto_b,
        deposito=deposito_b,
        production_unit_id=contexto["production_unit_id"],
        quantidade_animais=1,
        custo_unitario=4.0,
        data_vacinacao=date(2026, 6, 24),
    )

    body = await _obter_resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 3
    assert body["eventos_sanitarios"] == 3
    assert body["vacinacoes"] == 2
    assert body["produto_mais_usado"]["produto_id"] == str(produto_a.id)
    assert body["produto_mais_usado"]["quantidade_eventos"] == 2
    assert body["ultima_vacinacao"] == "2026-06-24"
