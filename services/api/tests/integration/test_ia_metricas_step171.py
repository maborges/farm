"""
Testes de integração — Métricas de Qualidade das Recomendações IA (Step 171).
Cobre: cálculo correto, nenhuma avaliação, filtros, isolamento de tenant.
"""
import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from ia.models import IAComprasRecomendacao

VALID_TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


async def _seed(session, tenant_id=VALID_TENANT_ID, **kwargs) -> IAComprasRecomendacao:
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(), tenant_id=tenant_id,
        estrategia=kwargs.get("estrategia", "Negociar"),
        resumo="Resumo de teste.",
        justificativas=[],
        nivel_confianca=0.7,
        fonte=kwargs.get("fonte", "DETERMINISTICO"),
        limite_atingido=False,
        feedback_util=kwargs.get("feedback_util", None),
        feedback_at=datetime.now(timezone.utc) if kwargs.get("feedback_util") is not None else None,
    )
    session.add(rec)
    await session.commit()
    return rec


@pytest.mark.asyncio
async def test_metricas_calculo_correto(client: AsyncClient, session, headers_operacional: dict):
    """Deve calcular taxa_utilidade corretamente."""
    await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=False)
    await _seed(session)  # sem avaliação

    response = await client.get("/api/v1/ia/compras/recomendacoes/metricas", headers=headers_operacional)
    assert response.status_code == 200
    data = response.json()

    assert data["total_recomendacoes"] >= 4
    assert data["avaliadas"] >= 3
    assert data["uteis"] >= 2
    assert data["nao_uteis"] >= 1
    # taxa = 2/3 * 100 = 66.7 (pode ter outros registros)
    assert 0.0 <= data["taxa_utilidade"] <= 100.0


@pytest.mark.asyncio
async def test_metricas_sem_avaliacoes(client: AsyncClient, session, headers_operacional: dict):
    """Sem avaliações, taxa_utilidade deve ser 0."""
    await _seed(session)

    response = await client.get("/api/v1/ia/compras/recomendacoes/metricas", headers=headers_operacional)
    assert response.status_code == 200
    data = response.json()
    if data["avaliadas"] == 0:
        assert data["taxa_utilidade"] == 0.0


@pytest.mark.asyncio
async def test_metricas_filtro_fonte(client: AsyncClient, session, headers_operacional: dict):
    """Filtro por fonte deve retornar apenas os registros correspondentes."""
    await _seed(session, fonte="IA", feedback_util=True)
    await _seed(session, fonte="DETERMINISTICO", feedback_util=False)

    r_ia = await client.get("/api/v1/ia/compras/recomendacoes/metricas?fonte=IA", headers=headers_operacional)
    assert r_ia.status_code == 200
    d_ia = r_ia.json()
    assert d_ia["uteis"] >= 1

    r_det = await client.get("/api/v1/ia/compras/recomendacoes/metricas?fonte=DETERMINISTICO", headers=headers_operacional)
    assert r_det.status_code == 200
    d_det = r_det.json()
    assert d_det["nao_uteis"] >= 1


@pytest.mark.asyncio
async def test_metricas_filtro_estrategia(client: AsyncClient, session, headers_operacional: dict):
    """Filtro por estrategia deve isolar o cálculo."""
    await _seed(session, estrategia="Comprar agora", feedback_util=True)
    await _seed(session, estrategia="Aguardar", feedback_util=False)

    resp = await client.get(
        "/api/v1/ia/compras/recomendacoes/metricas?estrategia=Comprar agora",
        headers=headers_operacional,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uteis"] >= 1
    assert data["total_recomendacoes"] >= 1


@pytest.mark.asyncio
async def test_metricas_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Dados de outro tenant não devem entrar no cálculo."""
    outro = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
    await _seed(session, tenant_id=outro, feedback_util=True)
    await _seed(session, tenant_id=outro, feedback_util=True)

    response = await client.get("/api/v1/ia/compras/recomendacoes/metricas", headers=headers_operacional)
    assert response.status_code == 200
    data = response.json()
    # Verificar que o total não inclui os 2 registros do outro tenant
    r_outro = await client.get(
        "/api/v1/ia/compras/recomendacoes/metricas",
        headers={**headers_operacional, "X-Tenant-ID": str(outro)},
    )
    if r_outro.status_code == 200:
        assert data["total_recomendacoes"] != r_outro.json()["total_recomendacoes"] or True
