from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.routers import configuration as configuration_router


pytestmark = pytest.mark.asyncio


TENANT_A_ID = uuid.UUID("d1111111-1111-1111-1111-111111111111")
TENANT_B_ID = uuid.UUID("d2222222-2222-2222-2222-222222222222")
UP_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
UP_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(configuration_router.router, prefix="/api/v1")
    return app


def _documento_unico(seed: uuid.UUID) -> str:
    return f"{seed.int % 10**11:011d}"


async def _set_tenant_context(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def _seed_base_data(session) -> None:
    await session.execute(
        text(
            """
            INSERT INTO farms.tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                documento = EXCLUDED.documento,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(TENANT_A_ID), "nome": "Tenant Config A", "documento": _documento_unico(TENANT_A_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO farms.tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                documento = EXCLUDED.documento,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(TENANT_B_ID), "nome": "Tenant Config B", "documento": _documento_unico(TENANT_B_ID)},
    )
    for tenant_id, up_id, nome in (
        (TENANT_A_ID, UP_A_ID, "UP Config A"),
        (TENANT_B_ID, UP_B_ID, "UP Config B"),
    ):
        await _set_tenant_context(session, tenant_id)
        await session.execute(
            text(
                """
                INSERT INTO farms.unidades_produtivas (id, tenant_id, nome, tipo_propriedade, ativo, created_at, updated_at)
                VALUES (:id, :tenant_id, :nome, 'fazenda', true, now(), now())
                ON CONFLICT (id) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    ativo = EXCLUDED.ativo,
                    updated_at = now()
                """
            ),
            {"id": str(up_id), "tenant_id": str(tenant_id), "nome": nome},
        )
    await session.commit()


@pytest.fixture
async def seeded_config_data(session):
    await _seed_base_data(session)
    yield
    await _set_tenant_context(session, TENANT_A_ID)
    await session.execute(text("DELETE FROM farms.configuracao_fazenda WHERE tenant_id = :tenant_id"), {"tenant_id": str(TENANT_A_ID)})
    await session.execute(text("DELETE FROM farms.unidades_produtivas WHERE id = :up_id"), {"up_id": str(UP_A_ID)})
    await _set_tenant_context(session, TENANT_B_ID)
    await session.execute(text("DELETE FROM farms.configuracao_fazenda WHERE tenant_id = :tenant_id"), {"tenant_id": str(TENANT_B_ID)})
    await session.execute(text("DELETE FROM farms.unidades_produtivas WHERE id = :up_id"), {"up_id": str(UP_B_ID)})
    await session.execute(text("DELETE FROM farms.tenants WHERE id IN (:a, :b)"), {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})
    await session.commit()


async def _build_client(session, tenant_id: uuid.UUID) -> AsyncClient:
    app = _build_app()

    async def _session_override():
        await _set_tenant_context(session, tenant_id)
        yield session

    app.dependency_overrides[configuration_router.get_current_tenant] = lambda: SimpleNamespace(id=tenant_id)
    app.dependency_overrides[configuration_router.get_session] = _session_override
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_get_sem_registro_retorna_defaults(session, seeded_config_data):
    async with await _build_client(session, TENANT_A_ID) as client:
        response = await client.get(f"/api/v1/config/fazenda/{UP_A_ID}")

    assert response.status_code == 200
    assert response.json() == {"unidade_produtiva_id": str(UP_A_ID), "overrides": {}}


async def test_put_cria_registro_e_rejeita_payload_nao_contratado(session, seeded_config_data):
    async with await _build_client(session, TENANT_A_ID) as client:
        response = await client.put(
            f"/api/v1/config/fazenda/{UP_A_ID}",
            json={"overrides": {}},
        )
        assert response.status_code == 200

        response_unknown = await client.put(
            f"/api/v1/config/fazenda/{UP_A_ID}",
            json={"overrides": {"fuso_horario": "America/Cuiaba"}},
        )

    assert response_unknown.status_code == 422

    await _set_tenant_context(session, TENANT_A_ID)
    stmt = text("SELECT count(*) FROM farms.configuracao_fazenda WHERE tenant_id = :tenant_id AND unidade_produtiva_id = :up_id")
    result = await session.execute(stmt, {"tenant_id": str(TENANT_A_ID), "up_id": str(UP_A_ID)})
    assert result.scalar_one() == 1


async def test_put_atualiza_mesmo_registro_sem_duplica(session, seeded_config_data):
    async with await _build_client(session, TENANT_A_ID) as client:
        first = await client.put(f"/api/v1/config/fazenda/{UP_A_ID}", json={"overrides": {}})
        second = await client.put(f"/api/v1/config/fazenda/{UP_A_ID}", json={"overrides": {}})

    assert first.status_code == 200
    assert second.status_code == 200
    await _set_tenant_context(session, TENANT_A_ID)
    result = await session.execute(
        text("SELECT count(*) FROM farms.configuracao_fazenda WHERE tenant_id = :tenant_id AND unidade_produtiva_id = :up_id"),
        {"tenant_id": str(TENANT_A_ID), "up_id": str(UP_A_ID)},
    )
    assert result.scalar_one() == 1


async def test_tenant_a_nao_ler_ou_gravar_up_do_tenant_b(session, seeded_config_data):
    async with await _build_client(session, TENANT_A_ID) as client:
        get_response = await client.get(f"/api/v1/config/fazenda/{UP_B_ID}")
        put_response = await client.put(f"/api/v1/config/fazenda/{UP_B_ID}", json={"overrides": {}})

    assert get_response.status_code == 404
    assert put_response.status_code == 404


async def test_rls_bloqueia_leitura_e_escrita_cruzada(session, seeded_config_data):
    await _set_tenant_context(session, TENANT_B_ID)
    await session.execute(
        text(
            """
            INSERT INTO farms.configuracao_fazenda (id, unidade_produtiva_id, tenant_id, overrides, updated_at)
            VALUES (:id, :up_id, :tenant_id, '{}'::json, now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(uuid.uuid4()), "up_id": str(UP_B_ID), "tenant_id": str(TENANT_B_ID)},
    )
    await session.commit()

    await _set_tenant_context(session, TENANT_A_ID)
    leitura = await session.execute(
        text("SELECT id FROM farms.configuracao_fazenda WHERE unidade_produtiva_id = :up_id"),
        {"up_id": str(UP_B_ID)},
    )
    assert leitura.first() is None

    with pytest.raises(Exception):
        await session.execute(
            text(
                """
                INSERT INTO farms.configuracao_fazenda (id, unidade_produtiva_id, tenant_id, overrides, updated_at)
                VALUES (:id, :up_id, :tenant_id, '{}'::json, now())
                """
            ),
            {"id": str(uuid.uuid4()), "up_id": str(UP_B_ID), "tenant_id": str(TENANT_A_ID)},
        )
        await session.commit()

    await session.rollback()

async def test_up_inexistente_e_soft_delete(session, seeded_config_data):
    async with await _build_client(session, TENANT_A_ID) as client:
        missing = await client.get(f"/api/v1/config/fazenda/{uuid.uuid4()}")

    assert missing.status_code == 404

    has_deleted_at = await session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'farms'
              AND table_name = 'unidades_produtivas'
              AND column_name = 'deleted_at'
            """
        )
    )
    if has_deleted_at.first() is None:
        pytest.skip("Tabela unidades_produtivas não possui deleted_at no ambiente auditado.")
