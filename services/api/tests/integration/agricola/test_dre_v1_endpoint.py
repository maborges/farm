from __future__ import annotations

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from agricola.dre.schemas import DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DRESourceItem, DREWarning
from core.services.auth_service import hash_password
from core.services.auth_service import AuthService
from tests.integration.helpers import garantir_assinatura, PLANO_BASE_ID
from tests.integration.conftest import TENANT_ID, FAZENDA_ID, USER_ID


def _token_sem_tenant(modules: list[str], plan_tier: str = "PROFISSIONAL") -> str:
    svc = AuthService(MagicMock())
    return svc.create_access_token(
        {
            "sub": str(USER_ID),
            "modules": modules,
            "fazendas_auth": [{"id": str(FAZENDA_ID), "role": "admin"}],
            "is_superuser": False,
            "plan_tier": plan_tier,
        },
        expires_delta=None,
    )


def _token_com_tenant(modules: list[str], plan_tier: str = "PROFISSIONAL") -> str:
    svc = AuthService(MagicMock())
    return svc.create_access_token(
        {
            "sub": str(USER_ID),
            "tenant_id": str(TENANT_ID),
            "modules": modules,
            "fazendas_auth": [{"id": str(FAZENDA_ID), "role": "admin"}],
            "is_superuser": False,
            "plan_tier": plan_tier,
        },
        expires_delta=None,
    )


async def _setup_contexto_acesso(session):
    await session.execute(text("""
        INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
        VALUES (:id, 'Tenant DRE V1', '12345678000199', true, 0, 10240, 'pt-BR', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(TENANT_ID)})

    await session.execute(text("""
        INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at)
        VALUES (:id, 'dre-v1@teste.com', 'drev1teste', 'Usuário DRE V1', :hash, true, false, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(USER_ID), "hash": hash_password("Agro@123456")})

    perfil_id = (await session.execute(text(
        "SELECT id FROM perfis_acesso WHERE tenant_id IS NULL AND nome = 'agronomo' LIMIT 1"
    ))).scalar_one_or_none()
    if perfil_id is None:
        perfil_id = (await session.execute(text("""
            INSERT INTO perfis_acesso (id, tenant_id, nome, descricao, is_custom, permissoes, created_at)
            VALUES (gen_random_uuid(), NULL, 'agronomo', 'Perfil Agrônomo', false, '{}'::json, NOW())
            RETURNING id
        """))).scalar_one()

    await garantir_assinatura(session, TENANT_ID)

    await session.execute(text("""
        DELETE FROM tenant_usuarios
        WHERE tenant_id = :tenant_id AND usuario_id = :usuario_id
    """), {
        "tenant_id": str(TENANT_ID),
        "usuario_id": str(USER_ID),
    })

    await session.execute(text("""
        INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, perfil_id, is_owner, status, created_at)
        VALUES (gen_random_uuid(), :tenant_id, :usuario_id, :perfil_id, false, 'ATIVO', NOW())
    """), {
        "tenant_id": str(TENANT_ID),
        "usuario_id": str(USER_ID),
        "perfil_id": str(perfil_id),
    })

    await session.commit()


async def _ajustar_assinatura(session, *, modules: list[str], plan_tier: str) -> None:
    await session.execute(text("""
        UPDATE planos_assinatura
           SET modulos_inclusos = CAST(:modulos AS json),
               plan_tier = :plan_tier
         WHERE id = :plano_id
    """), {
        "modulos": json.dumps(modules),
        "plan_tier": plan_tier,
        "plano_id": str(PLANO_BASE_ID),
    })
    await session.commit()


