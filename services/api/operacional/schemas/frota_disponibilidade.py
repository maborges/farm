from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


StatusOperacionalFrota = Literal[
    "DISPONIVEL",
    "EM_USO",
    "EM_MANUTENCAO",
    "BLOQUEADO",
    "CHECKLIST_PENDENTE",
    "NAO_CONFORME",
    "DOCUMENTO_VENCIDO",
]


class FrotaDisponibilidadeResumo(BaseModel):
    disponiveis: int
    em_uso: int
    em_manutencao: int
    bloqueados: int
    checklist_pendente: int
    nao_conformes: int
    documentos_vencidos: int


class FrotaDisponibilidadeChecklistPendente(BaseModel):
    exige_checklist: bool
    modelo_id: UUID | None = None
    modelo_nome: str | None = None
    ultimo_checklist_id: UUID | None = None
    ultimo_checklist_em: datetime | None = None
    checklist_recente: bool
    motivo: str | None = None


class FrotaDisponibilidadeNaoConformidade(BaseModel):
    ordem: int
    descricao: str
    observacao: str | None = None
    status: Literal["NOK"]


class FrotaDisponibilidadeOsAberta(BaseModel):
    os_id: UUID
    numero_os: str
    tipo: str
    status: str
    data_abertura: datetime


class FrotaDisponibilidadeDocumentoVencido(BaseModel):
    id: UUID
    tipo: str
    descricao: str | None = None
    numero: str | None = None
    data_vencimento: date | None = None


class FrotaDisponibilidadeEquipamentoItem(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    equipamento_status: str
    unidade_produtiva_id: UUID | None = None
    status_operacional: StatusOperacionalFrota
    ultimo_checklist_em: datetime | None = None
    checklist_pendente: bool
    nao_conforme: bool
    bloqueado_manual: bool
    motivo_status: str | None = None
    motivo_bloqueio_manual: str | None = None
    os_aberta: FrotaDisponibilidadeOsAberta | None = None
    documentos_vencidos: list[FrotaDisponibilidadeDocumentoVencido]
    manutencao_preventiva_vencida: bool


class FrotaDisponibilidadeResponse(BaseModel):
    resumo: FrotaDisponibilidadeResumo
    equipamentos: list[FrotaDisponibilidadeEquipamentoItem]
    gerado_em: datetime


class FrotaDisponibilidadeEquipamentoResponse(BaseModel):
    equipamento: FrotaDisponibilidadeEquipamentoItem
    checklist: FrotaDisponibilidadeChecklistPendente
    nao_conformidades: list[FrotaDisponibilidadeNaoConformidade]
    gerado_em: datetime


class FrotaDisponibilidadeBloqueioRequest(BaseModel):
    motivo: str | None = None


class FrotaDisponibilidadeBloqueioResponse(BaseModel):
    equipamento_id: UUID
    equipamento_nome: str
    bloqueado_operacional: bool
    motivo_bloqueio_operacional: str | None = None
    bloqueado_operacional_em: datetime | None = None
    liberado_operacional_em: datetime | None = None
    mensagem: str
