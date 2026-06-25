from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import Category, Domain

from .context import AlertGeneratorContext
from .result import AlertGeneratorResult


class BaseAlertGenerator(ABC):
    """Official contract for Alert Engine generators."""

    generator_name: ClassVar[str] = "base"
    domain: ClassVar[Domain | None] = None
    category: ClassVar[Category | None] = None
    execution_modes: ClassVar[tuple[str, ...]] = ("scheduled", "hybrid")

    def __init__(self, session: AsyncSession, tenant_id: UUID | None = None) -> None:
        self.session = session
        self.tenant_id = tenant_id

    @abstractmethod
    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute the generator for a single canonical context."""
