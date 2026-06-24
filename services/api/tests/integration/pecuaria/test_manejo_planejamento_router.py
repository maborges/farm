import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.cadastros.produtos.models import Produto, TipoProduto
from core.cadastros.pessoas.models import Pessoa
from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from tests.integration.conftest import _gerar_token

pytestmark = pytest.mark.asyncio


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    token = _gerar_token(tenant_id, ["CORE", "P1_REBANHO", "A2_CAMPO"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(uuid.uuid4()),
    }


async def _criar_lote(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    identificacao: str,
) -> LoteAnimal:
    lote = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao=identificacao,
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 1),
        ativo=True,
    )
    session.add(lote)
    await session.commit()
    await session.refresh(lote)
    return lote


async def _criar_area_piquete(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    nome: str,
) -> AreaRural:
    area = AreaRural(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo=TipoArea.PIQUETE.value,
        nome=nome,
        ativo=True,
    )
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area


async def _criar_animal(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    lote_id: uuid.UUID,
    numero_brinco: str,
    status: str = "ATIVO",
) -> Animal:
    animal = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        lote_id=lote_id,
        numero_brinco=numero_brinco,
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status=status,
        data_entrada=date(2026, 6, 1),
        peso_atual_kg=120.0,
    )
    session.add(animal)
    await session.commit()
    await session.refresh(animal)
    return animal


async def _criar_operador(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> Pessoa:
    operador = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        ativo=True,
    )
    session.add(operador)
    await session.commit()
    await session.refresh(operador)
    return operador


async def _criar_produto_vacina(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> Produto:
    produto = Produto(
        tenant_id=tenant_id,
        nome=nome,
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def test_planejar_pesagem_para_todos_os_animais(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    area = await _criar_area_piquete(session, tenant_requisicao, unidade_produtiva_id, "Piquete 1")
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Pesagem 1")
    lote.area_id = area.id
    session.add(lote)
    await session.commit()
    await session.refresh(lote)
    animais = [
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "1001"),
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "1002"),
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "1003"),
    ]

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "PESAGEM",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-10",
            "observacoes": "Pesagem de desmame",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["tipo"] == "PESAGEM"
    assert body["origem"] == "PROGRAMADA"
    assert body["status"] == "PENDENTE"
    assert body["quantidade_animais"] == 3
    assert len(body["animais"]) == 3
    assert body["data_programada"] == "2026-07-10"
    assert body["lote"]["id"] == str(lote.id)
    assert body["lote"]["identificacao"] == "Lote Pesagem 1"
    assert body["area_id"] == str(area.id)

    tarefa = (await session.execute(select(TarefaCampo).where(TarefaCampo.lote_id == lote.id))).scalars().one()
    assert tarefa.module == "pecuaria"
    assert tarefa.type == "PESAGEM"
    assert tarefa.origem == "PROGRAMADA"
    assert tarefa.status_execucao == "PENDENTE"
    assert tarefa.data_programada == date(2026, 7, 10)
    assert tarefa.dados["lote_id"] == str(lote.id)
    assert tarefa.dados["area_id"] == str(area.id)
    assert tarefa.dados["data_evento"] == "2026-07-10T00:00:00Z"
    assert tarefa.dados["animais"][0]["peso_kg"] is None
    assert tarefa.area_rural_id == area.id

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert eventos == []
    await session.refresh(animais[0])
    assert animais[0].peso_atual_kg == 120.0


async def test_planejar_pesagem_para_subconjunto_de_animais(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Pesagem 2")
    animal_1 = await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "2001")
    animal_2 = await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "2002")
    await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "2003")
    operador = await _criar_operador(session, tenant_requisicao, "Operador Pesagem")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "PESAGEM",
            "lote_id": str(lote.id),
            "animais_ids": [str(animal_1.id), str(animal_2.id)],
            "data_programada": "2026-07-11",
            "operador_id": str(operador.id),
            "observacoes": "Pesagem seletiva",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quantidade_animais"] == 2
    assert {item["animal_id"] for item in body["animais"]} == {str(animal_1.id), str(animal_2.id)}
    assert body["operador"]["id"] == str(operador.id)
    assert body["operador"]["nome_exibicao"] == "Operador Pesagem"

    tarefa = (await session.execute(select(TarefaCampo).where(TarefaCampo.lote_id == lote.id))).scalars().first()
    assert tarefa is not None
    assert tarefa.operador_id == operador.id
    assert tarefa.dados["observacoes"] == "Pesagem seletiva"


