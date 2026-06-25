from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertGeneratorContext(BaseModel):
    """Shared execution context for all Alert Engine generators."""

    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    event_id: UUID | None = None
    batch_id: UUID | None = None
    scope: str | None = None
    reason: str | None = None
    dry_run: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)
