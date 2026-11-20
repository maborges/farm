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
from core.models.tenant import Tenant
from campo.models import TarefaCampo
from operacional.models.estoque import Deposito, EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from tests.integration.conftest import FAZENDA_ID, TENANT_ID, _gerar_token
from tests.integration.helpers import garantir_assinatura

pytestmark = pytest.mark.asyncio


def _headers(tenant_id: uuid.UUID) -> dict[str, str]:
    token = _gerar_token(tenant_id, ["CORE", "P1_REBANHO"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(FAZENDA_ID),
    }


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


async def _criar_contexto(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    area_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    production_unit_id = uuid.uuid4()
    session.add_all(
        [
            AreaRural(
                id=area_id,
                tenant_id=tenant_id,
                unidade_produtiva_id=FAZENDA_ID,
                tipo="PIQUETE",
                nome=f"Piquete {area_id.hex[:6]}",
                ativo=True,
            ),
            Safra(id=safra_id, tenant_id=tenant_id, ano_safra="2026/27", cultura="BOVINOCULTURA", status="PLANEJADA"),
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
    await session.commit()
    return area_id, safra_id, production_unit_id


async def _criar_lote(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    area_id: uuid.UUID,
    identificacao: str,
    quantidade: int,
) -> tuple[LoteAnimal, list[Animal]]:
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=FAZENDA_ID,
        area_id=area_id,
        identificacao=identificacao,
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=quantidade,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 24),
        ativo=True,
    )
    session.add(lote)
    await session.commit()
    return lote, []


async def _criar_animais_com_peso(
    session: AsyncSession,
    lote: LoteAnimal,
    tenant_id: uuid.UUID,
    pesos: list[float | None],
) -> list[Animal]:
    animais: list[Animal] = []
    for index, peso in enumerate(pesos):
        animal = Animal(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=FAZENDA_ID,
            lote_id=lote.id,
            numero_brinco=f"{lote.identificacao[:4]}-{index + 1}",
            especie="BOVINO",
            categoria="BEZERRO",
            sexo="MACHO",
            status="ATIVO",
            data_entrada=date(2026, 6, 24),
            peso_atual_kg=peso,
        )
        session.add(animal)
        animais.append(animal)
    await session.commit()
    return animais


async def _registrar_pesagens(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    animal: Animal,
    pesagens: list[tuple[date, float]],
) -> None:
    for data_evento, peso in pesagens:
        session.add(
            EventoAnimal(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                animal_id=animal.id,
                tipo="PESAGEM",
                data_evento=data_evento,
                peso_kg=peso,
                observacoes="pesagem",
            )
        )
    await session.commit()


async def _registrar_vacinacao_com_custo(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lote: LoteAnimal,
    production_unit_id: uuid.UUID,
    produto_nome: str,
    custo_total: float,
    data_vacinacao: date,
) -> None:
    unidade_medida = await _garantir_unidade_medida(session)
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=produto_nome,
        tipo=TipoProduto.VACINA.value,
        unidade_medida="ML",
        preco_medio=4.0,
        ativo=True,
    )
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=FAZENDA_ID,
        nome=f"Dep {produto_nome}",
        tipo="GERAL",
        ativo=True,
    )
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
        unidade_produtiva_id=FAZENDA_ID,
        area_rural_id=lote.area_id,
        lote_id=lote.id,
        dados={},
        concluida_em=datetime.combine(data_vacinacao, datetime.min.time()),
        client_created_at=datetime.combine(data_vacinacao, datetime.min.time()),
        client_updated_at=datetime.combine(data_vacinacao, datetime.min.time()),
    )
    movimento = EstoqueMovimento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        data_movimento=datetime.combine(data_vacinacao, datetime.min.time(), tzinfo=timezone.utc),
        tipo_movimento="SAIDA",
        produto_id=produto.id,
        deposito_id=deposito.id,
        lote_id=None,
        quantidade=-10.0,
        unidade_medida_id=unidade_medida.id,
        custo_unitario=4.0,
        custo_total=custo_total,
        origem="PECUARIA_VACINACAO",
        origem_id=tarefa.id,
        production_unit_id=production_unit_id,
        observacoes=f"PECUARIA_VACINACAO - tarefa {tarefa.id}",
    )
    session.add_all([produto, deposito, tarefa, movimento])
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
            allocation_basis=2,
        )
    )
    await session.commit()


