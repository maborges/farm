from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.cadastros.propriedades.models import AreaRural
from core.models import Tenant, TenantUsuario, Usuario
from core.cadastros.produtos.models import Produto, TipoProduto
from core.measurements.models import UnidadeMedida
from core.models.unidade_produtiva import UnidadeProdutiva
from campo.models import TarefaCampo
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, LoteAnimal
from core.services.auth_service import AuthService
from tests.integration.helpers import garantir_assinatura

pytestmark = pytest.mark.asyncio


def _gerar_headers(tenant_id: uuid.UUID, fazenda_id: uuid.UUID, user_id: uuid.UUID, modules: list[str]) -> dict[str, str]:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "modules": modules,
        "fazendas_auth": [{"id": str(fazenda_id), "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    token = svc.create_access_token(claims, expires_delta=timedelta(hours=1))
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(fazenda_id),
    }


async def _garantir_contexto_base(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session.add(
        Tenant(
            id=tenant_id,
            nome="Tenant Dashboard Pecuaria",
            documento=str(tenant_id).replace("-", "")[:11],
            ativo=True,
        )
    )
    session.add(
        Usuario(
            id=user_id,
            email=f"pecuaria-{user_id.hex[:8]}@example.com",
            username=f"pecuaria_{user_id.hex[:8]}",
            nome_completo="Usuario Pecuaria",
            senha_hash="hash",
            is_superuser=False,
            ativo=True,
        )
    )
    session.add(
        # A unidade produtiva é necessária para o contexto e para manter o tenant isolado.
        # O dashboard aceita X-Fazenda-ID via dependency canônica.
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda Pecuaria Dashboard", ativo=True)
    )
    await session.flush()
    session.add(
        TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=user_id,
            is_owner=True,
            status="ATIVO",
        )
    )
    await session.commit()
    await garantir_assinatura(session, tenant_id)
    await session.commit()
    return tenant_id, fazenda_id, user_id


async def _criar_area_piquete(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    *,
    ativa: bool = True,
    tipo: str = "PIQUETE",
) -> uuid.UUID:
    area_id = uuid.uuid4()
    session.add(
        AreaRural(
            id=area_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            tipo=tipo,
            nome=f"Area {area_id.hex[:6]}",
            ativo=ativa,
        )
    )
    await session.commit()
    return area_id


async def _criar_lote(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    area_id: uuid.UUID | None,
    *,
    ativo: bool = True,
) -> uuid.UUID:
    lote_id = uuid.uuid4()
    session.add(
        LoteAnimal(
            id=lote_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            area_id=area_id,
            identificacao=f"Lote {lote_id.hex[:6]}",
            especie="BOVINO",
            categoria="BEZERRO",
            raca="Nelore",
            quantidade_cabecas=0,
            peso_medio_kg=0.0,
            data_formacao=date(2026, 6, 24),
            ativo=ativo,
        )
    )
    await session.commit()
    return lote_id


async def _criar_animais(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    lote_id: uuid.UUID,
    pesos: list[float | None],
) -> None:
    for index, peso in enumerate(pesos):
        session.add(
            Animal(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=fazenda_id,
                lote_id=lote_id,
                numero_brinco=f"{lote_id.hex[:4]}-{index + 1}",
                especie="BOVINO",
                categoria="BEZERRO",
                sexo="MACHO",
                status="ATIVO",
                data_entrada=date(2026, 6, 24),
                peso_atual_kg=peso,
            )
        )
    await session.commit()


async def _criar_tarefa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    lote_id: uuid.UUID,
    *,
    task_type: str,
    status_execucao: str,
    data_programada: date | None,
) -> uuid.UUID:
    tarefa_id = uuid.uuid4()
    session.add(
        TarefaCampo(
            id=tarefa_id,
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=str(uuid.uuid4()),
            origem="PROGRAMADA",
            status_execucao=status_execucao,
            titulo=f"Tarefa {task_type}",
            prioridade="NORMAL",
            type=task_type,
            module="pecuaria",
            data_programada=data_programada,
            unidade_produtiva_id=fazenda_id,
            area_rural_id=None,
            lote_id=lote_id,
            status=status_execucao,
            dados={"tipo": task_type},
            fotos=[],
            localizacao_status="INDISPONIVEL",
            client_created_at=datetime.utcnow(),
            client_updated_at=datetime.utcnow(),
        )
    )
    await session.commit()
    return tarefa_id


