from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FrotaCustoResumo(BaseModel):
    custo_total_frota: float
    custo_combustivel: float
    custo_manutencao: float
    custo_pecas_itens: float
    custo_documental: float
    custo_medio_por_equipamento: float
    equipamento_mais_caro_nome: str | None = None
    equipamento_mais_caro_total: float | None = None


class FrotaCustoEquipamentoItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    unidade_produtiva_id: UUID | None = None
    equipamento_status: str
    horimetro_atual: float | None = None
    km_atual: float | None = None
    custo_combustivel: float
    custo_manutencao: float
    custo_pecas_itens: float
    custo_documental: float
    custo_total: float
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    participacao_percentual: float | None = None


class FrotaCustoRankingItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    custo_total: float
    participacao_percentual: float | None = None
    custo_por_hora: float | None = None
    custo_por_km: float | None = None


class FrotaCustoHistoricoItem(BaseModel):
    referencia: str
    tipo: str
    valor: float
    data: datetime | None = None


class FrotaCustoAgrupadoSafra(BaseModel):
    safra_id: UUID | None = None
    safra_nome: str | None = None
    custo_total: float
    participacao_percentual: float | None = None


class FrotaCustoAgrupadoTalhao(BaseModel):
    talhao_id: UUID | None = None
    talhao_nome: str | None = None
    custo_total: float
    participacao_percentual: float | None = None


class FrotaCustoAgrupadoOperacao(BaseModel):
    operacao: str
    custo_total: float
    participacao_percentual: float | None = None


class FrotaCustoAgrupadoUP(BaseModel):
    unidade_produtiva_id: UUID | None = None
    unidade_produtiva_nome: str | None = None
    custo_total: float
    participacao_percentual: float | None = None


class FrotaCustoResponse(BaseModel):
    resumo: FrotaCustoResumo
    equipamentos: list[FrotaCustoEquipamentoItem]
    ranking: list[FrotaCustoRankingItem]
    por_safra: list[FrotaCustoAgrupadoSafra] = []
    por_talhao: list[FrotaCustoAgrupadoTalhao] = []
    por_operacao: list[FrotaCustoAgrupadoOperacao] = []
    por_unidade_produtiva: list[FrotaCustoAgrupadoUP] = []
    gerado_em: datetime


class FrotaCustoEquipamentoDetalhe(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    horimetro_atual: float | None = None
    km_atual: float | None = None
    custo_combustivel: float
    custo_manutencao: float
    custo_pecas_itens: float
    custo_documental: float
    custo_total: float
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    participacao_percentual: float | None = None


class FrotaCustoEquipamentoResponse(BaseModel):
    equipamento: FrotaCustoEquipamentoDetalhe
    historico: list[FrotaCustoHistoricoItem]
    gerado_em: datetime


class FrotaCustoRankingResponse(BaseModel):
    ranking: list[FrotaCustoRankingItem]
    gerado_em: datetime
