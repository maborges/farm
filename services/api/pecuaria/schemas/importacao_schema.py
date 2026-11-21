"""Schemas Pydantic para pré-visualização e execução de importações na Pecuária."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TipoImportacaoPecuaria = Literal["LOTES", "ANIMAIS", "PESAGENS"]
ModoConflitoImportacao = Literal["ATUALIZAR", "IGNORAR"]
AcaoLinhaImportacao = Literal["CRIAR", "ATUALIZAR", "IGNORAR", "ERRO"]


class CampoMapeavelInfo(BaseModel):
    """Metadados de um campo aceito no mapeamento da planilha."""

    chave: str
    rotulo: str
    obrigatorio: bool = False
    descricao: str = ""


class LinhaImportacaoPreview(BaseModel):
    """Resultado de validação e classificação de uma linha da planilha."""

    linha_numero: int
    acao: AcaoLinhaImportacao
    identificador: str
    dados: dict[str, object] = Field(default_factory=dict)
    erros: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)


class ImportacaoPreviewResponse(BaseModel):
    """Resumo completo do dry-run de importação com mapeamento detectado."""

    tipo: TipoImportacaoPecuaria
    nome_arquivo: str
    formato: str
    colunas_arquivo: list[str]
    mapeamento_aplicado: dict[str, str | None]
    campos_disponiveis: list[CampoMapeavelInfo]
    total_linhas: int
    validas: int
    a_criar: int
    a_atualizar: int
    a_ignorar: int
    com_erro: int
    avisos_total: int
    preview_linhas: list[LinhaImportacaoPreview] = Field(default_factory=list)
    linhas_erro: list[LinhaImportacaoPreview] = Field(default_factory=list)


class ImportacaoExecucaoResponse(BaseModel):
    """Resultado consolidado após efetivação da importação no banco."""

    tipo: TipoImportacaoPecuaria
    total_linhas: int
    criados: int
    atualizados: int
    ignorados: int
    erros: int
    lotes_criados_automaticamente: int = 0
    lotes_atualizados: int = 0
    avisos_total: int = 0
    linhas_erro: list[LinhaImportacaoPreview] = Field(default_factory=list)
