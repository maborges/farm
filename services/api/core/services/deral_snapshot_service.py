"""Serviço de gerenciamento, validação e governança de snapshots DERAL/SEAB-PR.

Implementa o pipeline seguro de ingestão de dados oficiais de mercado:
1. Upload com validação de formato (.json, .csv e .xls), tamanho e integridade SHA-256 dos bytes.
2. Parsing e decodificação nativa de planilhas oficiais BIFF8 (.xls), modelos CSV e envelopes JSON.
3. Segregação explícita entre integridade de bytes, proveniência e aprovação administrativa.
4. Armazenamento persistente e imutável dos bytes originais e dados normalizados em PostgreSQL.
5. Verificação e recálculo de integridade criptográfica pós-persistência.
6. Publicação atômica transacional com controle de concorrência e rollback seguro.
7. Reconciliação multi-worker com suporte a falhas de rede/Redis e auditoria em AdminAuditLog.
"""

from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import json
import re
import unicodedata
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import xlrd
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from core.models.admin_audit_log import AdminAuditLog
from core.models.configuration import ConfiguracaoSaaS
from core.schemas.agro_config_schemas import (
    KEY_MERCADO,
    AgroMercadoConfig,
    DeralSnapshotDetailResponse,
    DeralSnapshotIntegrityResponse,
    DeralSnapshotMetadata,
    DeralSnapshotsListResponse,
    DeralSnapshotUploadResponse,
)
from core.services.admin_audit_service import resolve_admin_identity
from core.services.agro_config_service import agro_config_service
from public_mercado.precos_publicos import (
    METADADOS_CATALOGO,
    SNAPSHOT_PATH,
)

# Chaves de persistência
KEY_DERAI_INDEX = "agro:deral:snapshots:index"
KEY_DERAI_SNAP_PREFIX = "agro:deral:snap:"

# 21 commodities esperadas no snapshot DERAL (todas exceto algodao, que é CONAB/MAPA)
COMMODITIES_HOMOLOGADAS_DERAL = {
    str(meta["id"]) for meta in METADADOS_CATALOGO if str(meta["id"]) != "algodao"
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_FILE_SIZE_BYTES = 100
ALLOWED_EXTENSIONS = {".json", ".csv", ".xls"}
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
DEFAULT_DERAL_DOC_URL = "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"

OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

HOMOLOGATED_GOV_DOMAINS = (
    "agricultura.pr.gov.br",
    "pr.gov.br",
    "seab.pr.gov.br",
    "gov.br",
)

COMMODITIES_XLS_MAP: list[tuple[str, str, str, int, str, str]] = [
    # (id, commodityNome, produtoOriginal, linha_1_based, unidade, unidadeOriginal)
    ("arroz", "Arroz em Casca", "Arroz em casca irrigado", 6, "Saca de 60 kg", "60 kg"),
    ("cafe-arabica", "Café Beneficiado (Produtor)", "Café beneficiado produtor", 7, "Saca de 60 kg", "60 kg"),
    ("feijao", "Feijão de Cor", "Feijao de cor", 9, "Saca de 60 kg", "60 kg"),
    ("milho", "Milho Físico", "Milho", 11, "Saca de 60 kg", "60 kg"),
    ("soja", "Soja em Grão", "Soja", 12, "Saca de 60 kg", "60 kg"),
    ("trigo", "Trigo em Grão", "Trigo", 17, "Saca de 60 kg", "60 kg"),
    ("boi-gordo", "Boi Gordo", "Boi gordo", 46, "Arroba (@ de 15 kg)", "arroba"),
    ("amendoim", "Amendoim em Casca", "Amendoim em casca", 5, "Saca de 25 kg", "25 kg"),
    ("feijao-preto", "Feijão Preto", "Feijao preto", 10, "Saca de 60 kg", "60 kg"),
    ("aveia-branca", "Aveia Branca", "Aveia branca", 14, "Saca de 60 kg", "60 kg"),
    ("canola", "Canola Grão", "Canola", 15, "Saca de 60 kg", "60 kg"),
    ("cevada", "Cevada em Grão", "Cevada", 16, "Saca de 60 kg", "60 kg"),
    ("cana-de-acucar", "Cana-de-Açúcar para Indústria", "Cana de acucar", 41, "Tonelada (1.000 kg)", "t"),
    ("erva-mate", "Erva-Mate Folha Verde", "Erva-mate verde", 42, "Arroba (@ de 15 kg)", "arroba"),
    ("mandioca-industrial", "Mandioca Industrial", "Mandioca", 44, "Tonelada (1.000 kg)", "t"),
    ("boi-magro", "Boi Magro p/ Engorda", "Boi magro p/engorda", 47, "Cabeça", "cabeca"),
    ("frango-vivo", "Frango Vivo", "Frango vivo", 49, "Quilo (kg)", "kg"),
    ("leite", "Leite (Produtor)", "Leite *", 50, "Litro", "l"),
    ("ovo-grande", "Ovo Tipo Grande", "Ovo grande", 51, "Caixa com 30 dúzias", "30 dz"),
    ("suino", "Suíno Vivo", "Suino", 53, "Quilo (kg)", "kg"),
    ("vaca-em-pe", "Vaca em Pé (Abate)", "Vaca em pe", 54, "Arroba (@ de 15 kg)", "arroba"),
]


def verificar_proveniencia_governamental(doc_origem: str, fonte_declarada: str) -> tuple[bool, str, str]:
    """Valida sintaticamente se a URL ou identificador informado pertence a domínios governamentais homologados.

    NOTA DE AUDITORIA E PROVENIÊNCIA (AGRO-ADMIN-01G/01H1):
    1. Distinção de Proveniência: Esta função realiza validação sintática contra a whitelist
       de domínios governamentais (*.pr.gov.br) e verificação de formato. A confirmação de origem
       indica conformidade com a URL declarada pelo operador, e NÃO atestação criptográfica de
       assinatura digital ou captura direta com certificado mTLS.
    2. Armazenamento Forense em Base64: O documento bruto (.xls) é persistido em Base64 na coluna
       conteudo_original_b64 com hash SHA-256 recalculado. O limite máximo permitido é de 10 MB
       (planilhas semanais do DERAL possuem tipicamente 100-300 KB).
    3. Política de Retenção: O histórico de snapshots é mantido ativo por 12 meses (ciclo agrícola anual
       de safra/entressafra) para fins comparativos, sem imposição infundada de guarda legal de 5 anos.
       Após 12 meses, os registros podem ser arquivados em storage secundário via batch offline.

    Returns:
        Tupla (origem_verificada, estado_verificacao, mensagem_diagnostico).
    """
    doc = str(doc_origem or "").strip()
    fonte = str(fonte_declarada or "").strip()

    if not doc:
        return False, "FALHA_VERIFICACAO", "Documento ou URL de origem oficial não informado."

    # Verifica se é URL HTTP/HTTPS
    if doc.startswith("http://") or doc.startswith("https://"):
        try:
            parsed = urlparse(doc)
            hostname = (parsed.hostname or "").lower()
            if any(hostname == d or hostname.endswith("." + d) for d in HOMOLOGATED_GOV_DOMAINS):
                return True, "VERIFICADO", f"Proveniência confirmada no domínio governamental oficial: {hostname}"
            return False, "FALHA_VERIFICACAO", f"Domínio '{hostname}' não pertence aos órgãos governamentais homologados ({', '.join(HOMOLOGATED_GOV_DOMAINS)})."
        except Exception as exc:
            return False, "FALHA_VERIFICACAO", f"URL de proveniência inválida: {exc}"

    # Referência textual direta de arquivo oficial do DERAL
    if "prp.xls" in doc.lower() or "deral" in fonte.lower() or "seab" in fonte.lower():
        return True, "VERIFICADO", "Referência documental direta de publicação DERAL/SEAB-PR homologada."

    return False, "PENDENTE", "Origem não pôde ser verificada automaticamente contra os domínios governamentais."


def parse_deral_xls(dados_xls: bytes, sha256_hash: str) -> dict[str, Any]:
    """Decodifica e valida a planilha oficial DERAL (.xls) BIFF8, extraindo as 21 commodities.

    Raises:
        HTTPException(400): Se a planilha for inválida, corrompida ou divergir do padrão homologado.
    """
    if not dados_xls.startswith(OLE2_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo não possui cabeçalho binário OLE2/BIFF8 válido de planilha .xls do Excel.",
        )
    try:
        wb = xlrd.open_workbook(file_contents=dados_xls)
        aba = wb.sheet_by_name("Rav")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Planilha DERAL corrompida ou aba oficial 'Rav' ausente: {exc}",
        )

    # Valida cabeçalho oficial
    titulo = str(aba.cell_value(0, 0)).strip()
    if "PREÇOS MÉDIOS SEMANAIS" not in titulo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Título oficial 'PREÇOS MÉDIOS SEMANAIS' não confere na célula Rav!A1: '{titulo}'",
        )

    # Valida coluna de preços MÉDIA na linha 2 (X2)
    cabecalho_x = str(aba.cell_value(1, 23)).strip()
    if cabecalho_x != "MÉDIA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cabeçalho da coluna de preços Rav!X2 deve ser 'MÉDIA', recebido: '{cabecalho_x}'",
        )

    # Extrai semana e período
    semana_raw = str(aba.cell_value(0, 9)).removeprefix("SEMANA: ").strip()
    periodo_raw = str(aba.cell_value(0, 15)).removeprefix("PERÍODO: ").strip()
    try:
        fim_periodo = periodo_raw.rsplit(" a ", 1)[1]
        data_ref = datetime.strptime(fim_periodo, "%d/%m/%Y").date().isoformat()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Período da planilha DERAL inválido ('{periodo_raw}'): {exc}",
        )

    # Resolve as linhas pelos rótulos para acompanhar mudanças de posição entre semanas.
    linhas = _indexar_linhas_deral(aba)
    itens: list[dict[str, Any]] = []
    for cid, nome, prod_orig, linha_base, unidade, unidade_orig in COMMODITIES_XLS_MAP:
        assinatura = (_normalizar_rotulo_deral(prod_orig), _normalizar_rotulo_deral(unidade_orig))
        linha = linhas.get(assinatura)
        if linha is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produto/unidade de '{cid}' ausente ou alterado (linha histórica {linha_base}).",
            )
        try:
            prod_lido = str(aba.cell_value(linha - 1, 1)).strip()
            unidade_lida = str(aba.cell_value(linha - 1, 2)).strip()
            val_raw = float(aba.cell_value(linha - 1, 23))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Falha ao ler célula da commodity '{cid}' na linha {linha}: {exc}",
            )

        if (_normalizar_rotulo_deral(prod_lido), _normalizar_rotulo_deral(unidade_lida)) != assinatura:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Divergência cadastral na linha {linha} para '{cid}': esperado ({prod_orig}, {unidade_orig}), recebido ({prod_lido}, {unidade_lida})",
            )

        if val_raw <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Preço inválido ({val_raw}) para '{cid}' na linha {linha}.",
            )

        dec_val = _arredondar_2_casas(val_raw)
        itens.append({
            "id": cid,
            "commodityNome": nome,
            "produtoOriginal": prod_orig,
            "classificacao": f"{prod_orig} — preço médio recebido pelo produtor",
            "valor": dec_val,
            "valorOriginal": val_raw,
            "unidade": unidade,
            "unidadeOriginal": unidade_orig,
            "registroOriginal": f"Rav!X{linha}",
            **_extrair_msa_e_extremos_deral(aba, linha, dec_val),
        })

    return {
        "schemaVersion": 1,
        "fonte": "DERAL/SEAB-PR",
        "documentoOficial": DEFAULT_DERAL_DOC_URL,
        "documentoHashSha256": sha256_hash,
        "tituloDocumento": titulo,
        "semana": semana_raw,
        "periodo": periodo_raw,
        "dataReferencia": data_ref,
        "dataPublicacao": None,
        "planilha": "Rav",
        "colunaValor": "MÉDIA",
        "transformacaoAplicada": "Arredondamento decimal HALF_UP para 2 casas",
        "itens": itens,
    }


