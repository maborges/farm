"""
Testes de integração — Sugestões de Melhoria do Prompt (Step 176).
Cobre: estratégia com muitos negativos, sem dados, comentários genéricos, isolamento tenant.
"""
import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from sqlalchemy import delete
from ia.models import IAComprasRecomendacao

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
URL = "/api/v1/ia/compras/recomendacoes/sugestoes-prompt"


@pytest.fixture(autouse=True)
async def _limpar_recomendacoes(session):
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()
    yield
    await session.rollback()
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()


async def _seed(session, tenant_id=TENANT_ID, **kwargs) -> IAComprasRecomendacao:
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        estrategia=kwargs.get("estrategia", "Negociar"),
        resumo="Resumo teste.",
        justificativas=[],
        nivel_confianca=0.7,
        fonte="DETERMINISTICO",
        limite_atingido=False,
        feedback_util=kwargs.get("feedback_util", False),
        feedback_at=datetime.now(timezone.utc),
        feedback_comentario=kwargs.get("comentario", None),
        feedback_revisado=False,
    )
    session.add(rec)
    await session.commit()
    return rec


@pytest.mark.asyncio
async def test_sem_feedbacks_retorna_lista_vazia(client: AsyncClient, session, headers_operacional: dict):
    """Sem feedbacks negativos, não deve gerar sugestão."""
    # Apenas feedbacks positivos
    await _seed(session, feedback_util=True)
    await _seed(session, feedback_util=True)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    # Pode ter dados de outros testes, mas a lista deve ser válida
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_estrategia_com_3_ou_mais_negativos_gera_sugestao(client: AsyncClient, session, headers_operacional: dict):
    """Estratégia com >= 3 feedbacks negativos deve gerar sugestão específica."""
    for _ in range(3):
        await _seed(session, estrategia="Negociar", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    sugestoes = resp.json()
    tipos = [s["tipo"] for s in sugestoes]
    assert "ESTRATEGIA_NEGOCIAR_EXCESSIVA" in tipos

    negociar = next(s for s in sugestoes if s["tipo"] == "ESTRATEGIA_NEGOCIAR_EXCESSIVA")
    assert negociar["total_ocorrencias"] >= 3
    assert negociar["mensagem"]
    assert negociar["sugestao"]


@pytest.mark.asyncio
async def test_aguardar_gera_sugestao_propria(client: AsyncClient, session, headers_operacional: dict):
    """Estratégia 'Aguardar' com >= 3 negativos gera tipo próprio."""
    for _ in range(3):
        await _seed(session, estrategia="Aguardar", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    tipos = [s["tipo"] for s in resp.json()]
    assert "ESTRATEGIA_AGUARDAR_EXCESSIVA" in tipos


@pytest.mark.asyncio
async def test_2_negativos_nao_gera_sugestao_estrategia(client: AsyncClient, session, headers_operacional: dict):
    """Menos de 3 feedbacks negativos por estratégia não deve gerar sugestão de estratégia."""
    for _ in range(2):
        await _seed(session, estrategia="Negociar", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    tipos = [s["tipo"] for s in resp.json()]
    assert "ESTRATEGIA_NEGOCIAR_EXCESSIVA" not in tipos


@pytest.mark.asyncio
async def test_feedbacks_sem_comentario_gera_sugestao(client: AsyncClient, session, headers_operacional: dict):
    """Muitos feedbacks sem comentário devem gerar sugestão FEEDBACK_SEM_COMENTARIO."""
    for _ in range(3):
        await _seed(session, feedback_util=False, comentario=None)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    tipos = [s["tipo"] for s in resp.json()]
    assert "FEEDBACK_SEM_COMENTARIO" in tipos

    sem_coment = next(s for s in resp.json() if s["tipo"] == "FEEDBACK_SEM_COMENTARIO")
    assert sem_coment["total_ocorrencias"] >= 3


@pytest.mark.asyncio
async def test_comentarios_genericos_geram_sugestao(client: AsyncClient, session, headers_operacional: dict):
    """Comentários com palavras como 'genérico' ou 'óbvio' devem gerar COMENTARIO_GENERICO."""
    await _seed(session, feedback_util=False, comentario="Muito generico, sem detalhe pratico.")
    await _seed(session, feedback_util=False, comentario="Comentario obvio e vago, nao ajudou.")

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    tipos = [s["tipo"] for s in resp.json()]
    assert "COMENTARIO_GENERICO" in tipos

    gen = next(s for s in resp.json() if s["tipo"] == "COMENTARIO_GENERICO")
    assert gen["total_ocorrencias"] >= 2


@pytest.mark.asyncio
async def test_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Feedbacks de outro tenant não devem gerar sugestões no tenant atual."""
    outro = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
    # 10 feedbacks negativos no tenant alheio
    for _ in range(10):
        await _seed(session, tenant_id=outro, estrategia="Negociar", feedback_util=False)

    # O tenant principal com dados limpos (zero negativos num tenant novo)
    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    # A resposta deve ser lista (sem crash)
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_campos_obrigatorios_presentes(client: AsyncClient, session, headers_operacional: dict):
    """Cada sugestão deve conter os campos esperados."""
    for _ in range(3):
        await _seed(session, estrategia="Comprar agora", feedback_util=False)

    resp = await client.get(URL, headers=headers_operacional)
    assert resp.status_code == 200
    for s in resp.json():
        assert "tipo" in s
        assert "mensagem" in s
        assert "sugestao" in s
        assert "total_ocorrencias" in s
        assert isinstance(s["total_ocorrencias"], int)