async def test_bloquear_tipo_diferente_de_pesagem(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Regras")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "TRANSFERENCIA",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-12",
        },
    )

    assert response.status_code == 422


async def test_planejar_vacinacao_para_todos_os_animais(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    area = await _criar_area_piquete(session, tenant_requisicao, unidade_produtiva_id, "Piquete Vacinação")
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Vacinação 1")
    lote.area_id = area.id
    session.add(lote)
    await session.commit()
    await session.refresh(lote)
    animais = [
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "6001"),
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "6002"),
    ]
    produto = await _criar_produto_vacina(session, tenant_requisicao, "Vacina Clostridiose")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-16",
            "produto_id": str(produto.id),
            "dose": 2.0,
            "unidade_medida": "ML",
            "via_aplicacao": "SUBCUTANEA",
            "observacoes": "Vacinação coletiva",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["tipo"] == "VACINACAO"
    assert body["quantidade_animais"] == 2
    assert body["area_id"] == str(area.id)
    assert len(body["animais"]) == 2

    tarefa = (await session.execute(select(TarefaCampo).where(TarefaCampo.lote_id == lote.id, TarefaCampo.type == "VACINACAO"))).scalars().one()
    assert tarefa.module == "pecuaria"
    assert tarefa.type == "VACINACAO"
    assert tarefa.dados["tipo"] == "VACINACAO"
    assert tarefa.dados["produto_id"] == str(produto.id)
    assert tarefa.dados["dose"] == 2.0
    assert tarefa.dados["unidade_medida"] == "ML"
    assert tarefa.dados["via_aplicacao"] == "SUBCUTANEA"
    assert tarefa.dados["animais_ids"] == [str(animal.id) for animal in animais]

    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert eventos == []


async def test_planejar_vacinacao_para_subconjunto_de_animais(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Vacinação 2")
    animal_1 = await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "6101")
    animal_2 = await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "6102")
    await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "6103")
    produto = await _criar_produto_vacina(session, tenant_requisicao, "Vacina Raiva")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "animais_ids": [str(animal_1.id), str(animal_2.id)],
            "data_programada": "2026-07-17",
            "produto_id": str(produto.id),
            "dose": 1.5,
            "unidade_medida": "ML",
            "via_aplicacao": "INTRAMUSCULAR",
            "observacoes": "Subconjunto",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quantidade_animais"] == 2
    assert {item["animal_id"] for item in body["animais"]} == {str(animal_1.id), str(animal_2.id)}


async def test_bloquear_dose_zero_ou_negativa(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Dose Invalida")
    produto = await _criar_produto_vacina(session, tenant_requisicao, "Vacina Dose")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-18",
            "produto_id": str(produto.id),
            "dose": 0,
            "unidade_medida": "ML",
        },
    )

    assert response.status_code == 422


async def test_bloquear_animal_fora_do_lote(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote_a = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote A")
    lote_b = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote B")
    animal = await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote_b.id, "3001")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote_a.id),
            "animais_ids": [str(animal.id)],
            "data_programada": "2026-07-13",
            "produto_id": str((await _criar_produto_vacina(session, tenant_requisicao, "Vacina Lote Errado")).id),
            "dose": 1.0,
            "unidade_medida": "ML",
        },
    )

    assert response.status_code == 400
    assert "não pertence ao lote" in response.json()["detail"]


async def test_bloquear_lote_de_outro_tenant(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    outro_tenant_id: uuid.UUID,
) -> None:
    outro_unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(outro_unidade_id), "tenant_id": str(outro_tenant_id), "nome": "Fazenda Outro Tenant"},
    )
    await session.commit()
    lote = await _criar_lote(session, outro_tenant_id, outro_unidade_id, "Lote Externo")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-14",
            "produto_id": str(uuid.uuid4()),
            "dose": 1.0,
            "unidade_medida": "ML",
        },
    )

    assert response.status_code in {400, 404}
    assert "não encontrado" in response.json()["detail"]


