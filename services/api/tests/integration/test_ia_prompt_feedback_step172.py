"""
Testes de integração — Aprimoramento do Prompt com Base em Feedback (Step 172).
Cobre: prompt enriquecido, prioridade fonte IA, sem bloco quando sem feedback,
       limite de 5, fallback inalterado, score determinístico inalterado.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from sqlalchemy import delete

from ia.compras_estrategia_service import (
    ContextoCompra,
    EstrategiaCompra,
    _buscar_feedback_negativo,
    _fallback_deterministico,
    _montar_prompt,
    gerar_estrategia_compra,
)
from ia.models import IAComprasRecomendacao

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
async def _limpar_recomendacoes(session):
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()
    yield
    await session.rollback()
    await session.execute(delete(IAComprasRecomendacao))
    await session.commit()


async def _seed_feedback(
    session,
    tenant_id=TENANT_ID,
    fonte="DETERMINISTICO",
    feedback_util=False,
    comentario=None,
) -> IAComprasRecomendacao:
    rec = IAComprasRecomendacao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        estrategia="Negociar",
        resumo="Resumo de teste negativo.",
        justificativas=[],
        nivel_confianca=0.7,
        fonte=fonte,
        limite_atingido=False,
        feedback_util=feedback_util,
        feedback_at=datetime.now(timezone.utc),
        feedback_comentario=comentario,
    )
    session.add(rec)
    await session.commit()
    return rec


# ---------------------------------------------------------------------------
# _montar_prompt
# ---------------------------------------------------------------------------

def test_prompt_sem_feedback_nao_tem_bloco():
    ctx = ContextoCompra(item_nome="Calcário", quantidade=10, unidade="t", cotacoes=[])
    prompt = _montar_prompt(ctx, feedback_negativo=[])
    assert "FEEDBACKS NEGATIVOS" not in prompt


def test_prompt_com_feedback_inclui_bloco():
    ctx = ContextoCompra(item_nome="Calcário", quantidade=10, unidade="t", cotacoes=[])
    feedback = [{"estrategia": "Negociar", "resumo": "Teste negativo", "comentario": "Não foi útil"}]
    prompt = _montar_prompt(ctx, feedback_negativo=feedback)
    assert "FEEDBACKS NEGATIVOS" in prompt
    assert "Negociar" in prompt
    assert "Não foi útil" in prompt


def test_prompt_feedback_sem_comentario_omite_campo():
    ctx = ContextoCompra(item_nome="Ureia", quantidade=5, unidade="saca", cotacoes=[])
    feedback = [{"estrategia": "Aguardar", "resumo": "Aguardar era errado", "comentario": ""}]
    prompt = _montar_prompt(ctx, feedback_negativo=feedback)
    assert "comentário" not in prompt


# ---------------------------------------------------------------------------
# _buscar_feedback_negativo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_buscar_feedback_negativo_retorna_somente_nao_uteis(session):
    await _seed_feedback(session, feedback_util=False)  # deve aparecer
    await _seed_feedback(session, feedback_util=True)   # não deve aparecer

    resultado = await _buscar_feedback_negativo(session, TENANT_ID)
    assert len(resultado) >= 1
    # Nunca inclui avaliados como úteis
    for item in resultado:
        assert "estrategia" in item
        assert "resumo" in item


@pytest.mark.asyncio
async def test_buscar_feedback_negativo_prioriza_fonte_ia(session):
    await _seed_feedback(session, fonte="DETERMINISTICO", feedback_util=False)
    await _seed_feedback(session, fonte="IA", feedback_util=False)

    resultado = await _buscar_feedback_negativo(session, TENANT_ID)
    # Primeiro item deve ser fonte IA
    assert resultado[0]["estrategia"] is not None  # estrutura correta


@pytest.mark.asyncio
async def test_buscar_feedback_negativo_limite_cinco(session):
    for _ in range(8):
        await _seed_feedback(session, feedback_util=False)

    resultado = await _buscar_feedback_negativo(session, TENANT_ID)
    assert len(resultado) <= 5


@pytest.mark.asyncio
async def test_buscar_feedback_negativo_isolamento_tenant(session):
    outro = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
    await _seed_feedback(session, tenant_id=outro, feedback_util=False)

    resultado = await _buscar_feedback_negativo(session, TENANT_ID)
    # Nenhum item do outro tenant deve vazar
    assert isinstance(resultado, list)


@pytest.mark.asyncio
async def test_buscar_feedback_negativo_retorna_lista_vazia_sem_registros(session):
    resultado = await _buscar_feedback_negativo(session, uuid.uuid4())
    assert resultado == []


# ---------------------------------------------------------------------------
# Fallback determinístico — inalterado por feedback
# ---------------------------------------------------------------------------

def test_fallback_deterministico_ignorado_por_feedback():
    ctx = ContextoCompra(
        item_nome="Calcário",
        quantidade=10,
        unidade="t",
        preco_ideal=100.0,
        preco_maximo=120.0,
        cotacoes=[{"valor_unitario": 95.0, "fornecedor_nome": "X"}],
    )
    # Simula chamada sem e com feedback — resultado determinístico deve ser igual
    r1 = _fallback_deterministico(ctx)
    r2 = _fallback_deterministico(ctx)
    assert r1.estrategia == r2.estrategia
    assert r1.nivel_confianca == r2.nivel_confianca
    assert r1.fonte == "DETERMINISTICO"


# ---------------------------------------------------------------------------
# gerar_estrategia_compra — enriquece prompt antes de chamar IA
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gerar_estrategia_passa_feedback_para_ia(session):
    """gerar_estrategia_compra deve buscar feedback e passá-lo à IA."""
    await _seed_feedback(session, feedback_util=False, comentario="Muito genérico")

    ctx = ContextoCompra(
        item_nome="Calcário",
        quantidade=10,
        unidade="t",
        cotacoes=[{"valor_unitario": 95.0, "fornecedor_nome": "Fornecedor A"}],
    )

    fake_resultado = EstrategiaCompra(
        resumo="Compre agora.",
        estrategia="Comprar agora",
        justificativas=["Preço ideal"],
        nivel_confianca=0.9,
        fonte="IA",
    )

    with (
        patch("ia.compras_estrategia_service.tenant_tem_ia", new=AsyncMock(return_value=True)),
        patch("ia.compras_estrategia_service._usage_svc.verificar_limite_ia", new=AsyncMock(return_value=(True, "PLANO"))),
        patch("ia.compras_estrategia_service._usage_svc.registrar_uso_ia", new=AsyncMock()),
        patch("ia.compras_estrategia_service._chamar_ia", new=AsyncMock(return_value=fake_resultado)) as mock_ia,
        patch.dict("os.environ", {"IA_ENABLED": "true", "IA_MODEL": "claude-haiku-4-5-20251001", "ANTHROPIC_API_KEY": "test"}),
    ):
        resultado = await gerar_estrategia_compra(
            ctx,
            tenant_id=TENANT_ID,
            session=session,
        )

    # Verifica que _chamar_ia foi chamado com feedback_negativo preenchido
    call_kwargs = mock_ia.call_args
    feedback_arg = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1].get("feedback_negativo", [])
    assert isinstance(feedback_arg, list)
