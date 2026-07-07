from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WizardResumoChecklistPendenteResponse(BaseModel):
    codigo_item: str
    descricao: str
    acao_recomendada: str | None = None
    acao_label: str | None = None
    acao_link: str | None = None
    obrigatorio: bool
    status: str
    severidade: str


class WizardResumoPendenciaCriticaResponse(BaseModel):
    id: uuid.UUID
    titulo: str
    descricao: str
    status: str
    severidade: str


class WizardResumoResponse(BaseModel):
    implantacao_id: uuid.UUID
    status: str
    etapa_atual: str
    percentual_progresso: int
    checklist_minimo_percentual: int
    unidade_produtiva_id: uuid.UUID | None = None
    pendencias_criticas_abertas: int
    checklist_minimo_satisfeito: bool
    elegivel_para_pronto_go_live: bool
    elegivel_para_go_live: bool
    motivos_bloqueio: list[str]
    itens_checklist_faltantes: list[WizardResumoChecklistPendenteResponse]
    pendencias_criticas: list[WizardResumoPendenciaCriticaResponse]


class WizardIniciarRequest(BaseModel):
    unidade_produtiva_id: uuid.UUID | None = None
    modo_implantacao: str = Field(default="ASSISTIDA")
    origem: str = Field(default="NOVO_ASSINANTE")
    escopo_modulos: dict[str, Any] | None = None
    diagnostico_inicial_snapshot: dict[str, Any] | None = None


class WizardActionRequest(BaseModel):
    motivo: str | None = None
    payload_snapshot: dict[str, Any] | None = None


class WizardEtapaResponse(BaseModel):
    id: uuid.UUID
    implantacao_id: uuid.UUID
    codigo_etapa: str
    nome: str
    status: str
    obrigatoria: bool
    ordem: int
    percentual_peso: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    skipped_at: datetime | None = None
    blocked_at: datetime | None = None
    dados_snapshot: dict[str, Any] | None = None
    observacoes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WizardChecklistItemResponse(BaseModel):
    id: uuid.UUID
    implantacao_id: uuid.UUID
    etapa_id: uuid.UUID | None = None
    codigo_item: str
    descricao: str
    acao_recomendada: str | None = None
    acao_label: str | None = None
    acao_link: str | None = None
    obrigatorio: bool
    status: str
    severidade: str
    evidencia_tipo: str
    evidencia_ref_id: str | None = None
    checked_by_usuario_id: uuid.UUID | None = None
    checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WizardChecklistResponse(BaseModel):
    implantacao_id: uuid.UUID
    checklist_minimo_satisfeito: bool
    pendencias_criticas_abertas: int
    itens: list[WizardChecklistItemResponse]


class WizardPendenciaResponse(BaseModel):
    id: uuid.UUID
    implantacao_id: uuid.UUID
    etapa_id: uuid.UUID | None = None
    tipo: str
    severidade: str
    status: str
    titulo: str
    descricao: str
    responsavel_usuario_id: uuid.UUID | None = None
    due_date: date | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
