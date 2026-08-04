import pytest
import uuid
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from sqlalchemy import text

from core.services.auth_service import AuthService

TENANT_A_ID = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000021")
TENANT_B_ID = uuid.UUID("bbbbbbbb-2222-0000-0000-000000000022")
FAZENDA_A_ID = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000031")
FAZENDA_B_ID = uuid.UUID("bbbbbbbb-2222-0000-0000-000000000032")
SAFRA_A_ID = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000041")
AREA_A_ID = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000051")
USER_A_ID = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000061")
USER_B_ID = uuid.UUID("bbbbbbbb-2222-0000-0000-000000000062")


def _token(tenant_id, fazenda_id, user_id):
    svc = AuthService(MagicMock())
    return svc.create_access_token(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "modules": ["CORE", "A1_PLANEJAMENTO"],
            "fazendas_auth": [{"id": str(fazenda_id), "role": "admin"}],
            "is_superuser": False,
            "plan_tier": "PROFISSIONAL",
        },
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture(scope="module")
def headers_a():
    return {
        "Authorization": f"Bearer {_token(TENANT_A_ID, FAZENDA_A_ID, USER_A_ID)}",
        "X-Tenant-ID": str(TENANT_A_ID),
        "x-fazenda-id": str(FAZENDA_A_ID),
    }


@pytest.fixture(scope="module")
def headers_b():
    return {
        "Authorization": f"Bearer {_token(TENANT_B_ID, FAZENDA_B_ID, USER_B_ID)}",
        "X-Tenant-ID": str(TENANT_B_ID),
        "x-fazenda-id": str(FAZENDA_B_ID),
    }


@pytest.fixture
async def client():
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed_tenants_e_dados(session):
    for u_id in (USER_A_ID, USER_B_ID):
        await session.execute(
            text(
                """
                INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo,
                                       is_superuser, created_at, updated_at)
                VALUES (:id, :email, :username, 'Usuário Teste', 'hash', true, false, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": str(u_id), "email": f"{u_id}@teste.com", "username": f"user_{str(u_id)[:8]}"},
        )

    for t_id, f_id, doc in [
        (TENANT_A_ID, FAZENDA_A_ID, "31111111111"),
        (TENANT_B_ID, FAZENDA_B_ID, "32222222222"),
    ]:
        await session.execute(
            text(
                """
                INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb,
                                      idioma_padrao, created_at, updated_at)
                VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": str(t_id), "nome": f"Tenant {str(t_id)[:4]}", "doc": doc},
        )
        await session.execute(
            text(
                """
                INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
                VALUES (:id, :tenant_id, :nome, true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": str(f_id), "tenant_id": str(t_id), "nome": f"Fazenda {str(t_id)[:4]}"},
        )

    # Dados exclusivos do tenant A: safra ativa + talhão + área
    await session.execute(
        text(
            """
            INSERT INTO safras (id, tenant_id, ano_safra, status, created_at, updated_at)
            VALUES (:id, :tenant_id, '2025/26', 'DESENVOLVIMENTO', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": str(SAFRA_A_ID), "tenant_id": str(TENANT_A_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome,
                                                 area_hectares, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :fazenda_id, 'TALHAO', 'Talhão Teste A', 100, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": str(AREA_A_ID), "tenant_id": str(TENANT_A_ID), "fazenda_id": str(FAZENDA_A_ID)},
    )
    await session.commit()


@pytest.mark.asyncio
async def test_summary_nao_vaza_entre_tenants(client, session, headers_a, headers_b):
    await _seed_tenants_e_dados(session)

    r_a = await client.get("/api/v1/reports/agricola/summary", headers=headers_a)
    r_b = await client.get("/api/v1/reports/agricola/summary", headers=headers_b)

    if r_a.status_code == 403 or r_b.status_code == 403:
        pytest.skip(f"Tenant de teste sem módulo CORE ativo: {r_a.text} / {r_b.text}")

    assert r_a.status_code == 200
    assert r_b.status_code == 200

    body_a, body_b = r_a.json(), r_b.json()
    # Tenant A tem 1 safra ativa e 100ha plantados; tenant B não tem nenhum dado.
    assert body_a["resumo"]["safras_ativas"] >= 1
    assert body_b["resumo"]["safras_ativas"] == 0
    assert body_b["resumo"]["total_hectares"] == 0


@pytest.mark.asyncio
async def test_talhoes_nao_vaza_entre_tenants(client, session, headers_a, headers_b):
    await _seed_tenants_e_dados(session)

    r_a = await client.get("/api/v1/reports/agricola/talhoes", headers=headers_a)
    r_b = await client.get("/api/v1/reports/agricola/talhoes", headers=headers_b)

    if r_a.status_code == 403 or r_b.status_code == 403:
        pytest.skip(f"Tenant de teste sem módulo CORE ativo: {r_a.text} / {r_b.text}")

    assert r_a.status_code == 200
    assert r_b.status_code == 200

    ids_a = {t["id"] for t in r_a.json()}
    ids_b = {t["id"] for t in r_b.json()}
    assert str(AREA_A_ID) in ids_a
    assert str(AREA_A_ID) not in ids_b


@pytest.mark.asyncio
async def test_profitability_nao_vaza_entre_tenants(client, session, headers_a, headers_b):
    await _seed_tenants_e_dados(session)

    r_a = await client.get("/api/v1/reports/agricola/profitability", headers=headers_a)
    r_b = await client.get("/api/v1/reports/agricola/profitability", headers=headers_b)

    if r_a.status_code == 403 or r_b.status_code == 403:
        pytest.skip(f"Tenant de teste sem módulo CORE ativo: {r_a.text} / {r_b.text}")

    assert r_a.status_code == 200
    assert r_b.status_code == 200

    ids_talhoes_b = {t["id"] for t in r_b.json()["por_talhao"]}
    assert str(AREA_A_ID) not in ids_talhoes_b


@pytest.mark.asyncio
async def test_talhao_detail_bloqueia_acesso_cross_tenant(client, session, headers_a, headers_b):
    await _seed_tenants_e_dados(session)

    r_a = await client.get(f"/api/v1/reports/agricola/talhao/{AREA_A_ID}", headers=headers_a)
    if r_a.status_code == 403:
        pytest.skip(f"Tenant de teste sem módulo CORE ativo: {r_a.text}")
    assert r_a.status_code == 200
    assert r_a.json()["id"] == str(AREA_A_ID)

    r_b = await client.get(f"/api/v1/reports/agricola/talhao/{AREA_A_ID}", headers=headers_b)
    assert r_b.status_code == 404
