"""Router FastAPI para templates e importação em massa de planilhas da Pecuária."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from core.exceptions import BusinessRuleError, EntityNotFoundError
from pecuaria.schemas.importacao_schema import (
    ImportacaoExecucaoResponse,
    ImportacaoPreviewResponse,
    ModoConflitoImportacao,
    TipoImportacaoPecuaria,
)
from pecuaria.services.importacao_service import ImportacaoPecuariaService, OpcoesImportacao
from pecuaria.services.importacao_templates import gerar_template_planilha
from pecuaria.services.planilha_parser import MAX_UPLOAD_BYTES

router = APIRouter(
    prefix="/pecuaria/importacoes",
    tags=["Pecuária - Importação de Planilhas (P1)"],
    dependencies=[Depends(require_module("P1_REBANHO"))],
)

_CHUNK_BYTES = 64 * 1024
_MAX_MAP_KEYS = 50


async def _ler_upload_com_limite(arquivo: UploadFile) -> tuple[str, bytes]:
    nome_seguro = Path(arquivo.filename or "planilha.xlsx").name
    acumulado = bytearray()
    while True:
        chunk = await arquivo.read(_CHUNK_BYTES)
        if not chunk:
            break
        acumulado.extend(chunk)
        if len(acumulado) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Arquivo excede o limite máximo de 5 MB.",
            )
    if not acumulado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )
    return nome_seguro, bytes(acumulado)


def _parse_mapeamento_json(raw: str | None) -> dict[str, str | None] | None:
    if not raw or not raw.strip():
        return None
    if len(raw) > 8192:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mapeamento de colunas excede o tamanho permitido.",
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato JSON inválido para mapeamento_colunas.",
        ) from exc
    if not isinstance(parsed, dict) or len(parsed) > _MAX_MAP_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estrutura inválida para mapeamento_colunas.",
        )
    resultado: dict[str, str | None] = {}
    for chave, valor in parsed.items():
        if not isinstance(chave, str) or len(chave) > 64:
            raise HTTPException(status_code=400, detail="Chave inválida no mapeamento.")
        if valor is not None and (not isinstance(valor, str) or len(valor) > 120):
            raise HTTPException(status_code=400, detail="Coluna inválida no mapeamento.")
        resultado[chave] = valor
    return resultado


@router.get("/template/{tipo}")
async def baixar_template_planilha(
    tipo: TipoImportacaoPecuaria,
    formato: Literal["xlsx", "csv"] = "xlsx",
    _tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> Response:
    """Disponibiliza modelo .xlsx ou .csv preenchido para importação."""
    conteudo, media_type, filename = gerar_template_planilha(tipo, formato)
    return Response(
        content=conteudo,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.post("/preview", response_model=ImportacaoPreviewResponse)
async def previsualizar_importacao(
    tipo: TipoImportacaoPecuaria = Form(...),
    unidade_produtiva_id: uuid.UUID = Form(...),
    modo_conflito: ModoConflitoImportacao = Form("ATUALIZAR"),
    criar_lotes_automaticamente: bool = Form(True),
    mapeamento_colunas: str | None = Form(None),
    arquivo: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> ImportacaoPreviewResponse:
    """Executa análise dry-run da planilha e devolve linhas classificadas e mapeamento."""
    nome_seguro, conteudo = await _ler_upload_com_limite(arquivo)
    mapeamento = _parse_mapeamento_json(mapeamento_colunas)
    opcoes = OpcoesImportacao(
        tipo=tipo,
        unidade_produtiva_id=unidade_produtiva_id,
        modo_conflito=modo_conflito,
        criar_lotes_automaticamente=criar_lotes_automaticamente,
        mapeamento_colunas=mapeamento,
    )
    service = ImportacaoPecuariaService(db, tenant_id)
    try:
        return await service.previsualizar(opcoes, nome_seguro, conteudo)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha inesperada na pré-visualização da planilha: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível analisar a planilha enviada.",
        ) from exc


@router.post("/executar", response_model=ImportacaoExecucaoResponse)
async def executar_importacao(
    tipo: TipoImportacaoPecuaria = Form(...),
    unidade_produtiva_id: uuid.UUID = Form(...),
    modo_conflito: ModoConflitoImportacao = Form("ATUALIZAR"),
    criar_lotes_automaticamente: bool = Form(True),
    ignorar_linhas_com_erro: bool = Form(False),
    mapeamento_colunas: str | None = Form(None),
    arquivo: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> ImportacaoExecucaoResponse:
    """Persiste lotes, animais ou pesagens validados em transação única."""
    nome_seguro, conteudo = await _ler_upload_com_limite(arquivo)
    mapeamento = _parse_mapeamento_json(mapeamento_colunas)
    opcoes = OpcoesImportacao(
        tipo=tipo,
        unidade_produtiva_id=unidade_produtiva_id,
        modo_conflito=modo_conflito,
        criar_lotes_automaticamente=criar_lotes_automaticamente,
        ignorar_linhas_com_erro=ignorar_linhas_com_erro,
        mapeamento_colunas=mapeamento,
    )
    service = ImportacaoPecuariaService(db, tenant_id)
    try:
        resultado = await service.executar(opcoes, nome_seguro, conteudo)
        await db.commit()
        return resultado
    except EntityNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("Falha inesperada na importação de planilha: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a importação da planilha.",
        ) from exc
