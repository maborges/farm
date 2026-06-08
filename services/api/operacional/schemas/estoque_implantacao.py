from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EstoqueImplantacaoPreviewMappingPayload(BaseModel):
    mapeamento: dict[str, str] = Field(default_factory=dict)


class EstoqueImplantacaoPreviewMessage(BaseModel):
    linha: int | None = None
    campo: str | None = None
    codigo: str
    mensagem: str


class EstoqueImplantacaoPreviewItem(BaseModel):
    numero_linha: int
    status: Literal["VALIDA", "AVISO", "ERRO"]
    payload_original: dict[str, Any] = Field(default_factory=dict)
    dados_normalizados: dict[str, Any] = Field(default_factory=dict)
    erros: list[EstoqueImplantacaoPreviewMessage] = Field(default_factory=list)
    avisos: list[EstoqueImplantacaoPreviewMessage] = Field(default_factory=list)
    sugestoes: dict[str, list[str]] = Field(default_factory=dict)


class EstoqueImplantacaoPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    arquivo_nome: str
    extensao: str
    encoding: str | None = None
    delimitador: str | None = None
    estrutura_minima_valida: bool
    colunas_detectadas: list[str] = Field(default_factory=list)
    mapeamento_utilizado: dict[str, str] = Field(default_factory=dict)
    total_linhas: int = 0
    linhas_validas: int = 0
    linhas_com_erro: int = 0
    linhas_com_aviso: int = 0
    produtos_nao_encontrados: list[str] = Field(default_factory=list)
    depositos_nao_encontrados: list[str] = Field(default_factory=list)
    valor_total_estimado: float = 0.0
    itens: list[EstoqueImplantacaoPreviewItem] = Field(default_factory=list)
    erros_arquivo: list[EstoqueImplantacaoPreviewMessage] = Field(default_factory=list)


class EstoqueImplantacaoItemCorrecaoRequest(BaseModel):
    produto_id_resolvido: uuid.UUID | None = None
    deposito_id_resolvido: uuid.UUID | None = None
    quantidade: float | None = None
    custo_unitario: float | None = None
    lote: str | None = None
    validade: date | None = None
    observacoes: str | None = None
    ignorado: bool | None = None


class EstoqueImplantacaoConfirmacaoRequest(BaseModel):
    confirmar_avisos: bool = False
    observacao: str | None = None


class EstoqueImplantacaoItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_linha: int
    status: Literal["VALIDA", "AVISO", "ERRO", "CORRIGIDO", "IGNORADO"]
    ignorado: bool
    payload_original: dict[str, Any] = Field(default_factory=dict)
    dados_normalizados: dict[str, Any] = Field(default_factory=dict)
    produto_id_resolvido: uuid.UUID | None = None
    deposito_id_resolvido: uuid.UUID | None = None
    erros: list[dict[str, Any]] = Field(default_factory=list)
    avisos: list[dict[str, Any]] = Field(default_factory=list)
    sugestoes: dict[str, list[str]] = Field(default_factory=dict)
    criado_em: datetime
    atualizado_em: datetime


class EstoqueImplantacaoSessaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID | None = None
    arquivo_nome: str
    arquivo_hash: str
    status: Literal[
        "RASCUNHO",
        "PREVIEW_GERADO",
        "VALIDADO_COM_ERROS",
        "PRONTO_PARA_CORRECAO",
        "PRONTO_PARA_CONFIRMAR",
        "CANCELADO",
        "CONFIRMADO",
    ]
    mapeamento_colunas: dict[str, str] = Field(default_factory=dict)
    colunas_detectadas: list[str] = Field(default_factory=list)
    total_linhas: int
    linhas_validas: int
    linhas_com_erro: int
    linhas_com_aviso: int
    valor_total_estimado: float
    criado_por: uuid.UUID | None = None
    criado_em: datetime
    atualizado_em: datetime
    cancelado_em: datetime | None = None
    confirmado_em: datetime | None = None
    confirmado_por: uuid.UUID | None = None
    total_itens: int = 0
    limit: int = 100
    offset: int = 0
    itens: list[EstoqueImplantacaoItemResponse] = Field(default_factory=list)


class EstoqueImplantacaoSessaoListResponse(BaseModel):
    itens: list[EstoqueImplantacaoSessaoResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0


class EstoqueImplantacaoItemListResponse(BaseModel):
    itens: list[EstoqueImplantacaoItemResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0


class EstoqueImplantacaoAptidaoConfirmacaoResponse(BaseModel):
    apta: bool
    erros_bloqueantes: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    total_itens_confirmaveis: int = 0
    valor_total_confirmavel: float = 0.0