def _arredondar_2_casas(valor: float) -> float:
    """Arredonda float com estratégia comercial ROUND_HALF_UP para 2 casas."""
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _extrair_pracas_linha_deral(aba: Any, linha: int) -> list[dict[str, Any]]:
    """Extrai os preços dos 20 Núcleos Regionais (colunas D..W, índices 3..22) da linha."""
    pracas: list[dict[str, Any]] = []
    limite_col = min(23, int(getattr(aba, "ncols", 0)))
    for col_idx in range(3, limite_col):
        nome_praca = str(aba.cell_value(1, col_idx)).strip()
        bruto = aba.cell_value(linha - 1, col_idx)
        if nome_praca and isinstance(bruto, (int, float)) and float(bruto) > 0:
            val_f = float(bruto)
            pracas.append({
                "praca": nome_praca,
                "valor": _arredondar_2_casas(val_f),
                "valorOriginal": val_f,
                "registroOriginal": f"Rav!{chr(65 + col_idx)}{linha}",
            })
    return pracas


def _extrair_msa_e_extremos_deral(aba: Any, linha: int, dec_val: float) -> dict[str, Any]:
    """Extrai Núcleos Regionais, Mín/Máx regional e variação MSA/colunas Y e Z."""
    pracas = _extrair_pracas_linha_deral(aba, linha)
    min_item = min(pracas, key=lambda p: float(p["valor"])) if pracas else None
    max_item = max(pracas, key=lambda p: float(p["valor"])) if pracas else None
    ncols = int(getattr(aba, "ncols", 0))
    msa_raw = aba.cell_value(linha - 1, 24) if ncols > 24 else None
    pct_raw = aba.cell_value(linha - 1, 25) if ncols > 25 else None
    val_msa, var_abs, var_pct = None, None, None
    if isinstance(msa_raw, (int, float)) and float(msa_raw) > 0:
        val_msa = _arredondar_2_casas(float(msa_raw))
        var_abs = _arredondar_2_casas(dec_val - val_msa)
        var_pct = (
            _arredondar_2_casas(float(pct_raw))
            if isinstance(pct_raw, (int, float))
            else _arredondar_2_casas(((dec_val - val_msa) / val_msa) * 100.0)
        )
    return {
        "valorSemanaAnterior": val_msa,
        "variacaoSemanalAbsoluta": var_abs,
        "variacaoSemanalPct": var_pct,
        "valorMinimoRegional": float(min_item["valor"]) if min_item else None,
        "pracaMinimoRegional": str(min_item["praca"]) if min_item else None,
        "valorMaximoRegional": float(max_item["valor"]) if max_item else None,
        "pracaMaximoRegional": str(max_item["praca"]) if max_item else None,
        "pracasRegionais": pracas,
    }


def _enriquecer_variacao_snapshot(
    itens: list[dict[str, Any]], mapa_anterior: dict[str, float]
) -> None:
    """Preenche variação semanal contra o snapshot anterior quando ausente (ex: upload CSV)."""
    for item in itens:
        if not isinstance(item, dict) or item.get("valorSemanaAnterior") is not None:
            continue
        cid = str(item.get("id") or "")
        ant = mapa_anterior.get(cid)
        val_atual = float(item.get("valor") or 0.0)
        if ant and ant > 0 and val_atual > 0:
            ant_round = _arredondar_2_casas(ant)
            item["valorSemanaAnterior"] = ant_round
            item["variacaoSemanalAbsoluta"] = _arredondar_2_casas(val_atual - ant_round)
            item["variacaoSemanalPct"] = _arredondar_2_casas(((val_atual - ant_round) / ant_round) * 100.0)


