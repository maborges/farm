"""Regras de expiração por inatividade das sessões web."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.configuration import ConfiguracaoSaaS

DEFAULT_SESSION_IDLE_MINUTES = 30


async def get_session_idle_minutes(session: AsyncSession) -> int:
    """Retorna o timeout global de inatividade da sessão, com default seguro."""
    result = await session.execute(
        select(ConfiguracaoSaaS.valor).where(
            ConfiguracaoSaaS.chave == "sessao",
            ConfiguracaoSaaS.ativo.is_(True),
        )
    )
    value = result.scalar_one_or_none()
    minutes = value.get("tempo_inatividade_minutos") if isinstance(value, dict) else None
    return max(1, min(int(minutes), 1440)) if minutes is not None else DEFAULT_SESSION_IDLE_MINUTES


def session_expiration(now, idle_minutes: int):
    """Calcula a data de expiração a partir do último evento de atividade."""
    return now + timedelta(minutes=idle_minutes)
