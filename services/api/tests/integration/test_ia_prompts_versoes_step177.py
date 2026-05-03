"""
Testes de integração — Controle de Versão do Prompt (Step 177).
Cobre: criar versão, ativar versão, apenas uma ativa por contexto, fallback hardcoded.
"""
import pytest
from httpx import AsyncClient
import uuid
from ia.models import IAPromptVersao
from datetime import datetime, timezone
from datetime import timedelta
from unittest.mock import MagicMock

from sqlalchemy import delete
from core.services.auth_service import AuthService
from core.models.tenant import Tenant

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
OUTRO_TENANT_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
BASE_URL = "/api/v1/ia/prompts/versoes"

CONTEUDO_TESTE = "Prompt de teste v{versao}.\n\nDADOS:\n{{dados}}\n\n{{feedback_block}}"


@pytest.fixture(autouse=True)
async def _limpar_prompt_versoes(session):
    from ia.models import IAPromptVersaoHistorico

    await session.execute(delete(IAPromptVersaoHistorico))
    await session.execute(delete(IAPromptVersao))
    await session.commit()
    yield
    await session.execute(delete(IAPromptVersaoHistorico))
    await session.execute(delete(IAPromptVersao))
    await session.commit()


async def _garantir_tenant(session, tenant_id: uuid.UUID, nome: str) -> None:
    if await session.get(Tenant, tenant_id):
        return
    session.add(
        Tenant(
            id=tenant_id,
            nome=nome,
            documento=str(tenant_id).replace("-", "")[:14],
            ativo=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()


def _headers_tenant(tenant_id: uuid.UUID) -> dict:
    claims = {
        "sub": str(USER_ID),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    token = AuthService(MagicMock()).create_access_token(claims, expires_delta=timedelta(hours=1))
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": "bbbbbbbb-0000-0000-0000-000000000002",
    }


async def _criar_versao(session, tenant_id=TENANT_ID, versao="v1", ativo=False, contexto="COMPRAS_ESTRATEGIA") -> IAPromptVersao:
    rec = IAPromptVersao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contexto=contexto,
        versao=versao,
        conteudo=CONTEUDO_TESTE.format(versao=versao),
        ativo=ativo,
        observacao=f"Versão {versao} de teste",
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_criar_versao(client: AsyncClient, headers_operacional: dict):
    """POST deve criar versão inativa por padrão."""
    conteudo = CONTEUDO_TESTE.format(versao="v1")
    resp = await client.post(
        BASE_URL,
        json={"contexto": "COMPRAS_ESTRATEGIA", "versao": "v1", "conteudo": conteudo, "observacao": "Teste"},
        headers=headers_operacional,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["versao"] == "v1"
    assert data["ativo"] is False
    assert data["is_global"] is False
    assert data["conteudo"] == conteudo


@pytest.mark.asyncio
async def test_listar_versoes(client: AsyncClient, session, headers_operacional: dict):
    """GET deve retornar versões do tenant."""
    await _criar_versao(session, versao="v1")
    await _criar_versao(session, versao="v2")

    resp = await client.get(f"{BASE_URL}?contexto=COMPRAS_ESTRATEGIA", headers=headers_operacional)
    assert resp.status_code == 200
    versoes = resp.json()
    assert len(versoes) >= 2
    for v in versoes:
        assert "id" in v
        assert "versao" in v
        assert "ativo" in v
        assert "conteudo" in v


@pytest.mark.asyncio
async def test_ativar_versao(client: AsyncClient, session, headers_operacional: dict):
    """PATCH /ativar deve marcar a versão como ativa."""
    rec = await _criar_versao(session, versao="v1", ativo=False)

    resp = await client.patch(f"{BASE_URL}/{rec.id}/ativar", headers=headers_operacional)
    assert resp.status_code == 200
    assert resp.json()["ativo"] is True

    await session.refresh(rec)
    assert rec.ativo is True


@pytest.mark.asyncio
async def test_apenas_uma_ativa_por_contexto(client: AsyncClient, session, headers_operacional: dict):
    """Ativar uma versão deve desativar as demais do mesmo contexto/tenant."""
    v1 = await _criar_versao(session, versao="v1", ativo=True)
    v2 = await _criar_versao(session, versao="v2", ativo=False)

    resp = await client.patch(f"{BASE_URL}/{v2.id}/ativar", headers=headers_operacional)
    assert resp.status_code == 200

    await session.refresh(v1)
    await session.refresh(v2)
    assert v2.ativo is True
    assert v1.ativo is False  # desativada automaticamente


@pytest.mark.asyncio
async def test_ativar_versao_nao_encontrada(client: AsyncClient, headers_operacional: dict):
    """UUID inexistente deve retornar 404."""
    resp = await client.patch(f"{BASE_URL}/{uuid.uuid4()}/ativar", headers=headers_operacional)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_ativar(client: AsyncClient, session, headers_operacional: dict):
    """Não deve ativar versão de outro tenant."""
    await _garantir_tenant(session, OUTRO_TENANT_ID, "Tenant Outro")
    rec_outro = await _criar_versao(session, tenant_id=OUTRO_TENANT_ID, versao="v1")

    resp = await client.patch(f"{BASE_URL}/{rec_outro.id}/ativar", headers=headers_operacional)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_listar_inclui_versoes_globais(client: AsyncClient, session, headers_operacional: dict):
    """GET deve incluir versões globais (tenant_id=None) na listagem."""
    rec_global = IAPromptVersao(
        id=uuid.uuid4(),
        tenant_id=None,
        contexto="COMPRAS_ESTRATEGIA",
        versao="global-v1",
        conteudo="Prompt global",
        ativo=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec_global)
    await session.commit()

    resp = await client.get(f"{BASE_URL}?contexto=COMPRAS_ESTRATEGIA", headers=headers_operacional)
    assert resp.status_code == 200
    versoes = resp.json()
    globais = [v for v in versoes if v["is_global"] is True]
    assert len(globais) >= 1


# ── Integração com serviço de estratégia ─────────────────────────────────────

@pytest.mark.asyncio
async def test_buscar_prompt_ativo_retorna_tenant_first(session):
    """_buscar_prompt_ativo deve preferir versão do tenant sobre global."""
    from ia.compras_estrategia_service import _buscar_prompt_ativo

    rec_global = IAPromptVersao(
        id=uuid.uuid4(), tenant_id=None, contexto="COMPRAS_ESTRATEGIA",
        versao="global-v1", conteudo="Prompt global ativo", ativo=True,
        created_at=datetime.now(timezone.utc),
    )
    rec_tenant = IAPromptVersao(
        id=uuid.uuid4(), tenant_id=TENANT_ID, contexto="COMPRAS_ESTRATEGIA",
        versao="tenant-v1", conteudo="Prompt tenant ativo", ativo=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec_global)
    session.add(rec_tenant)
    await session.commit()

    resultado = await _buscar_prompt_ativo(session, TENANT_ID)
    assert resultado == "Prompt tenant ativo"


@pytest.mark.asyncio
async def test_buscar_prompt_ativo_fallback_global(session):
    """Sem versão ativa do tenant, deve retornar a global."""
    from ia.compras_estrategia_service import _buscar_prompt_ativo

    await _garantir_tenant(session, uuid.UUID("dddddddd-0000-0000-0000-000000000004"), "Tenant sem versão")
    tenant_sem_versao = uuid.UUID("dddddddd-0000-0000-0000-000000000004")
    rec_global = IAPromptVersao(
        id=uuid.uuid4(), tenant_id=None, contexto="COMPRAS_ESTRATEGIA",
        versao="global-v1", conteudo="Prompt global fallback", ativo=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec_global)
    await session.commit()

    resultado = await _buscar_prompt_ativo(session, tenant_sem_versao)
    assert resultado == "Prompt global fallback"


@pytest.mark.asyncio
async def test_buscar_prompt_ativo_sem_versao_retorna_none(session):
    """Sem nenhuma versão ativa, deve retornar None (fallback hardcoded)."""
    from ia.compras_estrategia_service import _buscar_prompt_ativo

    tenant_novo = uuid.UUID("ffffffff-0000-0000-0000-000000000006")
    await _garantir_tenant(session, tenant_novo, "Tenant novo")
    resultado = await _buscar_prompt_ativo(session, tenant_novo)
    assert resultado is None
