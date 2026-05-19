from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FrotaAgriculturaResumo(BaseModel):
    horas_totais: float
    km_totais: float
    custo_estimado_total: float | None = None
    custo_hora_estimado: float | None = None
    custo_km_estimado: float | None = None
    apontamentos_total: int = 0
    hectares_totais: float = 0.0
    quantidade_total: float = 0.0
    custo_apontamentos_total: float | None = None
    produtividade_media_ha_hora: float | None = None
    custo_medio_por_ha: float | None = None
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


class FrotaAgriculturaApontamentoOperacaoItem(BaseModel):
    tipo_operacao: str
    apontamentos: int
    hectares_totais: float
    horas_totais: float
    custo_total: float | None = None
    custo_por_ha: float | None = None
    custo_por_hora: float | None = None
    produtividade_ha_hora: float | None = None


class FrotaAgriculturaApontamentoTalhaoItem(BaseModel):
    talhao_id: UUID | None = None
    talhao_nome: str
    safra_id: UUID | None = None
    safra_nome: str | None = None
    apontamentos: int
    hectares_totais: float
    horas_totais: float
    custo_total: float | None = None
    custo_por_ha: float | None = None
    produtividade_ha_hora: float | None = None


class FrotaAgriculturaApontamentoOperadorItem(BaseModel):
    operador_id: UUID | None = None
    operador_nome: str
    apontamentos: int
    equipamentos_utilizados: int
    horas_totais: float
    hectares_totais: float
    custo_total: float | None = None
    custo_por_ha: float | None = None
    produtividade_ha_hora: float | None = None


class FrotaAgriculturaApontamentoEquipamentoItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    apontamentos: int
    horas_totais: float
    hectares_totais: float
    custo_total: float | None = None
    custo_por_ha: float | None = None
    produtividade_ha_hora: float | None = None


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
    apontamentos_por_operacao: list[FrotaAgriculturaApontamentoOperacaoItem] = Field(default_factory=list)
    apontamentos_por_talhao: list[FrotaAgriculturaApontamentoTalhaoItem] = Field(default_factory=list)
    apontamentos_por_operador: list[FrotaAgriculturaApontamentoOperadorItem] = Field(default_factory=list)
    equipamentos_por_apontamento: list[FrotaAgriculturaApontamentoEquipamentoItem] = Field(default_factory=list)
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
