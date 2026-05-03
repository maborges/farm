"""Step 121 — Testes: consumo híbrido de IA (plano + créditos extras)"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from ia.usage_service import consultar_uso_hibrido, LIMITES_MENSAIS
from core.constants import PlanTier


TIER_PROF = PlanTier.PROFISSIONAL.value
TIER_ENT = PlanTier.ENTERPRISE.value


def _mock_hibrido(uso_plano: int, extras_disponiveis: int, uso_pacotes: int):
    """Retorna patches para as três funções internas usadas por consultar_uso_hibrido."""
    return (
        patch("ia.usage_service._uso_mensal_plano", return_value=uso_plano),
        patch("ia.usage_service.creditos_extras_ativos", return_value=extras_disponiveis),
        patch("ia.usage_service.creditos_extras_usados", return_value=uso_pacotes),
    )


@pytest.mark.asyncio
async def test_uso_so_plano():
    """Tenant dentro do limite do plano — sem créditos extras usados."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    p1, p2, p3 = _mock_hibrido(uso_plano=30, extras_disponiveis=0, uso_pacotes=0)
    with p1, p2, p3:
        resultado = await consultar_uso_hibrido(tenant_id, TIER_PROF, session)

    assert resultado["uso_plano"] == 30
    assert resultado["uso_pacotes"] == 0
    assert resultado["creditos_extras_disponiveis"] == 0
    assert resultado["usando_creditos_extras"] is False


@pytest.mark.asyncio
async def test_uso_so_pacote():
    """Plano esgotado e créditos extras sendo utilizados."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    limite = LIMITES_MENSAIS[TIER_PROF]  # 100
    p1, p2, p3 = _mock_hibrido(uso_plano=limite, extras_disponiveis=50, uso_pacotes=10)
    with p1, p2, p3:
        resultado = await consultar_uso_hibrido(tenant_id, TIER_PROF, session)

    assert resultado["uso_plano"] == limite
    assert resultado["uso_pacotes"] == 10
    assert resultado["creditos_extras_disponiveis"] == 50
    assert resultado["usando_creditos_extras"] is True


@pytest.mark.asyncio
async def test_uso_misto():
    """Plano parcialmente usado + créditos extras disponíveis mas não esgotados no plano."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    p1, p2, p3 = _mock_hibrido(uso_plano=60, extras_disponiveis=100, uso_pacotes=0)
    with p1, p2, p3:
        resultado = await consultar_uso_hibrido(tenant_id, TIER_PROF, session)

    # Plano ainda não esgotado → não está usando créditos extras
    assert resultado["usando_creditos_extras"] is False
    assert resultado["creditos_extras_disponiveis"] == 100


@pytest.mark.asyncio
async def test_tenant_sem_pacote():
    """Tenant com plano ativo mas zero créditos extras."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    p1, p2, p3 = _mock_hibrido(uso_plano=10, extras_disponiveis=0, uso_pacotes=0)
    with p1, p2, p3:
        resultado = await consultar_uso_hibrido(tenant_id, TIER_PROF, session)

    assert resultado["creditos_extras_disponiveis"] == 0
    assert resultado["usando_creditos_extras"] is False


@pytest.mark.asyncio
async def test_tenant_sem_ia_tier_essencial():
    """Tenant em plano que não tem IA (tier não mapeado) → uso_plano = 0."""
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    # tier ESSENCIAL não está em LIMITES_MENSAIS → limite = None
    p2 = patch("ia.usage_service.creditos_extras_ativos", return_value=0)
    p3 = patch("ia.usage_service.creditos_extras_usados", return_value=0)
    with p2, p3:
        resultado = await consultar_uso_hibrido(tenant_id, "ESSENCIAL", session)

    assert resultado["uso_plano"] == 0
    assert resultado["usando_creditos_extras"] is False
