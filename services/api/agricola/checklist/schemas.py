from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import date, datetime
from typing import Literal, Optional

TipoResultadoChecklist = Literal["TAREFA_CAMPO", "SOLICITACAO_ESTOQUE", "MANUAL"]
StatusVerificacaoChecklist = Literal["PENDENTE", "OK", "OK_PARCIAL", "BLOQUEANTE"]


# --- Templates ---

class ChecklistTemplateCreate(BaseModel):
    cultura: str | None = None
    fase: str
    titulo: str = Field(..., min_length=2, max_length=200)
    descricao: str | None = None
    obrigatorio: bool = False
    ordem: int = 0
    tipo_resultado: TipoResultadoChecklist = "MANUAL"
    produto_id_padrao: Optional[UUID] = None
    quantidade_minima: Optional[float] = Field(None, gt=0)


class ChecklistTemplateUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=2, max_length=200)
    descricao: str | None = None
    obrigatorio: bool | None = None
    ordem: int | None = None
    ativo: bool | None = None
    tipo_resultado: Optional[TipoResultadoChecklist] = None
    produto_id_padrao: Optional[UUID] = None
    quantidade_minima: Optional[float] = Field(None, gt=0)


class ChecklistTemplateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    cultura: str | None
    fase: str
    titulo: str
    descricao: str | None
    obrigatorio: bool
    ordem: int
    ativo: bool
    is_system: bool
    created_at: datetime
    tipo_resultado: TipoResultadoChecklist = "MANUAL"
    produto_id_padrao: Optional[UUID] = None
    quantidade_minima: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# --- Itens por safra ---

class ChecklistItemConcluidoUpdate(BaseModel):
    concluido: Optional[bool] = None
    cancelado: Optional[bool] = None
    motivo_cancelamento: Optional[str] = None


class ChecklistItemAdicionar(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=200)
    descricao: str | None = None
    obrigatorio: bool = False
    ordem: int = 0


class SafraChecklistItemResponse(BaseModel):
    id: UUID
    safra_id: UUID
    template_id: UUID | None
    fase: str
    titulo: str
    descricao: str | None
    obrigatorio: bool
    ordem: int
    concluido: bool
    usuario_id: UUID | None
    concluido_em: datetime | None
    cancelado: bool
    usuario_cancelamento_id: UUID | None
    cancelado_em: datetime | None
    motivo_cancelamento: str | None
    created_at: datetime

    tipo_resultado: TipoResultadoChecklist = "MANUAL"
    operacao_agricola_id: UUID | None = None
    reserva_estoque_id: UUID | None = None
    requisicao_material_id: UUID | None = None
    responsavel_id: UUID | None = None
    prazo_resposta: date | None = None
    status_verificacao: StatusVerificacaoChecklist = "PENDENTE"
    justificativa_ok_parcial: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChecklistItemOverrideRequest(BaseModel):
    """Override manual do veredito — ex.: saldo ainda insuficiente mas o
    pedido de compra já foi providenciado."""
    status_verificacao: Literal["OK", "OK_PARCIAL"]
    justificativa: str = Field(..., min_length=3, max_length=500)


class ChecklistItemAtribuirRequest(BaseModel):
    responsavel_id: UUID
    prazo_resposta: Optional[date] = None


class ChecklistItemGerarOperacaoRequest(BaseModel):
    talhao_id: UUID


class ChecklistFaseStatus(BaseModel):
    fase: str
    total: int
    concluidos: int
    obrigatorios_pendentes: int
    pode_avancar: bool
    veredito: Literal["OK", "OK_PARCIAL", "BLOQUEANTE"] = "OK"
    itens: list[SafraChecklistItemResponse]
