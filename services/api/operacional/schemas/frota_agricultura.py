from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FrotaAgriculturaResumo(BaseModel):
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    operacao_mais_cara: str | None = None
    operacao_mais_cara_custo: float | None = None
    talhao_mais_caro: str | None = None
    talhao_mais_caro_custo: float | None = None
    equipamento_mais_usado: str | None = None
    equipamento_mais_usado_valor: float | None = None


class FrotaAgriculturaSafraItem(BaseModel):
    safra_id: UUID | None = None
    safra_nome: str
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    total_jornadas: int


class FrotaAgriculturaTalhaoItem(BaseModel):
    talhao_id: UUID | None = None
    talhao_nome: str
    safra_id: UUID | None = None
    safra_nome: str | None = None
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    total_jornadas: int


class FrotaAgriculturaOperacaoItem(BaseModel):
    tipo_operacao: str
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    total_jornadas: int


class FrotaAgriculturaEquipamentoSafraItem(BaseModel):
    safra_id: UUID | None = None
    safra_nome: str
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    total_jornadas: int


class FrotaAgriculturaResponse(BaseModel):
    resumo: FrotaAgriculturaResumo
    por_safra: list[FrotaAgriculturaSafraItem]
    por_talhao: list[FrotaAgriculturaTalhaoItem]
    por_operacao: list[FrotaAgriculturaOperacaoItem]
    equipamentos_por_safra: list[FrotaAgriculturaEquipamentoSafraItem]
    gerado_em: datetime


class FrotaAgriculturaSafraResponse(BaseModel):
    safra_id: UUID
    safra_nome: str
    resumo: FrotaAgriculturaResumo
    por_talhao: list[FrotaAgriculturaTalhaoItem]
    por_operacao: list[FrotaAgriculturaOperacaoItem]
    equipamentos: list[FrotaAgriculturaEquipamentoSafraItem]
    gerado_em: datetime


class FrotaAgriculturaTalhaoResponse(BaseModel):
    talhao_id: UUID
    talhao_nome: str
    resumo: FrotaAgriculturaResumo
    por_operacao: list[FrotaAgriculturaOperacaoItem]
    equipamentos: list[FrotaAgriculturaEquipamentoSafraItem]
    gerado_em: datetime


class FrotaAgriculturaOperacoesResponse(BaseModel):
    resumo: FrotaAgriculturaResumo
    operacoes: list[FrotaAgriculturaOperacaoItem]
    gerado_em: datetime


class FrotaAgriculturaEquipamentoResponse(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    resumo: FrotaAgriculturaResumo
    por_safra: list[FrotaAgriculturaSafraItem]
    por_talhao: list[FrotaAgriculturaTalhaoItem]
    por_operacao: list[FrotaAgriculturaOperacaoItem]
    gerado_em: datetime
