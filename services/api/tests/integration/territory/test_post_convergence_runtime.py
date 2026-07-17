from __future__ import annotations

import uuid
import warnings
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from core.services.auth_service import AuthService
from imoveis.services.imovel_service import NIRFValidator


pytestmark = pytest.mark.asyncio


TENANT_A_ID = uuid.UUID("c1111111-1111-1111-1111-111111111111")
TENANT_B_ID = uuid.UUID("c2222222-2222-2222-2222-222222222222")
USER_A_ID = uuid.UUID("e1111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("e2222222-2222-2222-2222-222222222222")
FAZENDA_A_ID = uuid.UUID("f1111111-1111-1111-1111-111111111111")
FAZENDA_B_ID = uuid.UUID("f2222222-2222-2222-2222-222222222222")
PLANO_A_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")
PLANO_B_ID = uuid.UUID("b2222222-2222-2222-2222-222222222222")


def _token(tenant_id: uuid.UUID, user_id: uuid.UUID, fazenda_id: uuid.UUID) -> str:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "A1_PLANEJAMENTO", "A2_CAMPO"],
        "fazendas_auth": [{"id": str(fazenda_id), "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


def _headers(tenant_id: uuid.UUID, user_id: uuid.UUID, fazenda_id: uuid.UUID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token(tenant_id, user_id, fazenda_id)}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(fazenda_id),
    }


def _nirf_valido(seed: str) -> str:
    corpo = f"{uuid.uuid5(uuid.NAMESPACE_DNS, seed).int % 10**12:012d}"
    return f"{corpo}{NIRFValidator._calcular_dv(corpo)}"


async def _seed_runtime_context(session) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                documento = EXCLUDED.documento,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(TENANT_A_ID), "nome": "Tenant Runtime A", "documento": "91111111111"},
    )
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                documento = EXCLUDED.documento,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(TENANT_B_ID), "nome": "Tenant Runtime B", "documento": "92222222222"},
    )
    await session.execute(
        text(
            """
            INSERT INTO usuarios (id, email, username, senha_hash, ativo, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, 'hash', true, true, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                username = EXCLUDED.username,
                ativo = EXCLUDED.ativo,
                is_superuser = EXCLUDED.is_superuser,
                updated_at = now()
            """
        ),
        {"id": str(USER_A_ID), "email": "runtime-a@example.com", "username": "runtime_a"},
    )
    await session.execute(
        text(
            """
            INSERT INTO usuarios (id, email, username, senha_hash, ativo, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, 'hash', true, true, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                username = EXCLUDED.username,
                ativo = EXCLUDED.ativo,
                is_superuser = EXCLUDED.is_superuser,
                updated_at = now()
            """
        ),
        {"id": str(USER_B_ID), "email": "runtime-b@example.com", "username": "runtime_b"},
    )
    await session.execute(
        text(
            """
            INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, perfil_id, is_owner, status, created_at)
            VALUES (:id, :tenant_id, :usuario_id, NULL, true, 'ATIVO', now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(TENANT_A_ID), "usuario_id": str(USER_A_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, perfil_id, is_owner, status, created_at)
            VALUES (:id, :tenant_id, :usuario_id, NULL, true, 'ATIVO', now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(TENANT_B_ID), "usuario_id": str(USER_B_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO planos_assinatura (
                id, nome, modulos_inclusos, limite_usuarios_minimo, limite_usuarios_maximo,
                preco_mensal, preco_anual, max_fazendas, max_categorias_plano, tem_trial, dias_trial,
                is_free, destaque, ordem, ativo, disponivel_site, disponivel_crm, created_at
            )
            VALUES (
                :id, :nome, CAST(:modulos AS json), 1, 10,
                0, 0, -1, -1, false, 15,
                false, false, 0, true, false, true, now()
            )
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                modulos_inclusos = EXCLUDED.modulos_inclusos,
                ativo = EXCLUDED.ativo
            """
        ),
        {"id": str(PLANO_A_ID), "nome": "Plano Runtime A", "modulos": '["CORE","A1_PLANEJAMENTO","A2_CAMPO"]'},
    )
    await session.execute(
        text(
            """
            INSERT INTO planos_assinatura (
                id, nome, modulos_inclusos, limite_usuarios_minimo, limite_usuarios_maximo,
                preco_mensal, preco_anual, max_fazendas, max_categorias_plano, tem_trial, dias_trial,
                is_free, destaque, ordem, ativo, disponivel_site, disponivel_crm, created_at
            )
            VALUES (
                :id, :nome, CAST(:modulos AS json), 1, 10,
                0, 0, -1, -1, false, 15,
                false, false, 0, true, false, true, now()
            )
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                modulos_inclusos = EXCLUDED.modulos_inclusos,
                ativo = EXCLUDED.ativo
            """
        ),
        {"id": str(PLANO_B_ID), "nome": "Plano Runtime B", "modulos": '["CORE","A1_PLANEJAMENTO","A2_CAMPO"]'},
    )
    await session.execute(
        text(
            """
            INSERT INTO assinaturas_tenant (
                id, tenant_id, plano_id, tipo_assinatura, ciclo_pagamento, usuarios_contratados,
                status, grace_period_days, created_at, updated_at
            )
            VALUES (:id, :tenant_id, :plano_id, 'TENANT', 'MENSAL', 10, 'ATIVA', 3, now(), now())
            ON CONFLICT (tenant_id, tipo_assinatura) DO UPDATE SET
                plano_id = EXCLUDED.plano_id,
                status = EXCLUDED.status,
                updated_at = now()
            """
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(TENANT_A_ID), "plano_id": str(PLANO_A_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO assinaturas_tenant (
                id, tenant_id, plano_id, tipo_assinatura, ciclo_pagamento, usuarios_contratados,
                status, grace_period_days, created_at, updated_at
            )
            VALUES (:id, :tenant_id, :plano_id, 'TENANT', 'MENSAL', 10, 'ATIVA', 3, now(), now())
            ON CONFLICT (tenant_id, tipo_assinatura) DO UPDATE SET
                plano_id = EXCLUDED.plano_id,
                status = EXCLUDED.status,
                updated_at = now()
            """
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(TENANT_B_ID), "plano_id": str(PLANO_B_ID)},
    )
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, tipo_propriedade, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :nome, 'fazenda', true, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(FAZENDA_A_ID), "tenant_id": str(TENANT_A_ID), "nome": "Fazenda Runtime A"},
    )
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, tipo_propriedade, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :nome, 'fazenda', true, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                nome = EXCLUDED.nome,
                ativo = EXCLUDED.ativo,
                updated_at = now()
            """
        ),
        {"id": str(FAZENDA_B_ID), "tenant_id": str(TENANT_B_ID), "nome": "Fazenda Runtime B"},
    )
    await session.commit()


@pytest.fixture
async def runtime_setup(session):
    await _seed_runtime_context(session)
    yield


async def _create_simple_up(client, headers, nome: str) -> dict:
    response = await client.post(
        "/api/v1/unidades-produtivas",
        json={
            "nome": nome,
            "tipo_propriedade": "fazenda",
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_ha": 1000.0,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cadastro_payload(
    nome_up: str,
    nome_propriedade: str,
    nome_imovel: str | None,
    *,
    nif_seed: str | None = None,
    imovel_id: uuid.UUID | None = None,
    propriedade_id: uuid.UUID | None = None,
    vinculo_id: uuid.UUID | None = None,
    vinculo_principal: bool | None = None,
    area_total_ha: str = "120.0000",
    area_explorada_ha: str | None = "80.0000",
    incluir_exploracao: bool = True,
) -> dict:
    payload = {
        "unidade_produtiva": {
            "nome": nome_up,
            "tipo_propriedade": "fazenda",
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_ha": 1000.0,
        },
        "propriedade": {
            "id": str(propriedade_id) if propriedade_id else None,
            "nome": nome_propriedade,
        },
        "exploracao_rural": None
        if not incluir_exploracao
        else (
            {
                "natureza": "propria",
                "data_inicio": date.today().isoformat(),
                "observacoes": "fluxo runtime",
            }
            if area_explorada_ha is None
            else {
                "natureza": "propria",
                "data_inicio": date.today().isoformat(),
                "area_explorada_ha": float(area_explorada_ha),
                "observacoes": "fluxo runtime",
            }
        ),
        "imovel_rural": None
        if nome_imovel is None
        else {
            "id": str(imovel_id) if imovel_id else None,
            "nome": nome_imovel,
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_ha": float(area_total_ha),
            "nirf": _nirf_valido(f"{nome_imovel}|{nif_seed or ''}"),
            "car_numero": "MT123456789012",
            "ccir_numero": "CCIR-123",
            "numero_matricula": "12.345",
            "tipo": "rural",
            "observacao": "fluxo runtime",
        },
        "propriedade_imovel": None
        if nome_imovel is None
        else {
            "id": str(vinculo_id) if vinculo_id else None,
            "tipo_vinculo": "PROPRIEDADE_SECUNDARIA" if vinculo_principal is False else "PROPRIEDADE_PRINCIPAL",
            "ativo": True,
            "data_inicio": date.today().isoformat(),
            "origem_documental": "Contrato base",
            "vinculo_principal": vinculo_principal if vinculo_principal is not None else True,
            "status_documental": "VALIDO",
        },
    }
    return payload


async def _resolve_context(session, tenant_id: uuid.UUID, up_id: uuid.UUID) -> dict[str, uuid.UUID]:
    propriedade_id = (
        await session.execute(
            text(
                """
                SELECT p.id
                FROM cadastros_propriedades p
                JOIN cadastros_exploracoes_rurais e ON e.propriedade_id = p.id
                WHERE p.tenant_id = :tenant_id
                  AND e.unidade_produtiva_id = :up_id
                ORDER BY e.created_at ASC
                LIMIT 1
                """
            ),
            {"tenant_id": str(tenant_id), "up_id": str(up_id)},
        )
    ).scalar_one()

    rows = (
        await session.execute(
            text(
                """
                SELECT i.id, i.nome, pi.vinculo_principal
                FROM imoveis_rurais i
                JOIN propriedade_imovel pi ON pi.imovel_rural_id = i.id
                WHERE i.tenant_id = :tenant_id
                  AND pi.propriedade_id = :propriedade_id
                ORDER BY pi.vinculo_principal DESC, pi.created_at ASC
                """
            ),
            {"tenant_id": str(tenant_id), "propriedade_id": str(propriedade_id)},
        )
    ).all()

    vinculo_ids = (
        await session.execute(
            text(
                """
                SELECT pi.id, pi.imovel_rural_id, pi.vinculo_principal
                FROM propriedade_imovel pi
                WHERE pi.tenant_id = :tenant_id
                  AND pi.propriedade_id = :propriedade_id
                ORDER BY pi.vinculo_principal DESC, pi.created_at ASC
                """
            ),
            {"tenant_id": str(tenant_id), "propriedade_id": str(propriedade_id)},
        )
    ).all()

    result = {
        "propriedade_id": propriedade_id,
        "imovel_1_id": rows[0][0] if rows else None,
        "imovel_2_id": rows[1][0] if len(rows) > 1 else None,
        "vinculo_1_id": vinculo_ids[0][0] if vinculo_ids else None,
        "vinculo_2_id": vinculo_ids[1][0] if len(vinculo_ids) > 1 else None,
        "principal_vinculo_id": next((row[0] for row in vinculo_ids if row[2]), None),
    }
    return result


async def _count(session, sql: str, **params) -> int:
    return int((await session.execute(text(sql), params)).scalar_one())


async def test_cadastro_simples_up_runtime(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    data = await _create_simple_up(client, headers, "UP Runtime Simples")
    up_id = uuid.UUID(data["id"])

    assert data["nome"] == "UP Runtime Simples"

    assert await _count(
        session,
        "SELECT count(*) FROM cadastros_exploracoes_rurais WHERE tenant_id = :tenant_id AND unidade_produtiva_id = :up_id",
        tenant_id=str(TENANT_A_ID),
        up_id=str(up_id),
    ) == 0


async def test_detalhe_e_lista_unidade_produtiva(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    data = await _create_simple_up(client, headers, "UP Runtime Detalhe")
    up_id = uuid.UUID(data["id"])

    get_response = await client.get(f"/api/v1/unidades-produtivas/{up_id}", headers=headers)
    assert get_response.status_code == 200, get_response.text
    assert uuid.UUID(get_response.json()["id"]) == up_id

    list_response = await client.get("/api/v1/unidades-produtivas", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == str(up_id) for item in list_response.json())


async def test_cadastro_completo_sem_imovel(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload(
            "UP Completa Sem Imovel",
            "Propriedade Sem Imovel",
            None,
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    up_id = uuid.UUID(response.json()["id"])

    contexto = await _resolve_context(session, TENANT_A_ID, up_id)
    assert contexto["propriedade_id"] is not None
    assert contexto["imovel_1_id"] is None
    assert contexto["vinculo_1_id"] is None

    assert await _count(
        session,
        "SELECT count(*) FROM cadastros_exploracoes_rurais WHERE tenant_id = :tenant_id AND unidade_produtiva_id = :up_id",
        tenant_id=str(TENANT_A_ID),
        up_id=str(up_id),
    ) == 1


async def test_cadastro_completo_com_imovel_e_atualizacao_idempotente(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    seed = uuid.uuid4().hex[:8]
    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload(
            "UP Completa Com Imovel",
            "Propriedade Runtime",
            "Imovel Runtime 1",
            nif_seed=seed,
        ),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    assert contexto["propriedade_id"] is not None
    assert contexto["imovel_1_id"] is not None
    assert contexto["principal_vinculo_id"] is not None

    update_payload = _cadastro_payload(
        "UP Completa Com Imovel Atualizada",
        "Propriedade Runtime Atualizada",
        "Imovel Runtime 1 Atualizado",
        propriedade_id=contexto["propriedade_id"],
        imovel_id=contexto["imovel_1_id"],
        vinculo_id=contexto["principal_vinculo_id"],
        vinculo_principal=True,
        area_explorada_ha=None,
        incluir_exploracao=False,
        nif_seed=seed,
    )
    update_response = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=update_payload,
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert uuid.UUID(update_response.json()["id"]) == up_id

    update_repeat = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=update_payload,
        headers=headers,
    )
    assert update_repeat.status_code == 200, update_repeat.text
    assert uuid.UUID(update_repeat.json()["id"]) == up_id

    contexto_final = await _resolve_context(session, TENANT_A_ID, up_id)
    assert contexto_final["propriedade_id"] == contexto["propriedade_id"]
    assert contexto_final["imovel_1_id"] == contexto["imovel_1_id"]
    assert contexto_final["vinculo_1_id"] == contexto["vinculo_1_id"]


async def test_atualizacao_sem_imovel_id_reaproveita_principal_existente(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    seed = uuid.uuid4().hex[:8]
    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload(
            "UP Reuso Principal",
            "Propriedade Reuso",
            "Imovel Reuso 1",
            nif_seed=seed,
        ),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    update_response = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=_cadastro_payload(
            "UP Reuso Principal",
            "Propriedade Reuso",
            "Imovel Reuso 1 Atualizado",
            propriedade_id=contexto["propriedade_id"],
            area_explorada_ha=None,
            incluir_exploracao=False,
            nif_seed=seed,
        ),
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text

    contexto_final = await _resolve_context(session, TENANT_A_ID, up_id)
    assert contexto_final["imovel_1_id"] == contexto["imovel_1_id"]
    assert contexto_final["vinculo_1_id"] == contexto["vinculo_1_id"]
    imovel_atualizado = await session.execute(
        text(
            """
            SELECT nome
            FROM imoveis_rurais
            WHERE tenant_id = :tenant_id
              AND id = :imovel_id
              AND deleted_at IS NULL
            """
        ),
        {"tenant_id": str(TENANT_A_ID), "imovel_id": str(contexto["imovel_1_id"])},
    )
    assert imovel_atualizado.scalar_one() == "Imovel Reuso 1 Atualizado"


async def test_segundo_imovel_e_troca_explicita_de_principal(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    seed = uuid.uuid4().hex[:8]
    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload(
            "UP Multi Imovel",
            "Propriedade Multi",
            "Imovel Multi 1",
            nif_seed=seed,
        ),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    second_payload = _cadastro_payload(
        "UP Multi Imovel",
        "Propriedade Multi",
        "Imovel Multi 2",
        propriedade_id=contexto["propriedade_id"],
        vinculo_principal=False,
        area_total_ha="80.0000",
        area_explorada_ha=None,
        incluir_exploracao=False,
        nif_seed=seed,
    )
    second_response = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=second_payload,
        headers=headers,
    )
    assert second_response.status_code == 200, second_response.text

    contexto_2 = await _resolve_context(session, TENANT_A_ID, up_id)
    assert contexto_2["imovel_2_id"] is not None
    assert contexto_2["vinculo_2_id"] is not None

    principal_before = contexto_2["principal_vinculo_id"]
    swap_response = await client.post(
        f"/api/v1/propriedade-imovel/{contexto_2['vinculo_2_id']}/definir-principal",
        params={"propriedade_id": str(contexto_2["propriedade_id"])},
        headers=headers,
    )
    assert swap_response.status_code == 200, swap_response.text
    assert swap_response.json()["vinculo_principal"] is True

    contexto_3 = await _resolve_context(session, TENANT_A_ID, up_id)
    assert contexto_3["principal_vinculo_id"] == contexto_2["vinculo_2_id"]
    assert contexto_3["principal_vinculo_id"] != principal_before


async def test_visoes_territorial_e_fundiaria(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    seed = uuid.uuid4().hex[:8]
    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload(
            "UP Visao",
            "Propriedade Visao",
            "Imovel Visao 1",
            nif_seed=seed,
        ),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    r_territorial = await client.get(
        f"/api/v1/propriedades/{contexto['propriedade_id']}/visao-territorial",
        headers=headers,
    )
    assert r_territorial.status_code == 200, r_territorial.text
    body_territorial = r_territorial.json()
    assert body_territorial["propriedade"]["id"] == str(contexto["propriedade_id"])
    assert body_territorial["vinculos"][0]["imovel_rural"]["id"] == str(contexto["imovel_1_id"])

    r_fundiaria = await client.get(
        f"/api/v1/imoveis-rurais/{contexto['imovel_1_id']}/visao-fundiaria",
        headers=headers,
    )
    assert r_fundiaria.status_code == 200, r_fundiaria.text
    body_fundiaria = r_fundiaria.json()
    assert body_fundiaria["imovel_rural"]["id"] == str(contexto["imovel_1_id"])
    assert body_fundiaria["propriedades_vinculadas"][0]["id"] == str(contexto["propriedade_id"])


async def test_delete_up_sem_warning_sqlalchemy(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    response = await client.post(
        "/api/v1/unidades-produtivas",
        json={
            "nome": "UP Delete Runtime",
            "tipo_propriedade": "fazenda",
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_ha": 900.0,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    up_id = uuid.UUID(response.json()["id"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        delete_response = await client.delete(f"/api/v1/unidades-produtivas/{up_id}", headers=headers)

    assert delete_response.status_code in {204, 409}, delete_response.text
    assert not any("DELETE expected to delete 1 row(s); 0 were matched" in str(item.message) for item in caught)

    get_response = await client.get(f"/api/v1/unidades-produtivas/{up_id}", headers=headers)
    if delete_response.status_code == 204:
        assert get_response.status_code == 404
    else:
        assert get_response.status_code in {200, 404}


async def test_rls_bloqueia_tenant_divergente(client, session, runtime_setup):
    headers_a = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    headers_b = _headers(TENANT_B_ID, USER_B_ID, FAZENDA_B_ID)
    seed = uuid.uuid4().hex[:8]

    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload("UP RLS", "Propriedade RLS", "Imovel RLS", nif_seed=seed),
        headers=headers_a,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    get_other = await client.get(f"/api/v1/unidades-produtivas/{up_id}", headers=headers_b)
    assert get_other.status_code == 404

    update_other = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=_cadastro_payload("UP RLS B", "Propriedade RLS B", None),
        headers=headers_b,
    )
    assert update_other.status_code in {404, 403}

    assoc_other = await client.post(
        "/api/v1/propriedade-imovel",
        json={
            "propriedade_id": str(contexto["propriedade_id"]),
            "imovel_rural_id": str(contexto["imovel_1_id"]),
            "tipo_vinculo": "PROPRIEDADE_SECUNDARIA",
            "ativo": True,
            "data_inicio": date.today().isoformat(),
            "origem_documental": "RLS",
        },
        headers=headers_b,
    )
    assert assoc_other.status_code in {404, 403}


async def test_rollback_integral_quando_associacao_falha(client, session, runtime_setup):
    headers = _headers(TENANT_A_ID, USER_A_ID, FAZENDA_A_ID)
    seed = uuid.uuid4().hex[:8]
    rollback_suffix = uuid.uuid4().hex[:8]
    nome_imovel_rollback = f"Imovel Rollback 2 {rollback_suffix}"
    create_response = await client.post(
        "/api/v1/unidades-produtivas/cadastro-completo",
        json=_cadastro_payload("UP Rollback Base", "Propriedade Rollback", "Imovel Rollback 1", nif_seed=seed),
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    up_id = uuid.UUID(create_response.json()["id"])
    contexto = await _resolve_context(session, TENANT_A_ID, up_id)

    failing_payload = _cadastro_payload(
        "UP Rollback Tentativa",
        "Propriedade Rollback",
        nome_imovel_rollback,
        propriedade_id=contexto["propriedade_id"],
        vinculo_principal=True,
        area_total_ha="121.0000",
        area_explorada_ha=None,
        incluir_exploracao=False,
        nif_seed=seed,
    )
    failing_response = await client.put(
        f"/api/v1/unidades-produtivas/{up_id}/cadastro-completo",
        json=failing_payload,
        headers=headers,
    )
    assert failing_response.status_code in {400, 409, 422}, failing_response.text

    imovel_rollback = await session.execute(
        text(
            """
            SELECT count(*)
            FROM imoveis_rurais
            WHERE tenant_id = :tenant_id
              AND nome = :nome
              AND deleted_at IS NULL
            """
        ),
        {"tenant_id": str(TENANT_A_ID), "nome": nome_imovel_rollback},
    )
    assert imovel_rollback.scalar_one() == 0

    vinculos = await session.execute(
        text(
            """
            SELECT count(*)
            FROM propriedade_imovel
            WHERE tenant_id = :tenant_id
              AND propriedade_id = :propriedade_id
            """
        ),
        {"tenant_id": str(TENANT_A_ID), "propriedade_id": str(contexto["propriedade_id"])},
    )
    assert vinculos.scalar_one() == 1
