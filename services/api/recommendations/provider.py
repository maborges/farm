from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


class RecommendationProvider(ABC):
    """Contract for recommendation providers that emit candidates only."""

    provider_name: ClassVar[str] = "base"
    domains: ClassVar[tuple[str, ...]] = ()

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    @abstractmethod
    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        """Return candidates for the given context without persisting them."""