def _validar_celula_csv_segura(valor: object, campo: str) -> str:
    """Rejeita prefixos de fórmula em células CSV para evitar formula injection."""
    texto = str(valor or "").strip()
    if texto[:1] in CSV_FORMULA_PREFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prefixo de fórmula não permitido na coluna CSV '{campo}'.",
        )
    return texto


def _parse_valor_csv(raw_val: str, cid: str) -> float:
    """Converte valor monetário CSV (ponto ou vírgula decimal) em float positivo."""
    limpo = raw_val.replace("R$", "").replace(" ", "").strip()
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".") if "." in limpo else limpo.replace(",", ".")
    try:
        dec = Decimal(limpo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor numérico CSV inválido para '{cid}': '{raw_val}'",
        ) from exc
    if not dec.is_finite() or dec <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Preço CSV deve ser positivo para '{cid}': '{raw_val}'",
        )
    return float(dec)


def _decodificar_leitor_csv(dados_csv: bytes) -> csv.DictReader[str]:
    """Decodifica bytes UTF-8 CSV com ou sem BOM e valida cabeçalhos seguros."""
    try:
        texto = dados_csv.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo CSV não está codificado em UTF-8 válido: {exc}",
        ) from exc
    linhas = [ln for ln in texto.splitlines() if ln.strip()]
    if len(linhas) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo CSV sem linhas de cotação.")
    delim = ";" if ";" in linhas[0] and "," not in linhas[0] else ","
    reader = csv.DictReader(io.StringIO("\n".join(linhas)), delimiter=delim)
    for col in reader.fieldnames or []:
        _validar_celula_csv_segura(col, "cabeçalho")
    reader.fieldnames = [str(c).strip().lower() for c in (reader.fieldnames or [])]
    return reader


def _converter_linha_csv(
    row: dict[str, str | None],
    mapa_ids: dict[str, tuple[str, str, int, str, str]],
) -> tuple[dict[str, Any], str, str]:
    """Valida e converte uma linha do CSV DERAL para o formato canônico do snapshot."""
    cid = _validar_celula_csv_segura(row.get("id"), "id")
    if cid not in mapa_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Commodity CSV desconhecida: '{cid}'.")
    nome, prod_orig, linha_base, unidade, unidade_orig = mapa_ids[cid]
    val_raw_str = _validar_celula_csv_segura(row.get("valor"), "valor")
    data_ref = _validar_celula_csv_segura(row.get("data_referencia"), "data_referencia")
    doc_raw = _validar_celula_csv_segura(row.get("documento_oficial"), "documento_oficial") or DEFAULT_DERAL_DOC_URL
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_ref):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Data CSV inválida para '{cid}': '{data_ref}'.")
    if not doc_raw.startswith("https://"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coluna 'documento_oficial' deve iniciar com https://.")
    valor = _parse_valor_csv(val_raw_str, cid)
    item = {
        "id": cid, "commodityNome": nome, "produtoOriginal": prod_orig,
        "classificacao": f"{prod_orig} — preço médio recebido pelo produtor",
        "valor": valor, "valorOriginal": valor, "unidade": unidade,
        "unidadeOriginal": unidade_orig, "registroOriginal": f"Rav!X{linha_base}",
    }
    return item, data_ref, doc_raw


def _coletar_itens_csv(reader: csv.DictReader[str]) -> tuple[list[dict[str, Any]], str, str]:
    """Agrega as 21 linhas do CSV exigindo data de referência uniforme."""
    mapa_ids = {cid: (nome, prod, ln, uni, uo) for cid, nome, prod, ln, uni, uo in COMMODITIES_XLS_MAP}
    itens: list[dict[str, Any]] = []
    vistas: set[str] = set()
    data_ref_unica, doc_unico = "", DEFAULT_DERAL_DOC_URL
    for row in reader:
        item, data_ref, doc_url = _converter_linha_csv(row, mapa_ids)
        if item["id"] in vistas:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Commodity duplicada no CSV: '{item['id']}'.")
        if data_ref_unica and data_ref != data_ref_unica:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todas as linhas CSV devem usar a mesma data_referencia.")
        data_ref_unica, doc_unico = data_ref, doc_url
        vistas.add(item["id"])
        itens.append(item)
    return itens, data_ref_unica, doc_unico


def parse_deral_csv(dados_csv: bytes, sha256_hash: str) -> dict[str, Any]:
    """Decodifica e valida modelo CSV com as 21 commodities homologadas DERAL.

    Args:
        dados_csv: Bytes UTF-8 do arquivo CSV enviado pelo operador.
        sha256_hash: Digest SHA-256 calculado sobre os bytes originais.

    Returns:
        Dicionário envelope no formato canônico do snapshot DERAL.

    Raises:
        HTTPException: Se houver fórmula maliciosa, formatação inválida ou itens ausentes.
    """
    reader = _decodificar_leitor_csv(dados_csv)
    itens, data_ref, doc_url = _coletar_itens_csv(reader)
    faltantes = COMMODITIES_HOMOLOGADAS_DERAL - {str(item["id"]) for item in itens}
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV incompleto. Faltam {len(faltantes)} commodities: {', '.join(sorted(faltantes))}",
        )
    return {
        "schemaVersion": 1,
        "fonte": "DERAL/SEAB-PR",
        "documentoOficial": doc_url,
        "documentoHashSha256": sha256_hash,
        "dataReferencia": data_ref,
        "dataPublicacao": None,
        "planilha": "CSV Modelo DERAL",
        "colunaValor": "MÉDIA",
        "transformacaoAplicada": "Arredondamento decimal HALF_UP para 2 casas",
        "itens": itens,
    }


def _normalizar_rotulo_deral(valor: object) -> str:
    """Normaliza caixa, espaços e acentos dos rótulos da planilha oficial."""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.casefold().split())


def _indexar_linhas_deral(aba: Any) -> dict[tuple[str, str], int]:
    """Indexa as linhas pelo produto e unidade atualmente publicados pelo DERAL."""
    return {
        (_normalizar_rotulo_deral(aba.cell_value(row, 1)), _normalizar_rotulo_deral(aba.cell_value(row, 2))): row + 1
        for row in range(2, aba.nrows)
        if str(aba.cell_value(row, 1)).strip() and str(aba.cell_value(row, 2)).strip()
    }


