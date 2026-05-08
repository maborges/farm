from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


TipoAlertaConsumo = Literal[
    "CONSUMO_ACIMA_MEDIA",
    "CUSTO_ACIMA_MEDIA",
    "LEITURA_MENOR_ANTERIOR",
    "INTERVALO_CURTO",
    "SEM_ABASTECIMENTO_RECENTE",
    "DESVIO_MEDIA_HISTORICA",
]
TipoMetricaConsumo = Literal["HORIMETRO", "KM", "AMBOS", "INDISPONIVEL"]


class FrotaConsumoResumo(BaseModel):
    litros_totais: float
    custo_total_combustivel: float
    custo_medio_litro: float | None = None
    consumo_medio_l_h: float | None = None
    consumo_medio_km_l: float | None = None
    equipamentos_com_anomalia: int
    total_alertas: int


class FrotaConsumoAlerta(BaseModel):
    tipo: TipoAlertaConsumo
    titulo: str
    severidade: Literal["warning", "danger"]
    equipamento_id: UUID
    equipamento_nome: str
    detalhe: str
    data_referencia: datetime | None = None
    dias_desde_evento: int | None = None


class FrotaConsumoEquipamentoItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    unidade_produtiva_id: UUID | None = None
    total_abastecimentos: int
    litros_totais: float
    custo_total_combustivel: float
    custo_medio_litro: float | None = None
    consumo_medio_l_h: float | None = None
    consumo_medio_km_l: float | None = None
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    variacao_media_frota_percent: float | None = None
    variacao_media_historica_percent: float | None = None
    eficiencia_score: float | None = None
    metrica_principal: TipoMetricaConsumo
    ultimo_abastecimento_em: datetime | None = None
    dias_sem_abastecimento: int | None = None
    alertas_total: int


class FrotaConsumoHistoricoItem(BaseModel):
    id: UUID
    data: datetime
    litros: float
    custo_total: float
    preco_litro: float
    tipo_combustivel: str
    tanque_cheio: bool
    horimetro_na_data: float | None = None
    km_na_data: float | None = None
    local: str
    observacoes: str | None = None


class FrotaConsumoRankingItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    metrica_principal: TipoMetricaConsumo
    eficiencia_score: float | None = None
    consumo_medio_l_h: float | None = None
    consumo_medio_km_l: float | None = None
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    variacao_media_frota_percent: float | None = None


class FrotaConsumoResponse(BaseModel):
    resumo: FrotaConsumoResumo
    equipamentos: list[FrotaConsumoEquipamentoItem]
    ranking_eficiencia: list[FrotaConsumoRankingItem]
    alertas: list[FrotaConsumoAlerta]
    historico_abastecimentos: list[FrotaConsumoHistoricoItem]
    gerado_em: datetime


class FrotaConsumoEquipamentoDetalhe(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    litros_totais: float
    custo_total_combustivel: float
    custo_medio_litro: float | None = None
    consumo_medio_l_h: float | None = None
    consumo_medio_km_l: float | None = None
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    variacao_media_frota_percent: float | None = None
    variacao_media_historica_percent: float | None = None
    eficiencia_score: float | None = None
    metrica_principal: TipoMetricaConsumo
    total_abastecimentos: int
    ultimo_abastecimento_em: datetime | None = None
    dias_sem_abastecimento: int | None = None


class FrotaConsumoEquipamentoResponse(BaseModel):
    equipamento: FrotaConsumoEquipamentoDetalhe
    historico_abastecimentos: list[FrotaConsumoHistoricoItem]
    alertas: list[FrotaConsumoAlerta]
    gerado_em: datetime


class FrotaConsumoRankingResponse(BaseModel):
    ranking: list[FrotaConsumoRankingItem]
    gerado_em: datetime
