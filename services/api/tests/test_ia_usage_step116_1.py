"""
Step 116.1 — Testes de controle de uso e custo de IA por tenant.
"""
import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from ia.usage_service import (
    verificar_limite_ia,
    registrar_uso_ia,
    consultar_uso_mensal,
    LIMITES_MENSAIS,
)
from ia.insights_service import (
    ContextoSafra,
    ResumoConsultivo,
    gerar_resumo_consultivo,
    _resumo_deterministico,
)


def _ctx(**kwargs) -> ContextoSafra:
    defaults = dict(
        total_custos=50000.0,
        categoria_dominante="insumos",
        margem=-5000.0,
        variacao_mensal_pct=25.0,
        alertas=[], recomendacoes=["Revisar insumos"], plano_acoes=[],
    )
    defaults.update(kwargs)
    return ContextoSafra(**defaults)


def _session_com_tier(tier: str | None, uso_mensal: int = 0):
    """Mock de sessão que retorna tier e contagem de uso."""
    session = MagicMock()
    calls = [0]

    async def execute_side(stmt):
        result = MagicMock()
        call = calls[0]
        calls[0] += 1
        if call == 0:
            # tenant_tem_ia → PlanoAssinatura.plan_tier
            result.scalar_one_or_none.return_value = tier
        elif call == 1:
            # tier lookup interno em gerar_resumo_consultivo
            result.scalar_one_or_none.return_value = tier
        elif call == 2:
            # verificar_limite_ia → COUNT
            result.scalar_one.return_value = uso_mensal
        else:
            result.scalar_one.return_value = 0
            result.scalar_one_or_none.return_value = None
        return result

    session.execute = execute_side
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ── LIMITES_MENSAIS ──────────────────────────────────────────────────────────

def test_limites_configurados():
    assert LIMITES_MENSAIS["PROFISSIONAL"] == 100
    assert LIMITES_MENSAIS["ENTERPRISE"] == 1000
    assert "BASICO" not in LIMITES_MENSAIS


# ── verificar_limite_ia ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dentro_limite_profissional():
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 50  # 50 de 100
    session.execute = AsyncMock(return_value=result)
    assert await verificar_limite_ia(uuid.uuid4(), "PROFISSIONAL", session) == (True, "PLANO")


@pytest.mark.asyncio
async def test_limite_atingido_profissional():
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 100  # exatamente no limite
    session.execute = AsyncMock(return_value=result)
    with patch("ia.usage_service.creditos_extras_ativos", new=AsyncMock(return_value=0)):
        assert await verificar_limite_ia(uuid.uuid4(), "PROFISSIONAL", session) == (False, "PLANO")


@pytest.mark.asyncio
async def test_enterprise_limite_maior():
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 500  # 500 de 1000
    session.execute = AsyncMock(return_value=result)
    assert await verificar_limite_ia(uuid.uuid4(), "ENTERPRISE", session) == (True, "PLANO")


@pytest.mark.asyncio
async def test_basico_sem_limite_retorna_false():
    session = MagicMock()
    session.execute = AsyncMock()
    assert await verificar_limite_ia(uuid.uuid4(), "BASICO", session) == (False, "PLANO")


# ── registrar_uso_ia ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registrar_uso_sucesso():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    await registrar_uso_ia(
        session, uuid.uuid4(), "resumo_consultivo", "SUCESSO",
        modelo="claude-haiku-4-5-20251001", tokens_entrada=300, tokens_saida=150,
    )
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_registrar_uso_calcula_custo():
    from ia.usage_service import CUSTO_POR_TOKEN_ENTRADA, CUSTO_POR_TOKEN_SAIDA
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    await registrar_uso_ia(session, uuid.uuid4(), "resumo_consultivo", "SUCESSO",
                           tokens_entrada=1000, tokens_saida=500)

    registro = session.add.call_args[0][0]
    esperado = Decimal(1000) * CUSTO_POR_TOKEN_ENTRADA + Decimal(500) * CUSTO_POR_TOKEN_SAIDA
    assert registro.custo_estimado == esperado


@pytest.mark.asyncio
async def test_registrar_uso_nao_quebra_com_erro_db():
    session = MagicMock()
    session.add = MagicMock(side_effect=Exception("DB error"))
    session.flush = AsyncMock()
    # Deve silenciar sem levantar exceção
    await registrar_uso_ia(session, uuid.uuid4(), "resumo_consultivo", "ERRO")


# ── gerar_resumo_consultivo com limites ─────────────────────────────────────

@pytest.mark.asyncio
async def test_plano_basico_nao_registra_uso():
    session = _session_com_tier("BASICO", uso_mensal=0)
    result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session)
    assert result.ia_disponivel is False
    assert result.limite_atingido is False
    # Não deve ter chamado add (não registra uso para BASICO)
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_limite_atingido_usa_fallback_com_flags():
    tid = uuid.uuid4()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    with patch("ia.insights_service.tenant_tem_ia", new=AsyncMock(return_value=True)), \
         patch("ia.usage_service.verificar_limite_ia", new=AsyncMock(return_value=(False, "PLANO"))), \
         patch("ia.usage_service.registrar_uso_ia", new=AsyncMock()), \
         patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        result = await gerar_resumo_consultivo(_ctx(), tenant_id=tid, session=session, tier="PROFISSIONAL")
    assert result.fonte == "DETERMINISTICO"
    assert result.ia_disponivel is True
    assert result.limite_atingido is True


@pytest.mark.asyncio
async def test_dentro_limite_chama_ia_e_registra():
    ia_result = ResumoConsultivo(
        resumo="Resumo IA.", recomendacoes=["Ação"], nivel_confianca="ALTO", fonte="IA",
    )
    registrar_mock = AsyncMock()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    with patch("ia.insights_service.tenant_tem_ia", new=AsyncMock(return_value=True)), \
         patch("ia.usage_service.verificar_limite_ia", new=AsyncMock(return_value=(True, "PLANO"))), \
         patch("ia.usage_service.registrar_uso_ia", new=registrar_mock), \
         patch("ia.insights_service._chamar_ia", new=AsyncMock(return_value=ia_result)), \
         patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session, tier="PROFISSIONAL")

    assert result.fonte == "IA"
    assert result.ia_disponivel is True
    assert result.limite_atingido is False
    registrar_mock.assert_awaited()
    assert registrar_mock.call_args[0][3] == "SUCESSO"


@pytest.mark.asyncio
async def test_ia_erro_registra_status_erro():
    registrar_mock = AsyncMock()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    with patch("ia.insights_service.tenant_tem_ia", new=AsyncMock(return_value=True)), \
         patch("ia.usage_service.verificar_limite_ia", new=AsyncMock(return_value=(True, "PLANO"))), \
         patch("ia.usage_service.registrar_uso_ia", new=registrar_mock), \
         patch("ia.insights_service._chamar_ia", new=AsyncMock(side_effect=Exception("API down"))), \
         patch.dict("os.environ", {"IA_ENABLED": "true", "ANTHROPIC_API_KEY": "sk-test"}):
        result = await gerar_resumo_consultivo(_ctx(), tenant_id=uuid.uuid4(), session=session, tier="ENTERPRISE")

    assert result.fonte == "DETERMINISTICO"
    assert result.ia_disponivel is True
    assert result.limite_atingido is False
    registrar_mock.assert_awaited()
    assert registrar_mock.call_args[0][3] == "ERRO"