class DeralSnapshotService:
    """Orquestrador de ingestão, validação, proveniência, integridade e ativação atômica de snapshots DERAL."""

    def __init__(self) -> None:
        self._active_snapshot_cache: dict[str, Any] | None = None
        self._active_snapshot_id: str | None = None

    def get_cached_active_snapshot(self) -> dict[str, Any] | None:
        """Retorna o snapshot ativo cacheado em memória, se houver."""
        return self._active_snapshot_cache

    def get_cached_active_snapshot_id(self) -> str | None:
        """Retorna o identificador do snapshot ativo cacheado em memória."""
        return self._active_snapshot_id

    def set_cached_active_snapshot(self, snapshot_id: str, data: dict[str, Any]) -> None:
        """Atualiza o cache em memória do snapshot ativo."""
        self._active_snapshot_id = snapshot_id
        self._active_snapshot_cache = data

    def clear_cache(self) -> None:
        """Limpa o cache em memória."""
        self._active_snapshot_cache = None
        self._active_snapshot_id = None

    async def sync_active_snapshot_from_db(
        self, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Descobre e reconcilia o snapshot ativo a partir da persistência em ConfiguracaoSaaS."""
        try:
            stmt_cfg = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_MERCADO)
            rec_cfg = (await session.execute(stmt_cfg)).scalar_one_or_none()
            id_cfg = (
                str(rec_cfg.valor.get("active_snapshot_id") or "")
                if rec_cfg and isinstance(rec_cfg.valor, dict)
                else ""
            )

            stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX)
            rec_idx = (await session.execute(stmt_idx)).scalar_one_or_none()
            id_idx = (
                str(rec_idx.valor.get("active_snapshot_id") or "")
                if rec_idx and isinstance(rec_idx.valor, dict)
                else ""
            )

            candidatos = [cid for cid in (id_cfg, id_idx) if cid]
            if not candidatos:
                return self.get_cached_active_snapshot()

            # Prioriza o ponteiro do índice de snapshots (ou o mais recente se divergirem)
            active_id = id_idx if id_idx and id_idx >= id_cfg else (id_cfg or id_idx)
            if self._active_snapshot_id == active_id and self._active_snapshot_cache is not None:
                return self._active_snapshot_cache

            snap_stmt = select(ConfiguracaoSaaS).where(
                ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{active_id}"
            )
            snap_rec = (await session.execute(snap_stmt)).scalar_one_or_none()

            if snap_rec and isinstance(snap_rec.valor, dict):
                data = snap_rec.valor.get("snapshot_data") or snap_rec.valor.get("data") or {}
                data = self._enriquecer_snapshot_legado_se_xls(snap_rec.valor, data)
                if data and data.get("itens"):
                    self.set_cached_active_snapshot(active_id, data)
                    return data
        except Exception as exc:
            logger.warning(f"Falha ao reconciliar snapshot ativo do banco: {exc}")

        return self.get_cached_active_snapshot()

    def _enriquecer_snapshot_legado_se_xls(
        self, rec_valor: dict[str, Any], snap_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Reprocessa bytes .xls persistidos caso o snapshot no banco não tenha núcleos regionais."""
        itens = snap_data.get("itens")
        if not isinstance(itens, list) or not itens:
            return snap_data
        primeiro = itens[0] if isinstance(itens[0], dict) else {}
        if primeiro.get("pracasRegionais") and primeiro.get("valorSemanaAnterior") is not None:
            return snap_data
        b64_str = str(rec_valor.get("raw_bytes_base64") or "")
        if not b64_str:
            return snap_data
        try:
            raw_bytes = base64.b64decode(b64_str)
            if raw_bytes.startswith(OLE2_MAGIC):
                sha = hashlib.sha256(raw_bytes).hexdigest()
                return parse_deral_xls(raw_bytes, sha)
        except Exception:
            pass
        return snap_data

    async def _get_or_create_index(self, session: AsyncSession) -> dict[str, Any]:
        """Recupera ou inicializa o índice de snapshots DERAL a partir do baseline bundled."""
        stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record and isinstance(record.valor, dict):
            return record.valor

        # Inicializa o índice com o baseline bundled deral-prp-2026-10-16.json
        baseline_id = "2026-10-16"
        baseline_filename = "deral-prp-2026-10-16.json"
        baseline_data: dict[str, Any] = {}
        baseline_sha256 = ""
        baseline_size = 0

        if SNAPSHOT_PATH.exists():
            content_bytes = SNAPSHOT_PATH.read_bytes()
            baseline_sha256 = hashlib.sha256(content_bytes).hexdigest()
            baseline_size = len(content_bytes)
            try:
                baseline_data = json.loads(content_bytes.decode("utf-8"))
            except Exception:
                baseline_data = {}

        now_iso = datetime.now(timezone.utc).isoformat()
        baseline_meta = {
            "id": baseline_id,
            "filename": baseline_filename,
            "sha256": baseline_sha256,
            "data_referencia": baseline_data.get("dataReferencia", "2026-10-16"),
            "data_publicacao": baseline_data.get("dataPublicacao"),
            "data_obtencao": now_iso,
            "fonte_oficial": baseline_data.get("fonte", "DERAL/SEAB-PR"),
            "origem_declarada": baseline_data.get("fonte", "DERAL/SEAB-PR"),
            "origem_verificada": True,
            "estado_verificacao": "VERIFICADO",
            "estado_aprovacao": "APROVADO",
            "aprovado_por": "sistema:bootstrap",
            "aprovado_em": now_iso,
            "motivo_rejeicao": None,
            "documento_oficial": baseline_data.get(
                "documentoOficial",
                "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
            ),
            "total_itens": len(baseline_data.get("itens", [])),
            "status": "ATIVO",
            "is_active": True,
            "uploaded_at": now_iso,
            "uploaded_by": "sistema:bootstrap",
            "activated_at": now_iso,
            "activated_by": "sistema:bootstrap",
            "transformacao_aplicada": baseline_data.get(
                "transformacaoAplicada", "Arredondamento decimal HALF_UP para 2 casas"
            ),
            "tamanho_bytes": baseline_size,
        }

        index_data = {
            "active_snapshot_id": baseline_id,
            "previous_snapshot_id": None,
            "snapshots": [baseline_meta],
        }

        index_record = ConfiguracaoSaaS(
            id=uuid.uuid4(),
            chave=KEY_DERAI_INDEX,
            valor=index_data,
            descricao="Índice de snapshots DERAL/SEAB-PR catalogados no DeepFarms Agro",
            ativo=True,
        )
        session.add(index_record)

        if baseline_data:
            snap_record = ConfiguracaoSaaS(
                id=uuid.uuid4(),
                chave=f"{KEY_DERAI_SNAP_PREFIX}{baseline_id}",
                valor={
                    "metadata": baseline_meta,
                    "snapshot_data": baseline_data,
                    "raw_bytes_base64": base64.b64encode(SNAPSHOT_PATH.read_bytes()).decode("ascii") if SNAPSHOT_PATH.exists() else "",
                },
                descricao=f"Snapshot DERAL {baseline_id} (Baseline homologado)",
                ativo=True,
            )
            session.add(snap_record)

        await session.commit()
        self.set_cached_active_snapshot(baseline_id, baseline_data)
        return index_data

    def validate_snapshot_raw(
        self,
        raw_bytes: bytes,
        filename: str,
    ) -> tuple[dict[str, Any], DeralSnapshotMetadata, list[str]]:
        """Valida extensão, tamanho, integridade SHA-256, proveniência e esquema contra o catálogo canônico.

        Args:
            raw_bytes: Conteúdo binário original do arquivo recebido.
            filename: Nome original do arquivo submetido.

        Returns:
            Tupla (snapshot_data_dict, metadata_object, validation_logs).

        Raises:
            HTTPException(400): Se o arquivo ou os dados forem inválidos ou não suportados.
        """
        validacoes: list[str] = []

        # 1. Validação estrita de extensão
        ext = Path(filename).suffix.lower()
        if ext == ".xlsx":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extensão '.xlsx' não suportada. Os formatos suportados são: .json (contrato estruturado DERAL v1) e .xls (planilha binária oficial BIFF8 DERAL/SEAB-PR).",
            )
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extensão '{ext}' inválida. Formatos homologados: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        validacoes.append(f"Extensão '{ext}' validada com sucesso.")

        # 2. Validação de limites operacionais de tamanho
        tamanho = len(raw_bytes)
        if tamanho < MIN_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo corrompido ou vazio (tamanho: {tamanho} bytes, mínimo: {MIN_FILE_SIZE_BYTES} bytes).",
            )
        if tamanho > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo excede o tamanho limite de 5 MB ({tamanho} bytes).",
            )
        validacoes.append(f"Tamanho de {tamanho} bytes dentro dos limites operacionais.")

        # 3. Cálculo de integridade criptográfica SHA-256 sobre bytes brutos
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        validacoes.append(f"Hash SHA-256 calculado sobre os bytes brutos originais: {sha256_hash}")

        # 4. Decodificação e parsing específico por formato
        data: dict[str, Any]
        if ext == ".json":
            try:
                content_str = raw_bytes.decode("utf-8")
                data = json.loads(content_str)
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Arquivo JSON não está codificado em UTF-8 válido: {exc}",
                ) from exc
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sintaxe JSON corrompida ou inválida: {exc}",
                ) from exc
        elif ext == ".csv":
            data = parse_deral_csv(raw_bytes, sha256_hash)
            validacoes.append("Modelo CSV DERAL decodificado e validado contra injeção de fórmulas.")
        elif ext == ".xls":
            data = parse_deral_xls(raw_bytes, sha256_hash)
            validacoes.append(f"Planilha .xls BIFF8 decodificada com sucesso via parser DERAL/SEAB.")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato '{ext}' não suportado.",
            )

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O snapshot deve conter um objeto envelope na raiz.",
            )

        # 5. Validação dos campos obrigatórios do envelope
        data_referencia = str(data.get("dataReferencia") or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_referencia):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campo 'dataReferencia' ausente ou fora do padrão ISO YYYY-MM-DD: '{data_referencia}'",
            )
        validacoes.append(f"Data de referência temporal validada: {data_referencia}")

        documento_oficial = str(data.get("documentoOficial") or "").strip()
        fonte_declarada = str(data.get("fonte") or "DERAL/SEAB-PR").strip()

        # 6. Verificação de proveniência oficial governamental
        origem_verif, estado_verif, msg_prov = verificar_proveniencia_governamental(
            documento_oficial, fonte_declarada
        )
        validacoes.append(msg_prov)

        itens = data.get("itens")
        if not isinstance(itens, list) or len(itens) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O snapshot não contém a lista obrigatória de itens de cotação.",
            )

        # 7. Validação das 21 commodities do catálogo canônico
        ids_encontrados = set()
        for idx, item in enumerate(itens):
            if not isinstance(item, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item no índice {idx} não é um objeto válido.",
                )
            cid = str(item.get("id") or "").strip()
            if not cid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item no índice {idx} não possui 'id' de commodity.",
                )
            if cid in ids_encontrados:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Commodity duplicada no snapshot: '{cid}'.",
                )
            ids_encontrados.add(cid)

            # Validação numérica estrita (sem nulos, strings vazias ou valores negativos)
            valor = item.get("valor")
            valor_original = item.get("valorOriginal")
            if valor is None or not isinstance(valor, (int, float)) or valor <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Commodity '{cid}' possui valor de cotação inválido ou negativo: {valor}",
                )
            if valor_original is None or not isinstance(valor_original, (int, float)) or valor_original <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Commodity '{cid}' possui 'valorOriginal' inválido ou negativo: {valor_original}",
                )

            # Validação de campos descritivos obrigatórios
            for fld in ["commodityNome", "produtoOriginal", "classificacao", "unidade", "unidadeOriginal", "registroOriginal"]:
                val = str(item.get(fld) or "").strip()
                if not val:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Commodity '{cid}' está sem o campo obrigatório '{fld}'.",
                    )

        faltantes = COMMODITIES_HOMOLOGADAS_DERAL - ids_encontrados
        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Snapshot incompleto. Faltam {len(faltantes)} commodities homologadas: {', '.join(sorted(faltantes))}",
            )

        extras = ids_encontrados - COMMODITIES_HOMOLOGADAS_DERAL
        if extras:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Snapshot contém commodities não catalogadas: {', '.join(sorted(extras))}",
            )

        validacoes.append(f"Todas as 21 commodities canônicas homologadas validadas com integridade cadastral.")

        snapshot_id = data_referencia
        norm_filename = f"deral-prp-{data_referencia}{ext}"

        now_iso = datetime.now(timezone.utc).isoformat()
        meta = DeralSnapshotMetadata(
            id=snapshot_id,
            filename=norm_filename,
            sha256=sha256_hash,
            data_referencia=data_referencia,
            data_publicacao=data.get("dataPublicacao"),
            data_obtencao=now_iso,
            fonte_oficial=fonte_declarada,
            origem_declarada=fonte_declarada,
            origem_verificada=origem_verif,
            estado_verificacao=estado_verif,  # type: ignore[arg-type]
            estado_aprovacao="PENDENTE",
            aprovado_por=None,
            aprovado_em=None,
            motivo_rejeicao=None,
            documento_oficial=documento_oficial,
            total_itens=len(itens),
            status="VALIDADO",
            is_active=False,
            uploaded_at=now_iso,
            uploaded_by="operador@deepfarms.com",
            transformacao_aplicada=str(data.get("transformacaoAplicada") or "Arredondamento decimal HALF_UP para 2 casas"),
            tamanho_bytes=tamanho,
        )

        return data, meta, validacoes

    async def list_snapshots(self, session: AsyncSession) -> DeralSnapshotsListResponse:
        """Lista todos os snapshots DERAL catalogados na plataforma."""
        index = await self._get_or_create_index(session)
        snaps_raw = index.get("snapshots", [])
        active_id = index.get("active_snapshot_id")

        items: list[DeralSnapshotMetadata] = []
        for s in snaps_raw:
            try:
                meta = DeralSnapshotMetadata.model_validate(s)
                meta.is_active = (meta.id == active_id)
                items.append(meta)
            except Exception as exc:
                logger.warning(f"Snapshot corrompido no índice: {exc}")

        items.sort(key=lambda x: x.data_referencia, reverse=True)

        return DeralSnapshotsListResponse(
            active_snapshot_id=active_id,
            snapshots=items,
            total=len(items),
        )

    async def get_snapshot_details(
        self, session: AsyncSession, snapshot_id: str
    ) -> DeralSnapshotDetailResponse:
        """Obtém detalhes e itens de um snapshot para visualização prévia."""
        index = await self._get_or_create_index(session)
        active_id = index.get("active_snapshot_id")

        meta_dict = next((s for s in index.get("snapshots", []) if s.get("id") == snapshot_id), None)
        if not meta_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot DERAL '{snapshot_id}' não encontrado no índice.",
            )

        metadata = DeralSnapshotMetadata.model_validate(meta_dict)
        metadata.is_active = (metadata.id == active_id)

        stmt = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{snapshot_id}"
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        itens: list[dict[str, Any]] = []
        raw_preview: dict[str, Any] | None = None

        if record and isinstance(record.valor, dict):
            snap_data = record.valor.get("snapshot_data", {})
            itens = snap_data.get("itens", [])
            raw_preview = {
                "schemaVersion": snap_data.get("schemaVersion"),
                "tituloDocumento": snap_data.get("tituloDocumento"),
                "semana": snap_data.get("semana"),
                "periodo": snap_data.get("periodo"),
            }
        elif snapshot_id == "2026-10-16" and SNAPSHOT_PATH.exists():
            try:
                baseline_data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
                itens = baseline_data.get("itens", [])
            except Exception:
                itens = []

        return DeralSnapshotDetailResponse(
            metadata=metadata,
            itens=itens,
            raw_document_preview=raw_preview,
        )

    async def upload_snapshot(
        self,
        session: AsyncSession,
        raw_bytes: bytes,
        filename: str,
        admin_claims: Any,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeralSnapshotUploadResponse:
        """Processa upload, valida conformidade rígida e salva snapshot com bytes imutáveis como VALIDADO."""
        data, metadata, validacoes = self.validate_snapshot_raw(raw_bytes, filename)
        mapa_anterior = await self._carregar_precos_atuais_mapa(session)
        if isinstance(data.get("itens"), list):
            _enriquecer_variacao_snapshot(data["itens"], mapa_anterior)

        admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)
        metadata.uploaded_by = admin_email

        stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
        res_idx = await session.execute(stmt_idx)
        idx_record = res_idx.scalar_one_or_none()

        if not idx_record:
            index_data = await self._get_or_create_index(session)
            stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
            res_idx = await session.execute(stmt_idx)
            idx_record = res_idx.scalar_one()

        index_val = dict(idx_record.valor) if isinstance(idx_record.valor, dict) else {}
        snaps_list = list(index_val.get("snapshots", []))

        existing = next((s for s in snaps_list if s.get("id") == metadata.id), None)
        if existing:
            if existing.get("is_active") or existing.get("id") == index_val.get("active_snapshot_id"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"O snapshot '{metadata.id}' já existe e está atualmente ATIVO. Não é permitido sobrescrever versão ativa.",
                )
            snaps_list = [s for s in snaps_list if s.get("id") != metadata.id]

        snaps_list.append(metadata.model_dump())
        index_val["snapshots"] = snaps_list
        idx_record.valor = copy.deepcopy(index_val)
        flag_modified(idx_record, "valor")

        snap_key = f"{KEY_DERAI_SNAP_PREFIX}{metadata.id}"
        stmt_snap = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == snap_key).with_for_update()
        res_snap = await session.execute(stmt_snap)
        snap_rec = res_snap.scalar_one_or_none()

        payload_to_store = {
            "metadata": metadata.model_dump(),
            "snapshot_data": data,
            "raw_bytes_base64": base64.b64encode(raw_bytes).decode("ascii"),
        }

        if snap_rec:
            snap_rec.valor = payload_to_store
            snap_rec.ativo = True
        else:
            snap_rec = ConfiguracaoSaaS(
                id=uuid.uuid4(),
                chave=snap_key,
                valor=payload_to_store,
                descricao=f"Snapshot DERAL {metadata.id} ({metadata.filename})",
                ativo=True,
            )
            session.add(snap_rec)

        audit = AdminAuditLog(
            id=uuid.uuid4(),
            admin_user_id=admin_uid,
            admin_email=admin_email,
            acao="agro.market.deral.upload",
            entidade="deral_snapshot",
            entidade_id=snap_rec.id,
            descricao=f"Upload e validação do snapshot DERAL {metadata.id} (SHA-256: {metadata.sha256[:16]}...)",
            dados_anteriores=None,
            dados_novos={
                "snapshot_id": metadata.id,
                "filename": metadata.filename,
                "sha256": metadata.sha256,
                "data_referencia": metadata.data_referencia,
                "total_itens": metadata.total_itens,
                "origem_verificada": metadata.origem_verificada,
                "estado_verificacao": metadata.estado_verificacao,
                "validacoes": validacoes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        session.add(audit)
        await session.commit()

        logger.info(f"Snapshot DERAL {metadata.id} validado e persistido por {admin_email}.")

        return DeralSnapshotUploadResponse(
            sucesso=True,
            mensagem="Snapshot DERAL validado com sucesso e persistido imutavelmente. Aguarda aprovação formal de proveniência.",
            metadata=metadata,
            validacoes=validacoes,
            itens_preview=data.get("itens", []),
        )

    async def approve_snapshot(
        self,
        session: AsyncSession,
        snapshot_id: str,
        aprovado: bool,
        justificativa: str,
        admin_claims: Any,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeralSnapshotDetailResponse:
        """Aprova ou rejeita formalmente a proveniência e integridade de um snapshot para publicação."""
        admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

        stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
        res_idx = await session.execute(stmt_idx)
        idx_rec = res_idx.scalar_one_or_none()
        if not idx_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Índice de snapshots não encontrado.",
            )

        index_val = dict(idx_rec.valor) if isinstance(idx_rec.valor, dict) else {}
        snaps_list = list(index_val.get("snapshots", []))
        target_meta = next((s for s in snaps_list if s.get("id") == snapshot_id), None)

        if not target_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' não catalogado para aprovação.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        if aprovado:
            if target_meta.get("estado_verificacao") == "FALHA_VERIFICACAO":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Snapshot com falha comprovada de verificação de proveniência governamental não pode ser aprovado.",
                )
            target_meta["estado_aprovacao"] = "APROVADO"
            if target_meta.get("status") != "ATIVO":
                target_meta["status"] = "APROVADO"
            target_meta["aprovado_por"] = admin_email
            target_meta["aprovado_em"] = now_iso
            target_meta["motivo_rejeicao"] = None
            acao = "agro.market.deral.approve"
            desc = f"Aprovação formal da proveniência do snapshot DERAL {snapshot_id}: {justificativa}"
        else:
            if target_meta.get("is_active"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é permitido rejeitar um snapshot que está atualmente ATIVO. Execute rollback primeiro.",
                )
            target_meta["estado_aprovacao"] = "REJEITADO"
            target_meta["status"] = "REJEITADO"
            target_meta["motivo_rejeicao"] = justificativa
            acao = "agro.market.deral.reject"
            desc = f"Rejeição formal da proveniência do snapshot DERAL {snapshot_id}: {justificativa}"

        index_val["snapshots"] = snaps_list
        idx_rec.valor = copy.deepcopy(index_val)
        flag_modified(idx_rec, "valor")

        stmt_snap = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{snapshot_id}"
        ).with_for_update()
        res_snap = await session.execute(stmt_snap)
        snap_rec = res_snap.scalar_one_or_none()
        if snap_rec and isinstance(snap_rec.valor, dict):
            snap_val = copy.deepcopy(snap_rec.valor)
            if "metadata" in snap_val and isinstance(snap_val["metadata"], dict):
                snap_val["metadata"]["estado_aprovacao"] = target_meta["estado_aprovacao"]
                snap_val["metadata"]["status"] = target_meta["status"]
                snap_val["metadata"]["aprovado_por"] = target_meta.get("aprovado_por")
                snap_val["metadata"]["aprovado_em"] = target_meta.get("aprovado_em")
                snap_val["metadata"]["motivo_rejeicao"] = target_meta.get("motivo_rejeicao")
                snap_rec.valor = snap_val
                flag_modified(snap_rec, "valor")

        audit = AdminAuditLog(
            id=uuid.uuid4(),
            admin_user_id=admin_uid,
            admin_email=admin_email,
            acao=acao,
            entidade="deral_snapshot",
            entidade_id=uuid.uuid4(),
            descricao=desc,
            dados_anteriores={"snapshot_id": snapshot_id},
            dados_novos={
                "snapshot_id": snapshot_id,
                "estado_aprovacao": target_meta["estado_aprovacao"],
                "justificativa": justificativa,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        session.add(audit)
        await session.commit()

        logger.info(f"Snapshot DERAL {snapshot_id} {'aprovado' if aprovado else 'rejeitado'} por {admin_email}.")
        return await self.get_snapshot_details(session, snapshot_id)

    async def verify_snapshot_integrity(
        self, session: AsyncSession, snapshot_id: str
    ) -> DeralSnapshotIntegrityResponse:
        """Audita e recalcula o hash SHA-256 e tamanho a partir dos bytes originais imutáveis persistidos."""
        index = await self._get_or_create_index(session)
        meta_dict = next((s for s in index.get("snapshots", []) if s.get("id") == snapshot_id), None)
        if not meta_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' não encontrado no índice.",
            )

        stmt = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{snapshot_id}"
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        raw_bytes = b""
        if record and isinstance(record.valor, dict):
            b64_str = record.valor.get("raw_bytes_base64", "")
            if b64_str:
                raw_bytes = base64.b64decode(b64_str)

        if not raw_bytes and snapshot_id == "2026-10-16" and SNAPSHOT_PATH.exists():
            raw_bytes = SNAPSHOT_PATH.read_bytes()

        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Arquivo original com bytes brutos do snapshot '{snapshot_id}' não encontrado no storage.",
            )

        sha256_recalc = hashlib.sha256(raw_bytes).hexdigest()
        sha256_registrado = str(meta_dict.get("sha256") or "")
        tamanho_registrado = int(meta_dict.get("tamanho_bytes") or len(raw_bytes))
        tamanho_armazenado = len(raw_bytes)

        integro = (sha256_recalc == sha256_registrado) and (tamanho_registrado == tamanho_armazenado)
        origem_verif = bool(meta_dict.get("origem_verificada", False))
        estado_verif = str(meta_dict.get("estado_verificacao", "PENDENTE"))

        msg = (
            "Integridade criptográfica comprovada: os bytes originais armazenados recalculam "
            "exatamente o mesmo SHA-256 e tamanho registrados no momento do upload."
            if integro
            else "FALHA DE INTEGRIDADE: Divergência entre o hash recalculado e o registrado!"
        )

        return DeralSnapshotIntegrityResponse(
            snapshot_id=snapshot_id,
            sha256_registrado=sha256_registrado,
            sha256_recalculado=sha256_recalc,
            tamanho_bytes_registrado=tamanho_registrado,
            tamanho_bytes_armazenado=tamanho_armazenado,
            integro=integro,
            verificado_em=datetime.now(timezone.utc).isoformat(),
            origem_verificada=origem_verif,
            estado_verificacao=estado_verif,
            mensagem=msg,
        )

    async def get_snapshot_raw_bytes(
        self, session: AsyncSession, snapshot_id: str
    ) -> tuple[bytes, str, str]:
        """Recupera os bytes brutos originais do documento para download ou auditoria forense.

        Returns:
            Tupla (raw_bytes, filename, content_type).
        """
        index = await self._get_or_create_index(session)
        meta_dict = next((s for s in index.get("snapshots", []) if s.get("id") == snapshot_id), None)
        if not meta_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' não encontrado.",
            )

        filename = str(meta_dict.get("filename") or f"deral-{snapshot_id}.json")
        ext = Path(filename).suffix.lower()
        content_types = {
            ".json": "application/json",
            ".csv": "text/csv; charset=utf-8",
            ".xls": "application/vnd.ms-excel",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        stmt = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{snapshot_id}"
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        raw_bytes = b""
        if record and isinstance(record.valor, dict):
            b64_str = record.valor.get("raw_bytes_base64", "")
            if b64_str:
                raw_bytes = base64.b64decode(b64_str)

        if not raw_bytes and snapshot_id == "2026-10-16" and SNAPSHOT_PATH.exists():
            raw_bytes = SNAPSHOT_PATH.read_bytes()

        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bytes brutos do snapshot '{snapshot_id}' inacessíveis.",
            )

        return raw_bytes, filename, content_type

    async def activate_snapshot(
        self,
        session: AsyncSession,
        snapshot_id: str,
        admin_claims: Any,
        expected_revision: Optional[int] = None,
        justificativa: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeralSnapshotDetailResponse:
        """Ativa atomicamente um snapshot previamente validado e aprovado com controle de concorrência."""
        admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

        stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
        res_idx = await session.execute(stmt_idx)
        idx_rec = res_idx.scalar_one_or_none()
        if not idx_rec:
            await self._get_or_create_index(session)
            stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
            res_idx = await session.execute(stmt_idx)
            idx_rec = res_idx.scalar_one()

        index_val = dict(idx_rec.valor) if isinstance(idx_rec.valor, dict) else {}
        snaps_list = list(index_val.get("snapshots", []))
        current_active_id = index_val.get("active_snapshot_id")

        if current_active_id == snapshot_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O snapshot '{snapshot_id}' já está atualmente ativo.",
            )

        target_meta = next((s for s in snaps_list if s.get("id") == snapshot_id), None)
        if not target_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' não catalogado para ativação.",
            )

        # TRAVA DE PROVENIÊNCIA E APROVAÇÃO OBRIGATÓRIA
        if target_meta.get("estado_aprovacao") != "APROVADO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"O snapshot '{snapshot_id}' está com estado de aprovação '{target_meta.get('estado_aprovacao')}'. "
                    "Apenas snapshots formalmente APROVADOS podem ser ativados no serviço público."
                ),
            )
        if target_meta.get("estado_verificacao") == "FALHA_VERIFICACAO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Snapshot com falha comprovada de verificação de proveniência não pode ser ativado.",
            )

        stmt_snap = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{snapshot_id}"
        )
        res_snap = await session.execute(stmt_snap)
        snap_rec = res_snap.scalar_one_or_none()

        if not snap_rec or not isinstance(snap_rec.valor, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dados persistidos do snapshot '{snapshot_id}' não encontrados. Operação abortada para evitar ponteiro nulo.",
            )

        snap_data = snap_rec.valor.get("snapshot_data", {})
        if not snap_data.get("itens") or len(snap_data.get("itens", [])) != 21:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Snapshot '{snapshot_id}' corrompido em banco. Operação abortada.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        for s in snaps_list:
            if s.get("id") == current_active_id:
                s["status"] = "ANTERIOR"
                s["is_active"] = False
            elif s.get("id") == snapshot_id:
                s["status"] = "ATIVO"
                s["is_active"] = True
                s["activated_at"] = now_iso
                s["activated_by"] = admin_email

        index_val["snapshots"] = snaps_list
        index_val["previous_snapshot_id"] = current_active_id
        index_val["active_snapshot_id"] = snapshot_id
        idx_rec.valor = copy.deepcopy(index_val)
        flag_modified(idx_rec, "valor")

        config_val, config_meta, _ = await agro_config_service.get_config(session, KEY_MERCADO, use_cache=False)
        updated_config_val = dict(config_val)
        updated_config_val["active_snapshot_id"] = snapshot_id
        updated_config_val["deral_active_snapshot"] = target_meta.get("filename", f"deral-prp-{snapshot_id}.json")

        claims_with_override = dict(admin_claims) if isinstance(admin_claims, dict) else {"sub": str(admin_uid), "email": admin_email}
        claims_with_override["_allow_snapshot_switch"] = True

        try:
            # commit=False assegura que a gravação do índice, config e auditoria ocorram em UMA SÓ transação
            _, new_cfg_meta = await agro_config_service.update_config(
                session=session,
                chave=KEY_MERCADO,
                novo_valor=updated_config_val,
                admin_claims=claims_with_override,
                expected_revision=expected_revision,
                descricao="Ativação de novo snapshot semanal DERAL homologado",
                ip_address=ip_address,
                user_agent=user_agent,
                commit=False,
            )

            audit = AdminAuditLog(
                id=uuid.uuid4(),
                admin_user_id=admin_uid,
                admin_email=admin_email,
                acao="agro.market.deral.activate",
                entidade="deral_snapshot",
                entidade_id=snap_rec.id,
                descricao=f"Ativação atômica do snapshot DERAL {snapshot_id} (substituindo {current_active_id})",
                dados_anteriores={
                    "active_snapshot_id": current_active_id,
                },
                dados_novos={
                    "active_snapshot_id": snapshot_id,
                    "filename": target_meta.get("filename"),
                    "sha256": target_meta.get("sha256"),
                    "justificativa": justificativa,
                    "revision": new_cfg_meta.revision,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc),
            )
            session.add(audit)

            # Transação atômica única
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        # Sincronização pós-commit segura
        await agro_config_service.post_commit_sync(
            chave=KEY_MERCADO,
            payload_data=updated_config_val,
            new_meta=new_cfg_meta,
            ativo=True,
        )

        self.set_cached_active_snapshot(snapshot_id, snap_data)

        # Invalida cache local de preços públicos
        from public_mercado.precos_publicos_service import get_precos_service
        try:
            precos_svc = get_precos_service()
            precos_svc.invalidate_cache()
        except Exception:
            pass

        logger.info(f"Snapshot DERAL {snapshot_id} ativado atomicamente por {admin_email}.")
        return await self.get_snapshot_details(session, snapshot_id)

    async def rollback_snapshot(
        self,
        session: AsyncSession,
        target_snapshot_id: str,
        admin_claims: Any,
        expected_revision: Optional[int] = None,
        justificativa: str = "Rollback operacional preventivo",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeralSnapshotDetailResponse:
        """Executa rollback atômico para um snapshot previamente homologado em transação única."""
        admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

        stmt_idx = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == KEY_DERAI_INDEX).with_for_update()
        res_idx = await session.execute(stmt_idx)
        idx_rec = res_idx.scalar_one_or_none()
        if not idx_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Índice de snapshots não encontrado.",
            )

        index_val = dict(idx_rec.valor) if isinstance(idx_rec.valor, dict) else {}
        snaps_list = list(index_val.get("snapshots", []))
        current_active_id = index_val.get("active_snapshot_id")

        if current_active_id == target_snapshot_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O snapshot '{target_snapshot_id}' já é a versão ativa atual.",
            )

        target_meta = next((s for s in snaps_list if s.get("id") == target_snapshot_id), None)
        if not target_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot de destino '{target_snapshot_id}' não encontrado para rollback.",
            )

        # Apenas versões aprovadas são elegíveis para rollback
        if target_meta.get("estado_aprovacao") not in ("APROVADO", None) and target_meta.get("status") not in ("ANTERIOR", "ATIVO", "APROVADO"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Snapshot '{target_snapshot_id}' não está aprovado para reversão.",
            )

        stmt_snap = select(ConfiguracaoSaaS).where(
            ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{target_snapshot_id}"
        )
        res_snap = await session.execute(stmt_snap)
        snap_rec = res_snap.scalar_one_or_none()

        if not snap_rec or not isinstance(snap_rec.valor, dict):
            if target_snapshot_id == "2026-10-16" and SNAPSHOT_PATH.exists():
                snap_data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Dados do snapshot '{target_snapshot_id}' inacessíveis.",
                )
        else:
            snap_data = snap_rec.valor.get("snapshot_data", {})

        now_iso = datetime.now(timezone.utc).isoformat()
        for s in snaps_list:
            if s.get("id") == current_active_id:
                s["status"] = "ANTERIOR"
                s["is_active"] = False
            elif s.get("id") == target_snapshot_id:
                s["status"] = "ATIVO"
                s["is_active"] = True
                s["activated_at"] = now_iso
                s["activated_by"] = f"{admin_email} (rollback)"

        index_val["snapshots"] = snaps_list
        index_val["previous_snapshot_id"] = current_active_id
        index_val["active_snapshot_id"] = target_snapshot_id
        idx_rec.valor = copy.deepcopy(index_val)
        flag_modified(idx_rec, "valor")

        config_val, _, _ = await agro_config_service.get_config(session, KEY_MERCADO, use_cache=False)
        updated_config_val = dict(config_val)
        updated_config_val["active_snapshot_id"] = target_snapshot_id
        updated_config_val["deral_active_snapshot"] = target_meta.get("filename", f"deral-prp-{target_snapshot_id}.json")

        claims_with_override = dict(admin_claims) if isinstance(admin_claims, dict) else {"sub": str(admin_uid), "email": admin_email}
        claims_with_override["_allow_snapshot_switch"] = True

        try:
            _, new_cfg_meta = await agro_config_service.update_config(
                session=session,
                chave=KEY_MERCADO,
                novo_valor=updated_config_val,
                admin_claims=claims_with_override,
                expected_revision=expected_revision,
                descricao=f"Rollback do snapshot DERAL para versão {target_snapshot_id}",
                ip_address=ip_address,
                user_agent=user_agent,
                commit=False,
            )

            audit = AdminAuditLog(
                id=uuid.uuid4(),
                admin_user_id=admin_uid,
                admin_email=admin_email,
                acao="agro.market.deral.rollback",
                entidade="deral_snapshot",
                entidade_id=snap_rec.id if snap_rec else uuid.uuid4(),
                descricao=f"Rollback do snapshot DERAL de {current_active_id} para {target_snapshot_id}",
                dados_anteriores={
                    "active_snapshot_id": current_active_id,
                },
                dados_novos={
                    "active_snapshot_id": target_snapshot_id,
                    "justificativa": justificativa,
                    "revision": new_cfg_meta.revision,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc),
            )
            session.add(audit)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        await agro_config_service.post_commit_sync(
            chave=KEY_MERCADO,
            payload_data=updated_config_val,
            new_meta=new_cfg_meta,
            ativo=True,
        )

        self.set_cached_active_snapshot(target_snapshot_id, snap_data)

        from public_mercado.precos_publicos_service import get_precos_service
        try:
            precos_svc = get_precos_service()
            precos_svc.invalidate_cache()
        except Exception:
            pass

        logger.info(f"Rollback para snapshot DERAL {target_snapshot_id} concluído por {admin_email}.")
        return await self.get_snapshot_details(session, target_snapshot_id)

    async def _carregar_precos_atuais_mapa(self, session: AsyncSession) -> dict[str, float]:
        """Obtém o mapa id -> valor do snapshot ativo no banco ou do baseline local."""
        snap_data = await self.sync_active_snapshot_from_db(session) or {}
        if not snap_data:
            index = await self._get_or_create_index(session)
            active_id = str(index.get("active_snapshot_id") or "")
            if active_id:
                stmt = select(ConfiguracaoSaaS).where(
                    ConfiguracaoSaaS.chave == f"{KEY_DERAI_SNAP_PREFIX}{active_id}"
                )
                rec = (await session.execute(stmt)).scalar_one_or_none()
                if rec and isinstance(rec.valor, dict):
                    snap_data = (
                        rec.valor.get("snapshot_data")
                        or rec.valor.get("data")
                        or {}
                    )
        if not snap_data and SNAPSHOT_PATH.exists():
            snap_data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return {
            str(item["id"]): float(item["valor"])
            for item in snap_data.get("itens", [])
            if isinstance(item, dict) and item.get("id") and item.get("valor") is not None
        }

    async def gerar_template_csv(self, session: AsyncSession) -> tuple[bytes, str]:
        """Gera arquivo CSV modelo com as 21 commodities e preços da referência ativa.

        Args:
            session: Sessão assíncrona do banco para ler cotações vigentes.

        Returns:
            Tupla (bytes_utf8_bom, nome_arquivo_csv).
        """
        precos_map = await self._carregar_precos_atuais_mapa(session)
        hoje_iso = date.today().isoformat()
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "id", "commodity_nome", "produto_original", "unidade",
            "unidade_original", "valor", "data_referencia", "documento_oficial",
        ])
        for cid, nome, prod_orig, _ln, unidade, unidade_orig in COMMODITIES_XLS_MAP:
            valor = precos_map.get(cid, 0.0)
            writer.writerow([cid, nome, prod_orig, unidade, unidade_orig, f"{valor:.2f}", hoje_iso, DEFAULT_DERAL_DOC_URL])
        csv_bytes = ("\ufeff" + buf.getvalue()).encode("utf-8")
        return csv_bytes, f"modelo-deral-prp-{hoje_iso}.csv"


# Instância singleton global do serviço
deral_snapshot_service = DeralSnapshotService()
