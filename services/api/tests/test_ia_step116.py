"""
Step 116 — Testes da camada de IA para resumo consultivo.
Cobre: fallback determinístico, controle por plano, falha da IA, valores preservados.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from ia.insights_service import (
    ContextoSafra,
    ResumoConsultivo,
    gerar_resumo_consultivo,
    _resumo_deterministico,
    tenant_tem_ia,
)


def _ctx(**kwargs) -> ContextoSafra:
    defaults = dict(
        total_custos=50000.0,
        categoria_dominante="insumos",
        margem=-5000.0,
        variacao_mensal_pct=25.0,
        alertas=["Margem negativa detectada"],
        recomendacoes=["Revisar custos de insumos"],
        plano_acoes=["Analisar contratos"],
    )
    defaults.update(kwargs)
    return ContextoSafra(**defaults)


def _mock_session(tier: str | None = None):
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = tier
    session.execute = AsyncMock(return_value=result)
    return session


# ── Fallback determinístico ─────────────────────────────────────────────────

def test_deterministico_sem_custos():
    ctx = _ctx(total_custos=0, categoria_dominante=None, margem=None, variacao_mensal_pct=None)
    result = _resumo_deterministico(ctx)
    assert result.fonte == "DETERMINISTICO"
    assert "Nenhum custo" in result.resumo


def test_deterministico_com_margem_negativa():
    result = _resumo_deterministico(_ctx(margem=-8000.0))
    assert result.fonte == "DETERMINISTICO"
    assert "negativa" in result.resumo
    assert result.nivel_confianca == "ALTO"


def test_deterministico_com_margem_positiva():
    result = _resumo_deterministico(_ctx(margem=12000.0))
    assert "positiva" in result.resumo


def test_deterministico_preserva_valores():
    ctx = _ctx(total_custos=98765.43, margem=None, categoria_dominante=None)
    result = _resumo_deterministico(ctx)
    assert "98.765,43" in result.resumo


def test_deterministico_variacao_positiva():
    result = _resumo_deterministico(_ctx(variacao_mensal_pct=30.0))
    assert "aumentaram" in result.resumo


def test_deterministico_variacao_reducao():
    result = _resumo_deterministico(_ctx(variacao_mensal_pct=-15.0))
    assert "reduziram" in result.resumo


def test_deterministico_recomendacoes_fallback():
    ctx = _ctx(recomendacoes=[])
    result = _resumo_deterministico(ctx)
    assert len(result.recomendacoes) > 0


# ── tenant_tem_ia ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_basico_nao_tem_ia():
    session = _mock_session(tier="BASICO")
    assert await tenant_tem_ia(uuid.uuid4(), session) is False


@pytest.mark.asyncio
async def test_tenant_profissional_tem_ia():
    session = _mock_session(tier="PROFISSIONAL")
    assert await tenant_tem_ia(uuid.uuid4(), session) is True


@pytest.mark.asyncio
async def test_tenant_enterprise_tem_ia():
    session = _mock_session(tier="ENTERPRISE")
    assert await tenant_tem_ia(uuid.uuid4(), session) is True


@pytest.mark.asyncio
async def test_tenant_sem_assinatura_nao_tem_ia():
    session = _mock_session(tier=None)
    assert await tenant_tem_ia(uuid.uuid4(), session) is False


@pytest.mark.asyncio
async def test_tenant_erro_db_nao_tem_ia():
    session = MagicMock()
    session.execute = AsyncMock(side_effect=Exception("DB error"))
    assert await tenant_tem_ia(uuid.uuid4(), session) is False


# ── Controle por plano — sem IA ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plano_basico_usa_fallback_e_ia_indisponivel():
    session = _mock_session(tier="BASICO")
    result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session)
    assert result.fonte == "DETERMINISTICO"
    assert result.ia_disponivel is False


@pytest.mark.asyncio
async def test_sem_session_usa_fallback_sem_ia():
    result = await gerar_resumo_consultivo(_ctx())
    assert result.fonte == "DETERMINISTICO"
    assert result.ia_disponivel is False


# ── Controle por plano — IA disponível mas flag global off ──────────────────

@pytest.mark.asyncio
async def test_profissional_flag_desabilitada_usa_fallback_mas_ia_disponivel():
    session = _mock_session(tier="PROFISSIONAL")
    with patch.dict("os.environ", {"IA_ENABLED": "false"}):
        result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session)
    assert result.fonte == "DETERMINISTICO"
    assert result.ia_disponivel is True  # tem plano, feature desativada globalmente


# ── IA habilitada — sucesso ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profissional_ia_habilitada_retorna_ia():
    ia_result = ResumoConsultivo(
        resumo="Sua safra apresenta custos elevados em insumos.",
        recomendacoes=["Renegociar contratos"],
        nivel_confianca="ALTO",
        fonte="IA",
    )
    session = _mock_session(tier="PROFISSIONAL")
    with patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        with patch("ia.insights_service._chamar_ia", new=AsyncMock(return_value=ia_result)):
            result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session)

    assert result.fonte == "IA"
    assert result.ia_disponivel is True


# ── Falha da IA com plano correto ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_ia_falha_usa_fallback_com_ia_disponivel():
    session = _mock_session(tier="ENTERPRISE")
    with patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        with patch("ia.insights_service._chamar_ia", new=AsyncMock(side_effect=Exception("timeout"))):
            result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session)

    assert result.fonte == "DETERMINISTICO"
    assert result.nivel_confianca == "MEDIO"
    assert result.ia_disponivel is True  # tem plano, IA falhou mas disponível


# ── IA não altera valores financeiros ───────────────────────────────────────

@pytest.mark.asyncio
async def test_ia_nao_altera_valores_calculados():
    ctx = _ctx(total_custos=123456.78, margem=-9999.0)
    ia_result = ResumoConsultivo(
        resumo="Resumo consultivo.", recomendacoes=["Ação 1"],
        nivel_confianca="ALTO", fonte="IA",
    )
    session = _mock_session(tier="PROFISSIONAL")
    with patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        with patch("ia.insights_service._chamar_ia", new=AsyncMock(return_value=ia_result)):
            result = await gerar_resumo_consultivo(ctx, tenant_id=uuid.uuid4(), session=session)

    assert ctx.total_custos == 123456.78
    assert ctx.margem == -9999.0
    assert result.fonte == "IA"