async def _resumo(client: AsyncClient, lote_id: uuid.UUID, headers: dict[str, str]):
    response = await client.get(f"/api/v1/pecuaria/lotes/{lote_id}/indicadores", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_indicadores_sem_animais_retorna_zero(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Sem Animais", 0)

    body = await _resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 0
    assert body["peso_total_kg"] == 0
    assert body["peso_medio_kg"] == 0
    assert body["gmd_medio_kg_dia"] is None
    assert body["ultima_pesagem"] is None
    assert body["custo_sanitario_total"] == 0


async def test_indicadores_animais_sem_peso_retorna_zero(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Sem Peso", 0)
    await _criar_animais_com_peso(session, lote, TENANT_ID, [None, None])

    body = await _resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 2
    assert body["peso_total_kg"] == 0
    assert body["peso_medio_kg"] == 0


async def test_indicadores_peso_total_e_medio(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Peso", 0)
    await _criar_animais_com_peso(session, lote, TENANT_ID, [200.0, 300.0, None])

    body = await _resumo(client, lote.id, headers_admin)

    assert body["quantidade_animais"] == 3
    assert body["peso_total_kg"] == 500.0
    assert body["peso_medio_kg"] == 250.0


async def test_indicadores_ultima_pesagem_e_gmd_medio(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote GMD", 0)
    animais = await _criar_animais_com_peso(session, lote, TENANT_ID, [100.0, 100.0])
    await _registrar_pesagens(session, TENANT_ID, animais[0], [(date(2026, 6, 1), 100.0), (date(2026, 7, 1), 130.0)])
    await _registrar_pesagens(session, TENANT_ID, animais[1], [(date(2026, 6, 1), 100.0), (date(2026, 7, 1), 160.0)])

    body = await _resumo(client, lote.id, headers_admin)

    assert body["ultima_pesagem"] == "2026-07-01"
    assert body["gmd_medio_kg_dia"] == 1.5


async def test_indicadores_custo_sanitario_calcula_rateios(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, production_unit_id = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Custo", 0)
    await _criar_animais_com_peso(session, lote, TENANT_ID, [200.0, 300.0])
    await _registrar_vacinacao_com_custo(
        session,
        tenant_id=TENANT_ID,
        lote=lote,
        production_unit_id=production_unit_id,
        produto_nome="Vacina X",
        custo_total=30.0,
        data_vacinacao=date(2026, 6, 24),
    )

    body = await _resumo(client, lote.id, headers_admin)

    assert body["custo_sanitario_total"] == 30.0
    assert body["custo_sanitario_por_cabeca"] == 15.0
    assert body["custo_sanitario_por_kg"] == 0.06
    assert body["custo_sanitario_por_arroba"] == 1.8


async def test_indicadores_isolamento_multi_tenant(client: AsyncClient, session: AsyncSession, outro_tenant_id: uuid.UUID) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Isolado", 1)
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(outro_tenant_id), "nome": "Tenant Outro", "documento": outro_tenant_id.hex[:11]},
    )
    await garantir_assinatura(session, outro_tenant_id)
    await session.commit()

    response = await client.get(f"/api/v1/pecuaria/lotes/{lote.id}/indicadores", headers=_headers(outro_tenant_id))

    assert response.status_code == 404


async def test_indicadores_pesagem_de_outro_lote_nao_entra(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, _ = await _criar_contexto(session, TENANT_ID)
    lote_a, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote A", 0)
    lote_b, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote B", 0)
    animais_a = await _criar_animais_com_peso(session, lote_a, TENANT_ID, [100.0])
    animais_b = await _criar_animais_com_peso(session, lote_b, TENANT_ID, [100.0])
    await _registrar_pesagens(session, TENANT_ID, animais_a[0], [(date(2026, 6, 1), 100.0), (date(2026, 6, 10), 110.0)])
    await _registrar_pesagens(session, TENANT_ID, animais_b[0], [(date(2026, 6, 1), 100.0), (date(2026, 7, 1), 160.0)])

    body = await _resumo(client, lote_a.id, headers_admin)

    assert body["ultima_pesagem"] == "2026-06-10"
    assert body["gmd_medio_kg_dia"] == 1.111


async def test_indicadores_custo_de_outro_lote_nao_entra(client: AsyncClient, session: AsyncSession, headers_admin: dict[str, str]) -> None:
    area_id, _, production_unit_id = await _criar_contexto(session, TENANT_ID)
    lote_a, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Custo A", 0)
    lote_b, _ = await _criar_lote(session, TENANT_ID, area_id, "Lote Custo B", 0)
    await _criar_animais_com_peso(session, lote_a, TENANT_ID, [200.0, 300.0])
    await _criar_animais_com_peso(session, lote_b, TENANT_ID, [200.0, 300.0])
    await _registrar_vacinacao_com_custo(
        session,
        tenant_id=TENANT_ID,
        lote=lote_a,
        production_unit_id=production_unit_id,
        produto_nome="Vacina A",
        custo_total=20.0,
        data_vacinacao=date(2026, 6, 24),
    )
    await _registrar_vacinacao_com_custo(
        session,
        tenant_id=TENANT_ID,
        lote=lote_b,
        production_unit_id=production_unit_id,
        produto_nome="Vacina B",
        custo_total=80.0,
        data_vacinacao=date(2026, 6, 24),
    )

    body = await _resumo(client, lote_a.id, headers_admin)

    assert body["custo_sanitario_total"] == 20.0
    assert body["custo_sanitario_por_cabeca"] == 10.0
