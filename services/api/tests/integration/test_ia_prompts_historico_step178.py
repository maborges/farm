"""
Testes de integração — Histórico de versões de prompt (Step 178).
"""
from datetime import datetime, timezone
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from unittest.mock import MagicMock
from datetime import timedelta

from ia.models import IAPromptVersao, IAPromptVersaoHistorico
from core.services.auth_service import AuthService

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
OUTRO_TENANT_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
BASE_URL = "/api/v1/ia/prompts/versoes"


@pytest.fixture(autouse=True)
async def _limpar_prompt_versoes(session):
    await session.execute(delete(IAPromptVersaoHistorico))
    await session.execute(delete(IAPromptVersao))
    await session.commit()
    yield
    await session.execute(delete(IAPromptVersaoHistorico))
    await session.execute(delete(IAPromptVersao))
    await session.commit()


async def _criar_versao(
    session,
    tenant_id=TENANT_ID,
    versao="v1",
    ativo=False,
    contexto="COMPRAS_ESTRATEGIA",
) -> IAPromptVersao:
    rec = IAPromptVersao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contexto=contexto,
        versao=versao,
        conteudo=f"Prompt {versao}",
        ativo=ativo,
        observacao=f"Versão {versao}",
        created_by=USER_ID,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


def _headers_outro_tenant() -> dict:
    claims = {
        "sub": str(USER_ID),
        "tenant_id": str(OUTRO_TENANT_ID),
        "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    token = AuthService(MagicMock()).create_access_token(claims, expires_delta=timedelta(hours=1))
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(OUTRO_TENANT_ID),
        "X-Fazenda-ID": "bbbbbbbb-0000-0000-0000-000000000002",
    }


@pytest.mark.asyncio
async def test_criacao_registra_evento_criada(client: AsyncClient, session, headers_operacional: dict):
    resp = await client.post(
        BASE_URL,
        json={
            "contexto": "COMPRAS_ESTRATEGIA",
            "versao": "v1",
            "conteudo": "Prompt inicial",
            "observacao": "Primeira versão",
        },
        headers=headers_operacional,
    )
    assert resp.status_code == 201
    versao_id = uuid.UUID(resp.json()["id"])

    rows = list((await session.execute(
        select(IAPromptVersaoHistorico).where(IAPromptVersaoHistorico.prompt_versao_id == versao_id)
    )).scalars().all())

    assert len(rows) == 1
    assert rows[0].tipo_evento == "CRIADA"
    assert rows[0].usuario_id == USER_ID
    assert rows[0].valor_anterior is None
    assert rows[0].valor_novo["versao"] == "v1"
    assert rows[0].valor_novo["ativo"] is False


@pytest.mark.asyncio
async def test_ativacao_registra_evento_ativada(client: AsyncClient, session, headers_operacional: dict):
    rec = await _criar_versao(session, versao="v2", ativo=False)

    resp = await client.patch(f"{BASE_URL}/{rec.id}/ativar", headers=headers_operacional)
    assert resp.status_code == 200

    rows = list((await session.execute(
        select(IAPromptVersaoHistorico)
        .where(IAPromptVersaoHistorico.prompt_versao_id == rec.id)
        .order_by(IAPromptVersaoHistorico.created_at.desc())
    )).scalars().all())

    assert rows[0].tipo_evento == "ATIVADA"
    assert rows[0].usuario_id == USER_ID
    assert rows[0].valor_anterior["ativo"] is False
    assert rows[0].valor_novo["ativo"] is True


@pytest.mark.asyncio
async def test_desativacao_automatica_registra_evento_desativada(client: AsyncClient, session, headers_operacional: dict):
    anterior = await _criar_versao(session, versao="v1", ativo=True)
    nova = await _criar_versao(session, versao="v2", ativo=False)

    resp = await client.patch(f"{BASE_URL}/{nova.id}/ativar", headers=headers_operacional)
    assert resp.status_code == 200

    await session.refresh(anterior)
    assert anterior.ativo is False

    rows = list((await session.execute(
        select(IAPromptVersaoHistorico)
        .where(IAPromptVersaoHistorico.prompt_versao_id == anterior.id)
        .order_by(IAPromptVersaoHistorico.created_at.desc())
    )).scalars().all())

    assert rows[0].tipo_evento == "DESATIVADA"
    assert rows[0].usuario_id == USER_ID
    assert rows[0].valor_anterior["ativo"] is True
    assert rows[0].valor_novo["ativo"] is False


@pytest.mark.asyncio
async def test_listagem_historico_respeita_tenant(client: AsyncClient, session, headers_operacional: dict):
    rec = await _criar_versao(session, tenant_id=TENANT_ID, versao="v-isolada", ativo=False)

    session.add(
        IAPromptVersaoHistorico(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            prompt_versao_id=rec.id,
            usuario_id=USER_ID,
            tipo_evento="CRIADA",
            valor_novo={"versao": "v-isolada", "ativo": False},
            created_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()

    headers_outro_tenant = _headers_outro_tenant()
    resp = await client.get(f"{BASE_URL}/{rec.id}/historico", headers=headers_outro_tenant)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_listagem_historico_ordenada_desc(client: AsyncClient, session, headers_operacional: dict):
    rec = await _criar_versao(session, versao="v3", ativo=False)
    antigo = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    recente = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)

    session.add_all([
        IAPromptVersaoHistorico(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            prompt_versao_id=rec.id,
            usuario_id=USER_ID,
            tipo_evento="CRIADA",
            valor_novo={"versao": "v3", "ativo": False},
            created_at=antigo,
        ),
        IAPromptVersaoHistorico(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            prompt_versao_id=rec.id,
            usuario_id=USER_ID,
            tipo_evento="ATIVADA",
            valor_anterior={"ativo": False},
            valor_novo={"ativo": True},
            created_at=recente,
        ),
    ])
    await session.commit()

    resp = await client.get(f"{BASE_URL}/{rec.id}/historico", headers=headers_operacional)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) >= 2
    assert data[0]["tipo_evento"] == "ATIVADA"
    assert data[1]["tipo_evento"] == "CRIADA"