async def _criar_base_eco(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    area_id: uuid.UUID,
) -> uuid.UUID:
    safra_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()
    production_unit_id = uuid.uuid4()
    session.add(
        Safra(
            id=safra_id,
            tenant_id=tenant_id,
            ano_safra="2026/27",
            cultura="BOVINOCULTURA",
            status="PLANEJADA",
        )
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
    await session.commit()
    return production_unit_id


async def _criar_custo_vacinacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    production_unit_id: uuid.UUID,
    tarefa_id: uuid.UUID,
    produto_nome: str,
    custo_total: float,
    data_evento: date,
) -> None:
    unidade_medida = await session.scalar(select(UnidadeMedida.id).where(UnidadeMedida.codigo == "ML"))
    if unidade_medida is None:
        unidade_medida_id = uuid.uuid4()
        session.add(
            UnidadeMedida(
                id=unidade_medida_id,
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
        )
    else:
        unidade_medida_id = unidade_medida

    produto_id = uuid.uuid4()
    session.add(
        Produto(
            id=produto_id,
            tenant_id=tenant_id,
            nome=produto_nome,
            tipo=TipoProduto.VACINA.value,
            unidade_medida="ML",
            preco_medio=4.0,
            ativo=True,
        )
    )
    await session.commit()
    movimento_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO estoque_movimentos
                (id, tenant_id, data_movimento, tipo_movimento, produto_id, deposito_id, lote_id,
                 quantidade, unidade_medida_id, custo_unitario, custo_total, origem, origem_id,
                 production_unit_id, observacoes, created_at)
            VALUES
                (:id, :tenant_id, :data_movimento, 'SAIDA', :produto_id, NULL, NULL,
                 :quantidade, :unidade_medida_id, :custo_unitario, :custo_total, 'PECUARIA_VACINACAO',
                 :origem_id, :production_unit_id, :observacoes, NOW())
            """
        ),
        {
            "id": movimento_id,
            "tenant_id": tenant_id,
            "data_movimento": datetime.combine(data_evento, datetime.min.time(), tzinfo=timezone.utc),
            "produto_id": produto_id,
            "quantidade": -10.0,
            "unidade_medida_id": unidade_medida_id,
            "custo_unitario": 4.0,
            "custo_total": custo_total,
            "origem_id": tarefa_id,
            "production_unit_id": production_unit_id,
            "observacoes": f"PECUARIA_VACINACAO - tarefa {tarefa_id}",
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO cost_allocations
                (id, tenant_id, production_unit_id, source, source_id, inventory_movement_id, cost_category,
                 amount, currency, allocation_date, allocation_method, allocation_basis, created_at)
            VALUES
                (:id, :tenant_id, :production_unit_id, 'PECUARIA_VACINACAO', :source_id, :inventory_movement_id,
                 'SANITARIO', :amount, 'BRL', :allocation_date, 'DIRECT', :allocation_basis, NOW())
            """
        ),
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "production_unit_id": production_unit_id,
            "source_id": tarefa_id,
            "inventory_movement_id": movimento_id,
            "amount": custo_total,
            "allocation_date": data_evento,
            "allocation_basis": 2,
        },
    )
    await session.commit()


@pytest.mark.asyncio
async def test_resumo_vazio(client: AsyncClient, session: AsyncSession):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE", "P1_REBANHO"])

    response = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["animais_ativos"] == 0
    assert data["lotes_ativos"] == 0
    assert data["piquetes_ativos"] == 0
    assert data["peso_total_kg"] == 0.0
    assert data["peso_medio_kg"] == 0.0
    assert data["ua_total"] == 0.0
    assert data["manejos_pendentes"] == 0
    assert data["vacinacoes_pendentes"] == 0
    assert data["custo_sanitario_acumulado"] == 0.0
    assert data["custo_operacional_acumulado"] == 0.0
    assert data["arrobas_totais"] == 0.0
    assert data["custo_total_por_arroba"] == 0.0
    assert data["custo_break_even_por_arroba"] == 0.0


@pytest.mark.asyncio
async def test_animais_lotes_piquetes_e_peso(client: AsyncClient, session: AsyncSession):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE", "P1_REBANHO"])

    area_id = await _criar_area_piquete(session, tenant_id, fazenda_id, ativa=True)
    await _criar_area_piquete(session, tenant_id, fazenda_id, ativa=False)
    lote_id = await _criar_lote(session, tenant_id, fazenda_id, area_id, ativo=True)
    await _criar_lote(session, tenant_id, fazenda_id, None, ativo=True)
    await _criar_lote(session, tenant_id, fazenda_id, None, ativo=False)
    await _criar_animais(session, tenant_id, fazenda_id, lote_id, [100.0, None, 150.0])

    response = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["animais_ativos"] == 3
    assert data["lotes_ativos"] == 2
    assert data["piquetes_ativos"] == 1
    assert data["peso_total_kg"] == 250.0
    assert data["peso_medio_kg"] == 125.0


