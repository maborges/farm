from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertGeneratorResult(BaseModel):
    """Canonical execution result for Alert Engine generators."""

    created: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    ignored: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    warnings: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    generator_name: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)
