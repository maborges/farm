from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


StatusVencimentoPreventivo = Literal["EM_DIA", "PROXIMO_VENCIMENTO", "VENCIDO"]
TipoRegraPreventiva = Literal["DIAS", "HORAS", "KM", "DIAS_HORAS", "DIAS_KM", "HORAS_KM", "DIAS_HORAS_KM"]


class FrotaPreventivaStatusResumo(BaseModel):
    planos_em_dia: int
    planos_proximos_vencimento: int
    planos_vencidos: int
    os_preventivas_abertas: int


class FrotaPreventivaRegraStatus(BaseModel):
    tipo: Literal["DIAS", "HORAS", "KM"]
    limite: float
    leitura_atual: float | datetime | None = None
    ultimo_registro: float | datetime | None = None
    proxima_execucao: float | datetime | None = None
    restante: float | None = None
    vencido_por: float | None = None
    status: StatusVencimentoPreventivo


class FrotaPreventivaPlanoItem(BaseModel):
    plano_id: UUID
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    unidade_produtiva_id: UUID | None = None
    plano_descricao: str
    tipo_regra: TipoRegraPreventiva
    limite_resumo: str
    leitura_atual_resumo: str
    proxima_execucao_resumo: str
    status: StatusVencimentoPreventivo
    regras: list[FrotaPreventivaRegraStatus]
    os_preventiva_aberta_id: UUID | None = None
    os_preventiva_aberta_numero: str | None = None


class FrotaPreventivaListResponse(BaseModel):
    resumo: FrotaPreventivaStatusResumo
    itens: list[FrotaPreventivaPlanoItem]
    gerado_em: datetime


class FrotaPreventivaEquipamentoResponse(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    planos: list[FrotaPreventivaPlanoItem]
    resumo: FrotaPreventivaStatusResumo
    gerado_em: datetime


class GerarOsPreventivaResponse(BaseModel):
    criada: bool
    ordem_servico_id: UUID
    numero_os: str
    status: str
    tipo: str
    equipamento_id: UUID
    plano_id: UUID
    data_abertura: datetime
    descricao_problema: str
