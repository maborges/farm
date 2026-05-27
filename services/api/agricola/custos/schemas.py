from pydantic import BaseModel, ConfigDict
from uuid import UUID

class CustoBreakdown(BaseModel):
    categoria: str
    valor_total: float
    valor_por_ha: float
    percentual: float

class ReumoCustosSafraResponse(BaseModel):
    safra_id: UUID
    area_total_ha: float
    custo_total_realizado: float
    custo_realizado_por_ha: float
    orcamento_previsto_total: float | None
    desvio_orcamento_pct: float | None
    fonte_orcamento_previsto: str
    usou_fallback_orcamento: bool
    fonte_apuracao: str
    usou_fallback_operacional: bool
    breakdown: list[CustoBreakdown]

    model_config = ConfigDict(from_attributes=True)
