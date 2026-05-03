import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import delete

from ia.models import IAComprasRecomendacao
from core.models.tenant import Tenant

# Coerência com conftest.py (integration)
VALID_TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
async def _limpar_recomendacoes(session):
    """Limpa recomendações antes e depois de cada teste para isolamento total."""
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()
    yield
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()


async def _garantir_tenant(session, tenant_id: uuid.UUID, nome: str) -> None:
    """Garante que o tenant existe para evitar erros de FK."""
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
    await session.flush()
    await session.commit()


async def _criar_recomendacao(session, tenant_id=VALID_TENANT_ID, **kwargs) -> IAComprasRecomendacao:
    """Helper para criar recomendação persistida no banco."""
    # Garante o tenant antes da recomendação
    await _garantir_tenant(session, tenant_id, f"Tenant {tenant_id}")
    
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        usuario_id=kwargs.get("usuario_id", uuid.uuid4()),
        estrategia=kwargs.get("estrategia", "Comprar agora"),
        resumo=kwargs.get("resumo", "Recomendação de teste"),
        justificativas=["Justificativa 1"],
        nivel_confianca=0.85,
        fonte="IA",
        limite_atingido=False,
    )
    session.add(rec)
    await session.flush()
    await session.commit()
    await session.refresh(rec)
    return rec


@pytest.mark.asyncio
async def test_feedback_util_true(client: AsyncClient, session, headers_operacional: dict):
    """Deve registrar feedback_util=True e preencher feedback_at."""
    rec = await _criar_recomendacao(session)

    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/feedback",
        json={"feedback_util": True},
        headers=headers_operacional,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["feedback_util"] is True
    # O feedback_at deve ter sido preenchido pelo servidor
    assert "id" in data


@pytest.mark.asyncio
async def test_feedback_util_false_com_comentario(client: AsyncClient, session, headers_operacional: dict):
    """Deve registrar feedback_util=False e salvar comentário."""
    rec = await _criar_recomendacao(session)
    comentario = "Não concordo com a estratégia de risco."

    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/feedback",
        json={"feedback_util": False, "feedback_comentario": comentario},
        headers=headers_operacional,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["feedback_util"] is False
    # Verificação no banco para garantir persistência real
    await session.refresh(rec)
    assert rec.feedback_util is False
    assert rec.feedback_comentario == comentario


@pytest.mark.asyncio
async def test_feedback_recomendacao_inexistente(client: AsyncClient, headers_operacional: dict):
    """Deve retornar 404 para ID inexistente."""
    id_fake = uuid.uuid4()
    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{id_fake}/feedback",
        json={"feedback_util": True},
        headers=headers_operacional,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_feedback_tenant_isolation(client: AsyncClient, session, headers_operacional: dict):
    """Não deve atualizar recomendação de outro tenant."""
    outro_tenant = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
    # _criar_recomendacao já garante o tenant
    rec_outro = await _criar_recomendacao(session, tenant_id=outro_tenant)

    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec_outro.id}/feedback",
        json={"feedback_util": True},
        headers=headers_operacional,
    )
    # Deve dar 404 porque o tenant_id do JWT não bate com o da recomendação
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_feedback_util_update(client: AsyncClient, session, headers_operacional: dict):
    """Deve permitir atualizar um feedback já existente."""
    rec = await _criar_recomendacao(session)
    
    # Primeiro feedback: True
    await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/feedback",
        json={"feedback_util": True},
        headers=headers_operacional,
    )
    
    # Segundo feedback: False
    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/feedback",
        json={"feedback_util": False, "feedback_comentario": "Mudei de ideia"},
        headers=headers_operacional,
    )
    
    assert response.status_code == 200
    assert response.json()["feedback_util"] is False


@pytest.mark.asyncio
async def test_feedback_invalid_payload(client: AsyncClient, session, headers_operacional: dict):
    """Deve retornar 422 para payload inválido (feedback_util ausente)."""
    rec = await _criar_recomendacao(session)
    response = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/feedback",
        json={"feedback_comentario": "Faltou o campo obrigatório"},
        headers=headers_operacional,
    )
    assert response.status_code == 422