@pytest.mark.asyncio
async def test_manejos_e_vacinacoes_pendentes_alias(client: AsyncClient, session: AsyncSession):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE", "P1_REBANHO"])
    area_id = await _criar_area_piquete(session, tenant_id, fazenda_id)
    lote_id = await _criar_lote(session, tenant_id, fazenda_id, area_id)

    await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        lote_id,
        task_type="PESAGEM",
        status_execucao="PENDENTE",
        data_programada=date.today(),
    )
    await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        lote_id,
        task_type="VACINACAO_LOTE",
        status_execucao="PENDENTE",
        data_programada=date.today(),
    )

    response = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["manejos_pendentes"] == 2
    assert data["vacinacoes_pendentes"] == 1


@pytest.mark.asyncio
async def test_custo_sanitario_acumulado(client: AsyncClient, session: AsyncSession):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE", "P1_REBANHO"])
    area_id = await _criar_area_piquete(session, tenant_id, fazenda_id)
    lote_id = await _criar_lote(session, tenant_id, fazenda_id, area_id)
    tarefa_id = await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        lote_id,
        task_type="VACINACAO",
        status_execucao="CONCLUIDA",
        data_programada=date.today(),
    )
    production_unit_id = await _criar_base_eco(session, tenant_id, fazenda_id, area_id)
    await _criar_custo_vacinacao(session, tenant_id, production_unit_id, tarefa_id, "Vacina X", 50.0, date.today())

    response = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["custo_sanitario_acumulado"] == 50.0


@pytest.mark.asyncio
async def test_isolamento_multi_tenant(client: AsyncClient, session: AsyncSession):
    tenant_a, fazenda_a, user_a = await _garantir_contexto_base(session)
    tenant_b = uuid.uuid4()
    fazenda_b = uuid.uuid4()
    user_b = uuid.uuid4()
    session.add(
        Tenant(
            id=tenant_b,
            nome="Tenant Pecuaria B",
            documento=str(tenant_b).replace("-", "")[:11],
            ativo=True,
        )
    )
    session.add(
        Usuario(
            id=user_b,
            email=f"pecuaria-b-{user_b.hex[:8]}@example.com",
            username=f"pecuaria_b_{user_b.hex[:8]}",
            nome_completo="Usuario Pecuaria B",
            senha_hash="hash",
            is_superuser=False,
            ativo=True,
        )
    )
    session.add(
        __import__("core.models.unidade_produtiva", fromlist=["UnidadeProdutiva"]).UnidadeProdutiva(
            id=fazenda_b,
            tenant_id=tenant_b,
            nome="Fazenda Pecuaria B",
            ativo=True,
        )
    )
    await session.commit()
    session.add(
        TenantUsuario(
            id=uuid.uuid4(),
            tenant_id=tenant_b,
            usuario_id=user_b,
            is_owner=True,
            status="ATIVO",
        )
    )
    await session.commit()
    await garantir_assinatura(session, tenant_b)
    await session.commit()

    area_a = await _criar_area_piquete(session, tenant_a, fazenda_a)
    lote_a = await _criar_lote(session, tenant_a, fazenda_a, area_a)
    await _criar_animais(session, tenant_a, fazenda_a, lote_a, [100.0])
    headers_a = _gerar_headers(tenant_a, fazenda_a, user_a, ["CORE", "P1_REBANHO"])

    area_b = await _criar_area_piquete(session, tenant_b, fazenda_b)
    lote_b = await _criar_lote(session, tenant_b, fazenda_b, area_b)
    await _criar_animais(session, tenant_b, fazenda_b, lote_b, [200.0])
    headers_b = _gerar_headers(tenant_b, fazenda_b, user_b, ["CORE", "P1_REBANHO"])

    response_a = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers_a)
    response_b = await client.get("/api/v1/pecuaria/dashboard/resumo-executivo", headers=headers_b)
    assert response_a.status_code == 200, response_a.text
    assert response_b.status_code == 200, response_b.text
    assert response_a.json()["animais_ativos"] == 1
    assert response_b.json()["animais_ativos"] == 1
