"""
Testes de integração — Plano de Melhoria Manual da IA (Step 174).
Cobre: marcar revisado, desmarcar, observação persistida, tenant isolation.
"""
import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from ia.models import IAComprasRecomendacao

VALID_TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


async def _criar_feedback_negativo(session, tenant_id=VALID_TENANT_ID) -> IAComprasRecomendacao:
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        estrategia="Negociar",
        resumo="Recomendação não refletiu o mercado.",
        justificativas=[],
        nivel_confianca=0.7,
        fonte="DETERMINISTICO",
        limite_atingido=False,
        feedback_util=False,
        feedback_at=datetime.now(timezone.utc),
        feedback_comentario="Não foi útil para a decisão.",
        feedback_revisado=False,
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


@pytest.mark.asyncio
async def test_marcar_revisado(client: AsyncClient, session, headers_operacional: dict):
    """Deve marcar feedback como revisado e preencher feedback_revisado_at."""
    rec = await _criar_feedback_negativo(session)

    resp = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/revisao-feedback",
        json={"feedback_revisado": True, "feedback_revisao_observacao": "Ajustar peso do prazo de entrega."},
        headers=headers_operacional,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback_revisado"] is True
    assert data["feedback_revisao_observacao"] == "Ajustar peso do prazo de entrega."
    assert data["feedback_revisado_at"] is not None

    await session.refresh(rec)
    assert rec.feedback_revisado is True
    assert rec.feedback_revisado_at is not None
    assert rec.feedback_revisao_observacao == "Ajustar peso do prazo de entrega."


@pytest.mark.asyncio
async def test_desmarcar_revisado(client: AsyncClient, session, headers_operacional: dict):
    """Deve permitir desmarcar revisão — feedback_revisado_at deve ser limpo."""
    rec = await _criar_feedback_negativo(session)
    rec.feedback_revisado = True
    rec.feedback_revisado_at = datetime.now(timezone.utc)
    session.add(rec)
    await session.commit()

    resp = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/revisao-feedback",
        json={"feedback_revisado": False},
        headers=headers_operacional,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback_revisado"] is False
    assert data["feedback_revisado_at"] is None

    await session.refresh(rec)
    assert rec.feedback_revisado is False
    assert rec.feedback_revisado_at is None


@pytest.mark.asyncio
async def test_observacao_persistida(client: AsyncClient, session, headers_operacional: dict):
    """Observação deve ser salva e devolvida na listagem de feedbacks negativos."""
    rec = await _criar_feedback_negativo(session)

    await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/revisao-feedback",
        json={"feedback_revisado": True, "feedback_revisao_observacao": "Dar mais peso ao histórico."},
        headers=headers_operacional,
    )

    # Verificar via GET feedbacks-negativos
    resp = await client.get("/api/v1/ia/compras/recomendacoes/feedbacks-negativos", headers=headers_operacional)
    assert resp.status_code == 200
    items = resp.json()
    revisado = next((i for i in items if i["id"] == str(rec.id)), None)
    assert revisado is not None
    assert revisado["feedback_revisado"] is True
    assert revisado["feedback_revisao_observacao"] == "Dar mais peso ao histórico."


@pytest.mark.asyncio
async def test_observacao_nula_sem_payload(client: AsyncClient, session, headers_operacional: dict):
    """Sem observação no payload, deve salvar None."""
    rec = await _criar_feedback_negativo(session)

    resp = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec.id}/revisao-feedback",
        json={"feedback_revisado": True},
        headers=headers_operacional,
    )
    assert resp.status_code == 200
    assert resp.json()["feedback_revisao_observacao"] is None


@pytest.mark.asyncio
async def test_nao_encontrado(client: AsyncClient, headers_operacional: dict):
    """UUID inexistente deve retornar 404."""
    resp = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{uuid.uuid4()}/revisao-feedback",
        json={"feedback_revisado": True},
        headers=headers_operacional,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, session, headers_operacional: dict):
    """Não deve atualizar recomendação de outro tenant."""
    outro_tenant = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
    rec_outro = await _criar_feedback_negativo(session, tenant_id=outro_tenant)

    resp = await client.patch(
        f"/api/v1/ia/compras/recomendacoes/{rec_outro.id}/revisao-feedback",
        json={"feedback_revisado": True},
        headers=headers_operacional,
    )
    assert resp.status_code == 404

    # Confirmar que o registro não foi alterado
    await session.refresh(rec_outro)
    assert rec_outro.feedback_revisado is False


@pytest.mark.asyncio
async def test_feedbacks_negativos_retorna_campos_revisao(client: AsyncClient, session, headers_operacional: dict):
    """GET feedbacks-negativos deve incluir campos de revisão."""
    rec = await _criar_feedback_negativo(session)

    resp = await client.get("/api/v1/ia/compras/recomendacoes/feedbacks-negativos", headers=headers_operacional)
    assert resp.status_code == 200
    items = resp.json()
    item = next((i for i in items if i["id"] == str(rec.id)), None)
    assert item is not None
    assert "feedback_revisado" in item
    assert "feedback_revisado_at" in item
    assert "feedback_revisao_observacao" in item
    assert item["feedback_revisado"] is False
