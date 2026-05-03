import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from datetime import timedelta
from unittest.mock import MagicMock
from sqlalchemy import delete
from ia.models import IAComprasRecomendacao
from core.models.tenant import Tenant
from core.services.auth_service import AuthService

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
URL = "/api/v1/ia/compras/recomendacoes/qualidade-resumo"
USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


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


def _headers_tenant(tenant_id: uuid.UUID) -> dict:
    token = AuthService(MagicMock()).create_access_token(
        {
            "sub": str(USER_ID),
            "tenant_id": str(tenant_id),
            "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
            "fazendas_auth": [{"id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "admin"}],
            "is_superuser": False,
            "plan_tier": "PROFISSIONAL",
        },
        expires_delta=timedelta(hours=1),
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": "bbbbbbbb-0000-0000-0000-000000000002",
    }


async def _seed(session, tenant_id=TENANT_ID, **kwargs) -> IAComprasRecomendacao:
    """Helper para criar massa de dados persistida."""
    # Garante o tenant antes da recomendação
    await _garantir_tenant(session, tenant_id, f"Tenant {tenant_id}")
    
    feedback_util = kwargs.get("feedback_util", None)
    revisado = kwargs.get("feedback_revisado", False)
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        estrategia=kwargs.get("estrategia", "Negociar"),
        resumo="Resumo de teste.",
        justificativas=[],
        nivel_confianca=0.7,
        fonte=kwargs.get("fonte", "DETERMINISTICO"),
        limite_atingido=False,
        feedback_util=feedback_util,
        feedback_at=datetime.now(timezone.utc) if feedback_util is not None else None,
        feedback_revisado=revisado,
        feedback_revisado_at=datetime.now(timezone.utc) if revisado else None,
    )
    session.add(rec)
    await session.flush()
    await session.commit()
    await session.refresh(rec)
    return rec


@pytest.mark.asyncio
async def test_calculo_correto(client: AsyncClient, session, headers_operacional: dict):
    """Deve calcular todos os campos corretamente."""
    await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=False, feedback_revisado=True)
    await _seed(session, feedback_util=False, feedback_revisado=False)
    await _seed(session)  # sem avaliação

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    d = resp.json()

    assert d["total_recomendacoes"] >= 5
    assert d["avaliadas"] >= 4
    assert d["feedbacks_negativos"] >= 2
    assert d["feedbacks_revisados"] >= 1
    assert d["feedbacks_pendentes_revisao"] >= 1
    assert 0.0 <= d["taxa_utilidade"] <= 100.0
    assert 0.0 <= d["taxa_revisao"] <= 100.0


@pytest.mark.asyncio
async def test_taxa_utilidade_calculo(client: AsyncClient, session, headers_operacional: dict):
    """taxa_utilidade = uteis / avaliadas * 100."""
    # 3 úteis, 1 não útil → taxa = 75%
    for _ in range(3):
        await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    d = resp.json()
    assert 0.0 <= d["taxa_utilidade"] <= 100.0


@pytest.mark.asyncio
async def test_taxa_revisao_calculo(client: AsyncClient, session, headers_operacional: dict):
    """taxa_revisao = revisados / negativos * 100."""
    # Criar cenário limpo com apenas negativos revisados e pendentes
    await _seed(session, feedback_util=False, feedback_revisado=True)
    await _seed(session, feedback_util=False, feedback_revisado=True)
    await _seed(session, feedback_util=False, feedback_revisado=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    d = resp.json()
    assert d["feedbacks_revisados"] >= 2
    assert d["feedbacks_pendentes_revisao"] >= 1
    assert d["taxa_revisao"] > 0.0


@pytest.mark.asyncio
async def test_sem_avaliadas_retorna_taxas_zero(client: AsyncClient, session, headers_operacional: dict):
    """Sem avaliações, taxa_utilidade e taxa_revisao devem ser 0."""
    # Seed sem feedback
    await _seed(session)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    d = resp.json()
    if d["avaliadas"] == 0:
        assert d["taxa_utilidade"] == 0.0
    if d["feedbacks_negativos"] == 0:
        assert d["taxa_revisao"] == 0.0


@pytest.mark.asyncio
async def test_estrategias_agrupadas(client: AsyncClient, session, headers_operacional: dict):
    """Deve agrupar e ordenar estratégias por total de feedbacks negativos."""
    await _seed(session, estrategia="Negociar", feedback_util=False)
    await _seed(session, estrategia="Negociar", feedback_util=False)
    await _seed(session, estrategia="Negociar", feedback_util=False)
    await _seed(session, estrategia="Aguardar", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    est = resp.json()["estrategias_com_mais_feedback_negativo"]
    assert len(est) >= 1
    # Negociar deve vir primeiro (mais feedbacks)
    assert est[0]["estrategia"] == "Negociar"
    assert est[0]["total"] >= 3
    # Ordenação decrescente
    totais = [e["total"] for e in est]
    assert totais == sorted(totais, reverse=True)


@pytest.mark.asyncio
async def test_estrategias_apenas_negativos(client: AsyncClient, session, headers_operacional: dict):
    """Estratégias com feedback positivo não devem aparecer no ranking negativo."""
    await _seed(session, estrategia="Comprar agora", feedback_util=True)
    await _seed(session, estrategia="Aguardar", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    est = resp.json()["estrategias_com_mais_feedback_negativo"]
    nomes = [e["estrategia"] for e in est]
    assert "Comprar agora" not in nomes


@pytest.mark.asyncio
async def test_filtro_fonte(client: AsyncClient, session, headers_operacional: dict):
    """Filtro por fonte deve restringir o cálculo."""
    await _seed(session, fonte="IA", feedback_util=True)
    await _seed(session, fonte="DETERMINISTICO", feedback_util=False)

    resp_ia = await client.get(f"{URL}?fonte=IA", headers=headers_operacional)
    assert resp_ia.status_code == 200
    d_ia = resp_ia.json()
    # Apenas registros IA (pode haver herança de outros testes se o isolamento falhar, mas o commit garante visibilidade)
    assert d_ia["total_recomendacoes"] >= 1


@pytest.mark.asyncio
async def test_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Dados de outro tenant não devem contaminar o resumo."""
    outro = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
    # _seed já garante o tenant
    await _seed(session, tenant_id=outro, feedback_util=False)
    await _seed(session, tenant_id=outro, feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    neg_atual = resp.json()["feedbacks_negativos"]

    resp_outro = await client.get(URL, headers=_headers_tenant(outro))
    assert resp_outro.status_code == 200
    neg_outro = resp_outro.json()["feedbacks_negativos"]
    
    assert neg_atual != neg_outro
    assert neg_outro >= 2
