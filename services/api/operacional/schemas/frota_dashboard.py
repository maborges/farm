from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


RiscoOperacionalTipo = Literal[
    "SEM_ABASTECIMENTO_RECENTE",
    "OS_ABERTA_ANTIGA",
    "MANUTENCAO_VENCIDA",
    "DOCUMENTO_VENCIDO",
    "CUSTO_ACIMA_MEDIA",
]


class FrotaDashboardResumo(BaseModel):
    total_equipamentos: int
    ativos: int
    parados: int
    em_uso: int
    em_manutencao: int
    em_risco: int
    os_abertas: int
    manutencoes_vencidas: int
    manutencoes_proximas: int
    documentos_vencidos: int
    custo_total_acumulado: float


class FrotaDashboardUltimoAbastecimento(BaseModel):
    id: UUID
    equipamento_id: UUID
    equipamento_nome: str
    data: datetime
    tipo_combustivel: str
    litros: float
    custo_total: float
    horimetro_na_data: float | None = None
    km_na_data: float | None = None

    model_config = ConfigDict(from_attributes=True)


class FrotaDashboardRankingItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    tipo: str
    status: str
    custo_total: float
    custo_abastecimento: float
    custo_manutencao: float
    os_abertas: int


class FrotaDashboardJornadaItem(BaseModel):
    jornada_id: UUID
    equipamento_id: UUID
    equipamento_nome: str
    operador_nome: str | None = None
    tipo_operacao: str
    data_inicio: datetime
    data_fim: datetime | None = None
    status: Literal["ABERTA", "FINALIZADA", "CANCELADA"]
    duracao_horas: float | None = None
    horas_trabalhadas: float | None = None
    km_trabalhados: float | None = None
    custo_estimado: float | None = None
    metrica_custo: Literal["HORA", "KM", "INDISPONIVEL"] = "INDISPONIVEL"


class FrotaDashboardRiscoItem(BaseModel):
    tipo: RiscoOperacionalTipo
    titulo: str
    severidade: Literal["warning", "danger"]
    equipamento_id: UUID
    equipamento_nome: str
    detalhe: str
    dias_desde_evento: int | None = None
    data_referencia: date | datetime | None = None


class FrotaDashboardEquipamentoItem(BaseModel):
    equipamento_id: UUID
    nome: str
    tipo: str
    status: str
    marca: str | None = None
    modelo: str | None = None
    unidade_produtiva_id: UUID | None = None
    horimetro_atual: float | None = None
    km_atual: float | None = None
    custo_total: float
    custo_abastecimento: float
    custo_manutencao: float
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    jornada_aberta: bool = False
    os_abertas: int
    manutencao_status: Literal["OK", "PROXIMA", "VENCIDA", "SEM_PLANO"]
    documentos_vencidos: int
    ultimo_abastecimento_em: datetime | None = None
    dias_sem_abastecimento: int | None = None
    risco_total: int
    riscos: list[RiscoOperacionalTipo]


class FrotaDashboardResponse(BaseModel):
    resumo: FrotaDashboardResumo
    equipamentos: list[FrotaDashboardEquipamentoItem]
    ranking_maior_custo: list[FrotaDashboardRankingItem]
    alertas_operacionais: list[FrotaDashboardRiscoItem]
    ultimos_abastecimentos: list[FrotaDashboardUltimoAbastecimento]
    ultimas_jornadas: list[FrotaDashboardJornadaItem]
    gerado_em: datetime
