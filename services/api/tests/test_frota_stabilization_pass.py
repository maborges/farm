"""
Testes — Frota & Equipamentos — Stabilization Pass

Cobre exportação simples, paginação operacional e hardening de permissões.
"""
from __future__ import annotations

import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.auth_service import AuthService
from core.cadastros.equipamentos.models import Equipamento
from operacional.models.abastecimento import Abastecimento
from operacional.models.frota import JornadaEquipamento, RegistroManutencao
from main import app


USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, 'Tenant Stab', :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_up(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    up_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'UP Stab', true, now(), now())"
        ),
        {"id": str(up_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()
    return up_id


async def _criar_equipamento(session: AsyncSession, tenant_id: uuid.UUID, up_id: uuid.UUID, nome: str) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=up_id,
        nome=nome,
        tipo="TRATOR",
        combustivel="DIESEL",
        status="ATIVO",
        horimetro_atual=120.0,
        km_atual=300.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_jornada(session: AsyncSession, tenant_id: uuid.UUID, equipamento_id: uuid.UUID, up_id: uuid.UUID, inicio: datetime, fim: datetime) -> None:
    session.add(
        JornadaEquipamento(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            operador_id=None,
            unidade_produtiva_id=up_id,
            safra_id=None,
            talhao_id=None,
            tipo_operacao="COLHEITA",
            data_inicio=inicio,
            data_fim=fim,
            horimetro_inicial=120.0,
            horimetro_final=140.0,
            km_inicial=300.0,
            km_final=340.0,
            status="FINALIZADA",
            observacoes="Stab",
        )
    )
    await session.commit()


async def _criar_abastecimento(session: AsyncSession, tenant_id: uuid.UUID, equipamento_id: uuid.UUID) -> None:
    session.add(
        Abastecimento(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            data=datetime.now(timezone.utc) - timedelta(days=1),
            operador_id=None,
            safra_id=None,
            talhao_id=None,
            horimetro_na_data=140.0,
            km_na_data=340.0,
            tipo_combustivel="DIESEL",
            litros=30.0,
            preco_litro=10.0,
            custo_total=300.0,
            tanque_cheio=True,
            local="INTERNO",
            observacoes="Stab",
        )
    )
    await session.commit()


async def _criar_manutencao(session: AsyncSession, tenant_id: uuid.UUID, equipamento_id: uuid.UUID) -> None:
    session.add(
        RegistroManutencao(
            tenant_id=tenant_id,
            equipamento_id=equipamento_id,
            os_id=None,
            safra_id=None,
            talhao_id=None,
            data_realizacao=datetime.now(timezone.utc) - timedelta(days=2),
            tipo="PREVENTIVA",
            descricao="Stab",
            custo_total=120.0,
            executado_por_id=None,
            horimetro_na_data=140.0,
            km_na_data=340.0,
            tecnico_responsavel=None,
        )
    )
    await session.commit()


def _gerar_token_operacional(tenant_id: uuid.UUID) -> str:
    svc = AuthService(object())
    claims = {
        "sub": str(USER_ID),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def headers_operacional(tenant_id: uuid.UUID) -> dict[str, str]:
    token = _gerar_token_operacional(tenant_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": "bbbbbbbb-0000-0000-0000-000000000002",
    }


@pytest.mark.asyncio
async def test_exportacoes_csv_e_xlsx_e_paginacao_jornadas(client, session: AsyncSession, headers_operacional: dict):
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    await _garantir_tenant(session, tenant_id)
    up_id = await _criar_up(session, tenant_id)
    equipamento = await _criar_equipamento(session, tenant_id, up_id, "Trator Stabilization")
    await _criar_jornada(session, tenant_id, equipamento.id, up_id, datetime.now(timezone.utc) - timedelta(hours=5), datetime.now(timezone.utc) - timedelta(hours=2))
    await _criar_jornada(session, tenant_id, equipamento.id, up_id, datetime.now(timezone.utc) - timedelta(hours=10), datetime.now(timezone.utc) - timedelta(hours=8))
    await _criar_abastecimento(session, tenant_id, equipamento.id)
    await _criar_manutencao(session, tenant_id, equipamento.id)

    resp_xlsx = await client.get(
        "/api/v1/frota/export/custos",
        params={"formato": "xlsx", "unidade_produtiva_id": str(up_id)},
        headers=headers_operacional,
    )
    assert resp_xlsx.status_code == 200
    assert "attachment" in resp_xlsx.headers["content-disposition"]
    assert "frota_custos.xlsx" in resp_xlsx.headers["content-disposition"]
    with zipfile.ZipFile(BytesIO(resp_xlsx.content)) as zf:
        assert "xl/workbook.xml" in zf.namelist()
        assert "xl/worksheets/sheet1.xml" in zf.namelist()

    resp_csv = await client.get(
        "/api/v1/frota/export/jornadas",
        params={"formato": "csv", "unidade_produtiva_id": str(up_id)},
        headers=headers_operacional,
    )
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")
    assert "frota_jornadas.csv" in resp_csv.headers["content-disposition"]
    assert "equipamento_nome" in resp_csv.text

    resp_page = await client.get(
        "/api/v1/frota/jornadas",
        params={"unidade_produtiva_id": str(up_id), "limit": 1},
        headers=headers_operacional,
    )
    assert resp_page.status_code == 200
    assert len(resp_page.json()["jornadas"]) == 1


@pytest.mark.asyncio
async def test_rotas_automatizacao_exigem_enterprise(client, session: AsyncSession, headers_operacional: dict):
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    await _garantir_tenant(session, tenant_id)
    resp = await client.get("/api/v1/frota/inteligencia/automacoes/logs", headers=headers_operacional)
    assert resp.status_code in {402, 403}