def _fake_response(*, tenant_id, safra_id, production_unit_id=None, unidade_produtiva_id=None) -> DREAgricolaResponse:
    warning = DREWarning(
        codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
        titulo="Movimento de estoque com custo sem apropriação",
        severidade="RISCO_ECONOMICO",
        mensagem="Há movimento de estoque com custo e sem CostAllocation na unidade filtrada.",
        origem="estoque_movimentos",
        amostras=[str(uuid4())],
        meta={"quantidade": 1},
    )
    item = DRESourceItem(
        natureza="RECEITA_OPERACIONAL",
        fonte_oficial="Receita",
        origem_tipo="COMERCIALIZACAO",
        origem_id=uuid4(),
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra_id=safra_id,
        valor=1000.0,
        meta={"receita_id": str(uuid4())},
    )
    section = DREAgricolaSection(
        valor=1000.0,
        itens=[item],
        total_registros=1,
        fontes={"COMERCIALIZACAO": 1000.0},
    )
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
        production_unit_ids=[production_unit_id] if production_unit_id else [],
        cultura="SOJA",
        receita_bruta=1000.0,
        deducoes=0.0,
        receita_liquida=1000.0,
        custos_diretos=0.0,
        custos_operacionais=0.0,
        margem_bruta=1000.0,
        despesas_operacionais=0.0,
        resultado_operacional=1000.0,
        receita=section,
        custos_diretos_detalhe=DREAgricolaSection(),
        custos_operacionais_detalhe=DREAgricolaSection(),
        despesas_operacionais_detalhe=DREAgricolaSection(),
        warnings=[warning],
        reconciliacao=DREReconcilacaoMeta(
            lancamentos_financeiros_receita=1200.0,
            lancamentos_financeiros_custo=200.0,
            lancamentos_financeiros_total=1000.0,
            estoque_movimentos_com_custo=1,
            cost_allocations_total=1,
            observacao="Reconciliacao sintetica para validacao do endpoint.",
            detalhes={"fonte": "teste"},
        ),
    )


@pytest.mark.asyncio
async def test_dre_v1_endpoint_exige_tenant(client: AsyncClient):
    token = _token_sem_tenant(["CORE", "A1_PLANEJAMENTO"])
    response = await client.get(
        "/api/v1/agricola/dre/v1?safra_id=00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dre_v1_endpoint_rejeita_core_only(client: AsyncClient, headers_core_only: dict, session):
    await _setup_contexto_acesso(session)
    await _ajustar_assinatura(session, modules=["CORE"], plan_tier="PROFISSIONAL")

    response = await client.get(
        "/api/v1/agricola/dre/v1?safra_id=00000000-0000-0000-0000-000000000001",
        headers=headers_core_only,
    )

    assert response.status_code == 402
    assert response.headers.get("X-Module-Required") == "A1_PLANEJAMENTO"


@pytest.mark.asyncio
async def test_dre_v1_endpoint_rejeita_tier_basico(client: AsyncClient, session):
    await _setup_contexto_acesso(session)
    await _ajustar_assinatura(session, modules=["CORE", "A1_PLANEJAMENTO", "A2_CAMPO"], plan_tier="BASICO")

    token = _token_com_tenant(["CORE", "A1_PLANEJAMENTO"], plan_tier="BASICO")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(TENANT_ID),
        "X-Fazenda-ID": str(FAZENDA_ID),
    }

    response = await client.get(
        "/api/v1/agricola/dre/v1?safra_id=00000000-0000-0000-0000-000000000001",
        headers=headers,
    )

    assert response.status_code == 402
    assert response.headers.get("X-Tier-Required") == "PROFISSIONAL"


@pytest.mark.asyncio
async def test_dre_v1_endpoint_delega_servico_e_retorna_metadata(
    client: AsyncClient,
    headers_agricola: dict,
    session,
):
    await _setup_contexto_acesso(session)
    await _ajustar_assinatura(session, modules=["CORE", "A1_PLANEJAMENTO", "A2_CAMPO"], plan_tier="PROFISSIONAL")

    safra_id = uuid4()
    production_unit_id = uuid4()
    unidade_produtiva_id = uuid4()
    fake_response = _fake_response(
        tenant_id=TENANT_ID,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )
    captured = {}

    class FakeService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id
            captured["session_type"] = type(session).__name__

        async def gerar(self, **kwargs):
            captured["kwargs"] = kwargs
            return fake_response

    with (
        patch("agricola.dre.router.DREAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()),
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()),
    ):
        response = await client.get(
            "/api/v1/agricola/dre/v1",
            params={
                "safra_id": str(safra_id),
                "production_unit_id": str(production_unit_id),
                "unidade_produtiva_id": str(unidade_produtiva_id),
                "data_inicio": str(date(2026, 1, 1)),
                "data_fim": str(date(2026, 1, 31)),
            },
            headers=headers_agricola,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tenant_id"] == str(TENANT_ID)
    assert payload["safra_id"] == str(safra_id)
    assert payload["production_unit_id"] == str(production_unit_id)
    assert payload["unidade_produtiva_id"] == str(unidade_produtiva_id)
    assert payload["warnings"]
    assert payload["reconciliacao"]["observacao"] is not None
    assert captured["tenant_id"] == TENANT_ID
    assert captured["kwargs"] == {
        "safra_id": safra_id,
        "production_unit_id": production_unit_id,
        "unidade_produtiva_id": unidade_produtiva_id,
        "data_inicio": date(2026, 1, 1),
        "data_fim": date(2026, 1, 31),
    }
