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
    "CHECKLIST_FALHA_CRITICA",
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
    disponibilidade_media: float = 100.0
    tempo_parado_manutencao_horas: float = 0.0
    mtbf_medio_horas: float = 0.0
    proporcao_custo_preventivo_percentual: float = 0.0
    custo_operacional_total: float = 0.0
    custo_preventivo_total: float = 0.0
    custo_corretivo_total: float = 0.0
    hectares_totais_apontados: float = 0.0
    custo_por_hectare: float | None = None
    indice_rentabilidade_operacional: float | None = None
    equipamentos_ociosos: int = 0
    equipamentos_falhas_criticas: int = 0
    checklists_pendentes: int = 0
    equipamentos_bloqueados: int = 0



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


class FrotaDashboardOperadorItem(BaseModel):
    operador_id: UUID
    operador_nome: str
    horas_operadas: float
    jornadas: int
    equipamentos_utilizados: int
    tempo_parado_horas: float
    falhas_reportadas: int
    checklists_com_ocorrencia: int
    consumo_operacional: float
    produtividade_operacional: float
    equipamentos_mais_utilizados: list[str] = []


class FrotaDashboardOcorrenciaChecklistItem(BaseModel):
    resposta_id: UUID
    equipamento_id: UUID
    equipamento_nome: str
    criticidade: str | None = None
    observacao: str | None = None
    tipo_jornada: str
    created_at: datetime
    os_gerada_id: UUID | None = None


class FrotaDashboardResponse(BaseModel):
    resumo: FrotaDashboardResumo
    equipamentos: list[FrotaDashboardEquipamentoItem]
    ranking_maior_custo: list[FrotaDashboardRankingItem]
    alertas_operacionais: list[FrotaDashboardRiscoItem]
    ultimos_abastecimentos: list[FrotaDashboardUltimoAbastecimento]
    ultimas_jornadas: list[FrotaDashboardJornadaItem]
    maquinas_ociosas: list[FrotaDashboardEquipamentoItem] = []
    operadores_produtividade: list[FrotaDashboardOperadorItem] = []
    principais_ocorrencias: list[FrotaDashboardOcorrenciaChecklistItem] = []
    gerado_em: datetime