async def test_bloquear_area_incompativel_do_lote(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    area = AreaRural(
        tenant_id=tenant_requisicao,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo=TipoArea.AREA_OPERACIONAL.value,
        nome="Área Operacional Teste",
        ativo=True,
    )
    session.add(area)
    await session.commit()
    await session.refresh(area)

    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Área Incompatível")
    lote.area_id = area.id
    session.add(lote)
    await session.commit()

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-15",
            "produto_id": str((await _criar_produto_vacina(session, tenant_requisicao, "Vacina Área Errada")).id),
            "dose": 1.0,
            "unidade_medida": "ML",
        },
    )

    assert response.status_code == 400
    assert "PIQUETE" in response.json()["detail"]


async def test_bloquear_produto_de_outro_tenant(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    outro_tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Produto Externo")
    produto_externo = await _criar_produto_vacina(session, outro_tenant_id, "Vacina Externa")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-19",
            "produto_id": str(produto_externo.id),
            "dose": 1.0,
            "unidade_medida": "ML",
        },
    )

    assert response.status_code in {400, 404}


async def test_listar_planejamentos_paginados(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Paginação")
    for index in range(3):
        await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, f"40{index + 1}")

    for index, data_programada in enumerate(("2026-07-20", "2026-07-21", "2026-07-22")):
        await client.post(
            "/api/v1/pecuaria/manejos/planejar",
            headers=headers_admin,
            json={
                "tipo": "PESAGEM",
                "lote_id": str(lote.id),
                "data_programada": data_programada,
                "observacoes": f"Planejamento {index + 1}",
            },
        )

    response = await client.get(
        "/api/v1/pecuaria/manejos/planejados?page=1&page_size=2&lote_id=" + str(lote.id),
        headers=headers_admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["lote"]["identificacao"] == "Lote Paginação"
    assert body["items"][0]["quantidade_animais"] == 3
    assert body["items"][0]["area_id"] is None


async def test_listar_planejamentos_inclui_vacinacao(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
) -> None:
    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Listagem Vacina")
    await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "7001")
    produto = await _criar_produto_vacina(session, tenant_requisicao, "Vacina Listagem")

    response_create = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "VACINACAO",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-24",
            "produto_id": str(produto.id),
            "dose": 2.0,
            "unidade_medida": "ML",
        },
    )
    assert response_create.status_code == 201, response_create.text

    response = await client.get(
        "/api/v1/pecuaria/manejos/planejados?tipo=VACINACAO&lote_id=" + str(lote.id),
        headers=headers_admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["tipo"] == "VACINACAO"


async def test_planejar_nao_dispara_manejo_sync_service(
    client: AsyncClient,
    headers_admin: dict[str, str],
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _nao_deve_ser_chamado(*args, **kwargs):
        raise AssertionError("ManejoSyncService não deveria ser acionado no planejamento.")

    monkeypatch.setattr(
        "pecuaria.services.manejo_sync_service.ManejoSyncService.processar_tarefa_campo",
        _nao_deve_ser_chamado,
    )

    tenant_requisicao = uuid.UUID(headers_admin["X-Tenant-ID"])
    lote = await _criar_lote(session, tenant_requisicao, unidade_produtiva_id, "Lote Sem Sync")
    await _criar_animal(session, tenant_requisicao, unidade_produtiva_id, lote.id, "5001")

    response = await client.post(
        "/api/v1/pecuaria/manejos/planejar",
        headers=headers_admin,
        json={
            "tipo": "PESAGEM",
            "lote_id": str(lote.id),
            "data_programada": "2026-07-23",
        },
    )

    assert response.status_code == 201, response.text
    tarefa = (await session.execute(select(TarefaCampo).where(TarefaCampo.lote_id == lote.id))).scalars().first()
    assert tarefa is not None
    eventos = (await session.execute(select(EventoAnimal).where(EventoAnimal.tarefa_campo_id == tarefa.id))).scalars().all()
    assert eventos == []
