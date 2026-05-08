from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


NivelRiscoFrota = Literal["BAIXO", "MEDIO", "ALTO", "CRITICO"]
TipoMetricaRisco = Literal["HORA", "KM", "INDISPONIVEL"]


class FrotaInteligenciaFator(BaseModel):
    chave: str
    titulo: str
    peso: int
    pontuacao: int
    detalhe: str | None = None


class FrotaInteligenciaEquipamentoItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    unidade_produtiva_id: UUID | None = None
    score_risco: int
    nivel_risco: NivelRiscoFrota
    custo_total: float
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    eficiencia_score: float | None = None
    jornada_aberta: bool = False
    horas_trabalhadas_recentes: float | None = None
    km_trabalhados_recentes: float | None = None
    dias_sem_abastecimento: int | None = None
    os_abertas: int
    os_aberta_antiga: bool = False
    manutencao_status: Literal["OK", "PROXIMA", "VENCIDA", "SEM_PLANO"]
    checklist_status: Literal["OK", "PENDENTE", "NAO_CONFORME", "SEM_EXIGENCIA"]
    documento_vencido: bool = False
    consumo_alerta: bool = False
    custo_alerta: bool = False
    uso_intensivo_alerta: bool = False
    recomendacoes: list[str]
    fatores: list[FrotaInteligenciaFator]


class FrotaInteligenciaRankingItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    valor: float | int | None = None
    score_risco: int | None = None
    nivel_risco: NivelRiscoFrota | None = None
    detalhe: str | None = None


class FrotaInteligenciaResumo(BaseModel):
    total_equipamentos: int
    equipamentos_criticos: int
    equipamentos_alto_risco: int
    equipamentos_medio_risco: int
    equipamentos_baixo_risco: int
    alertas_consolidados: int


class FrotaInteligenciaAcaoDireta(BaseModel):
    label: str
    url: str
    tipo: Literal["LINK", "ACTION"]
    payload: dict | None = None


class FrotaInteligenciaInsight(BaseModel):
    titulo: str
    descricao: str
    impacto_financeiro: float | None = None
    gravidade: Literal["ALTA", "MEDIA", "BAIXA"]
    acao_sugerida: str
    contexto: str
    acao_direta: FrotaInteligenciaAcaoDireta | None = None


class FrotaInteligenciaResponse(BaseModel):
    resumo: FrotaInteligenciaResumo
    equipamentos: list[FrotaInteligenciaEquipamentoItem]
    ranking_risco: list[FrotaInteligenciaRankingItem]
    ranking_mais_caros: list[FrotaInteligenciaRankingItem]
    ranking_menos_eficientes: list[FrotaInteligenciaRankingItem]
    recomendacoes_gerais: list[str]
    insights_financeiros: list[FrotaInteligenciaInsight] = []
    gerado_em: datetime


class FrotaInteligenciaEquipamentoResponse(BaseModel):
    equipamento: FrotaInteligenciaEquipamentoItem
    ranking_risco_posicao: int | None = None
    gerado_em: datetime
