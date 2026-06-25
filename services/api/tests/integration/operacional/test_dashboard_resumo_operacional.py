from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from core.models import Tenant, TenantUsuario, Usuario
from core.models.unidade_produtiva import UnidadeProdutiva
from core.services.auth_service import AuthService
from campo.models import TarefaCampo
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


async def _garantir_contexto_base(session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session.add(
        Tenant(
            id=tenant_id,
            nome="Tenant Dashboard Operacional",
            documento=str(tenant_id).replace("-", "")[:11],
            ativo=True,
        )
    )
    session.add(
        Usuario(
            id=user_id,
            email=f"operacional-{user_id.hex[:8]}@example.com",
            username=f"operacional_{user_id.hex[:8]}",
            nome_completo="Usuario Operacional",
            senha_hash="hash",
            is_superuser=False,
            ativo=True,
        )
    )
    session.add(UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda Operacional", ativo=True))
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
    await session.flush()
    await garantir_assinatura(session, tenant_id)
    await session.commit()
    return tenant_id, fazenda_id, user_id


async def _criar_tarefa(
    session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    *,
    module: str,
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
            titulo=f"{module} {status_execucao}",
            prioridade="NORMAL",
            type="PLANEJAMENTO",
            module=module,
            data_programada=data_programada,
            unidade_produtiva_id=fazenda_id,
            status=status_execucao,
            dados={},
            fotos=[],
            localizacao_status="INDISPONIVEL",
            client_created_at=datetime.utcnow(),
            client_updated_at=datetime.utcnow(),
        )
    )
    await session.commit()
    return tarefa_id


@pytest.mark.asyncio
async def test_resumo_vazio(client: AsyncClient, session):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE"])

    response = await client.get("/api/v1/operacional/dashboard/resumo-operacional", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "pendentes": 0,
        "em_execucao": 0,
        "atrasadas": 0,
        "concluidas": 0,
        "agricultura": {"pendentes": 0, "em_execucao": 0, "atrasadas": 0, "concluidas": 0},
        "pecuaria": {"pendentes": 0, "em_execucao": 0, "atrasadas": 0, "concluidas": 0},
    }


@pytest.mark.asyncio
async def test_contagem_por_status_e_dominio(client: AsyncClient, session):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE"])

    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="agricola", status_execucao="PENDENTE", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="agricola", status_execucao="EM_EXECUCAO", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="agricola", status_execucao="CONCLUIDA", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="pecuaria", status_execucao="PENDENTE", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="pecuaria", status_execucao="EM_EXECUCAO", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="pecuaria", status_execucao="CONCLUIDA", data_programada=date.today())

    response = await client.get("/api/v1/operacional/dashboard/resumo-operacional", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pendentes"] == 2
    assert data["em_execucao"] == 2
    assert data["concluidas"] == 2
    assert data["atrasadas"] == 0
    assert data["agricultura"] == {"pendentes": 1, "em_execucao": 1, "atrasadas": 0, "concluidas": 1}
    assert data["pecuaria"] == {"pendentes": 1, "em_execucao": 1, "atrasadas": 0, "concluidas": 1}


@pytest.mark.asyncio
async def test_tarefas_atrasadas(client: AsyncClient, session):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE"])

    await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        module="pecuaria",
        status_execucao="PENDENTE",
        data_programada=date.today() - timedelta(days=2),
    )
    await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        module="agricola",
        status_execucao="EM_EXECUCAO",
        data_programada=date.today() - timedelta(days=1),
    )
    await _criar_tarefa(
        session,
        tenant_id,
        user_id,
        fazenda_id,
        module="agricola",
        status_execucao="CONCLUIDA",
        data_programada=date.today() - timedelta(days=5),
    )

    response = await client.get("/api/v1/operacional/dashboard/resumo-operacional", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["atrasadas"] == 2
    assert data["agricultura"]["atrasadas"] == 1
    assert data["pecuaria"]["atrasadas"] == 1


@pytest.mark.asyncio
async def test_ignora_canceladas_e_invalidas(client: AsyncClient, session):
    tenant_id, fazenda_id, user_id = await _garantir_contexto_base(session)
    headers = _gerar_headers(tenant_id, fazenda_id, user_id, ["CORE"])

    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="agricola", status_execucao="CANCELADA", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="pecuaria", status_execucao="INVALIDADA", data_programada=date.today())
    await _criar_tarefa(session, tenant_id, user_id, fazenda_id, module="agricola", status_execucao="PENDENTE", data_programada=date.today())

    response = await client.get("/api/v1/operacional/dashboard/resumo-operacional", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pendentes"] == 1
    assert data["agricultura"]["pendentes"] == 1
    assert data["pecuaria"]["pendentes"] == 0
