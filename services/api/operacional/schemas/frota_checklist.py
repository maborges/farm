from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TipoChecklistJornada = Literal["ABERTURA", "ENCERRAMENTO"]
CategoriaChecklistOperacional = Literal["SEGURANCA", "MECANICA", "OPERACIONAL", "DOCUMENTACAO"]
StatusChecklistResposta = Literal["CONFORME", "NAO_CONFORME", "NAO_APLICAVEL"]
CriticidadeChecklist = Literal["BAIXA", "MEDIA", "ALTA", "CRITICA"]


class ChecklistOperacionalItemCreate(BaseModel):
    categoria: CategoriaChecklistOperacional
    descricao: str = Field(min_length=3, max_length=255)
    obrigatorio: bool = True
    ordem: int = 0


class ChecklistOperacionalCreate(BaseModel):
    nome: str = Field(min_length=3, max_length=150)
    tipo_equipamento: str | None = Field(default=None, max_length=30)
    tipo_jornada: TipoChecklistJornada
    exige_antes_operacao: bool = False
    bloqueia_falha_critica: bool = True
    itens: list[ChecklistOperacionalItemCreate] = Field(min_length=1)


class ChecklistOperacionalItemResponse(BaseModel):
    id: UUID
    categoria: str
    descricao: str
    obrigatorio: bool
    ordem: int
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ChecklistOperacionalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nome: str
    tipo_equipamento: str | None
    tipo_jornada: str
    exige_antes_operacao: bool
    bloqueia_falha_critica: bool
    ativo: bool
    itens: list[ChecklistOperacionalItemResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistOperacionalRespostaCreate(BaseModel):
    item_id: UUID
    status: StatusChecklistResposta
    falha: bool = False
    criticidade: CriticidadeChecklist | None = None
    observacao: str | None = Field(default=None, max_length=1000)


class ChecklistOperacionalPreenchimentoCreate(BaseModel):
    checklist_id: UUID | None = None
    equipamento_id: UUID
    operador_id: UUID | None = None
    jornada_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    tipo_jornada: TipoChecklistJornada
    respostas: list[ChecklistOperacionalRespostaCreate] = Field(min_length=1)
    gerar_os: bool = False
    executado_por_id: UUID | None = None
    reportado_por_id: UUID | None = None


class ChecklistOperacionalRespostaResponse(BaseModel):
    id: UUID
    checklist_id: UUID
    item_id: UUID
    equipamento_id: UUID
    jornada_id: UUID | None = None
    operador_id: UUID | None = None
    executado_por_id: UUID | None = None
    reportado_por_id: UUID | None = None
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    tipo_jornada: str
    status: str
    falha: bool
    criticidade: str | None = None
    observacao: str | None = None
    alerta_operacional: bool
    os_gerada_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistOperacionalPreenchimentoResponse(BaseModel):
    checklist_id: UUID
    equipamento_id: UUID
    bloqueou_operacao: bool
    os_gerada_id: UUID | None = None
    respostas: list[ChecklistOperacionalRespostaResponse]
