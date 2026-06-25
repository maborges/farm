from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DashboardResumoOperacionalDominioResponse(BaseModel):
    pendentes: int = Field(ge=0)
    em_execucao: int = Field(ge=0)
    atrasadas: int = Field(ge=0)
    concluidas: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class DashboardResumoOperacionalResponse(BaseModel):
    pendentes: int = Field(ge=0)
    em_execucao: int = Field(ge=0)
    atrasadas: int = Field(ge=0)
    concluidas: int = Field(ge=0)
    agricultura: DashboardResumoOperacionalDominioResponse
    pecuaria: DashboardResumoOperacionalDominioResponse

    model_config = ConfigDict(from_attributes=True)

