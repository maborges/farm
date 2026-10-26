"""
Teste de auditoria forense e paridade estrita: Planilha XLS DERAL × Snapshot JSON.
Verifica:
1. Correspondência estrita do SHA-256 do arquivo binário OLE2.
2. Extração célula a célula de todas as 21 commodities homologadas.
3. Arredondamento monetário estrito via Decimal com ROUND_HALF_UP.
4. Paridade exata de IDs, coordenadas (Rav!X...), unidades e rótulos.
5. Falha detalhada identificando a commodity e o campo exato em caso de divergência.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

# Adiciona services/api ao sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from scripts.atualizar_snapshot_deral import extrair_valores_coluna_x_biff8
from public_mercado.precos_publicos import carregar_precos_publicos

SNAPSHOT_DIR = API_ROOT / "public_mercado" / "data"
EVIDENCIAS_DIR = REPO_ROOT / "docs" / "implementation" / "reports" / "evidencias"


def localizar_planilha_por_hash(hash_sha256: str) -> Path | None:
    """Localiza o arquivo XLS correspondente ao hash SHA-256 no repositório."""
    for arquivo in EVIDENCIAS_DIR.rglob("*.xls"):
        if hashlib.sha256(arquivo.read_bytes()).hexdigest() == hash_sha256:
            return arquivo
    return None


def test_paridade_estrita_xls_vs_snapshot_deral():
    """Confronta diretamente o binário oficial do DERAL com o snapshot JSON em produção."""
    snapshot_path = SNAPSHOT_DIR / "deral-prp-2026-10-16.json"
    assert snapshot_path.exists(), f"Snapshot não encontrado em: {snapshot_path}"

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    hash_esperado = snapshot.get("documentoHashSha256")
    assert hash_esperado, "Snapshot não contém documentoHashSha256"

    # Localiza o arquivo XLS pela proveniência criptográfica
    planilha_path = localizar_planilha_por_hash(hash_esperado)
    assert planilha_path is not None, f"Nenhuma planilha com hash {hash_esperado} encontrada em {EVIDENCIAS_DIR}"

    raw_bytes = planilha_path.read_bytes()
    assert hashlib.sha256(raw_bytes).hexdigest() == hash_esperado, "Hash SHA-256 da planilha diverge do esperado"

    # Extrai diretamente os valores numéricos da coluna X via BIFF8
    valores_coluna_x = extrair_valores_coluna_x_biff8(raw_bytes)

    # Leitura dos rótulos e unidades diretamente da planilha via xlrd para dupla checagem independente
    import xlrd
    book = xlrd.open_workbook(str(planilha_path))
    sheet = book.sheet_by_name(snapshot.get("planilha", "Rav"))

    itens = snapshot.get("itens", [])
    assert len(itens) == 21, f"Esperava-se 21 itens no snapshot, encontrado {len(itens)}"

    divergencias = []

    for item in itens:
        cid = item["id"]
        registro = item["registroOriginal"]
        assert registro.startswith("Rav!X"), f"[{cid}] Registro original inválido: {registro}"
        row_excel = int(registro.split("!X")[1])
        row_idx = row_excel - 1

        # 1. Validação do valor bruto e arredondamento
        if row_excel not in valores_coluna_x:
            divergencias.append(f"[{cid}] Célula {registro} não encontrada no parser BIFF8 da coluna X")
            continue

        valor_bruto_biff8 = valores_coluna_x[row_excel]
        valor_bruto_xlrd = float(sheet.cell_value(row_idx, 23))

        if abs(valor_bruto_biff8 - valor_bruto_xlrd) > 1e-5:
            divergencias.append(
                f"[{cid}] Divergência entre parsers no valor bruto: BIFF8={valor_bruto_biff8} vs XLRD={valor_bruto_xlrd}"
            )

        # Arredondamento comercial HALF_UP
        dec_bruto = Decimal(str(valor_bruto_biff8))
        valor_esperado_round = float(dec_bruto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        if abs(item["valor"] - valor_esperado_round) > 1e-4:
            divergencias.append(
                f"[{cid}] Divergência em 'valor': snapshot={item['valor']} vs esperado={valor_esperado_round} (bruto={valor_bruto_biff8})"
            )

        if abs(item["valorOriginal"] - valor_bruto_biff8) > 1e-4:
            divergencias.append(
                f"[{cid}] Divergência em 'valorOriginal': snapshot={item['valorOriginal']} vs esperado={valor_bruto_biff8}"
            )

        # 2. Validação do rótulo do produto original na planilha
        rotulo_col_b = str(sheet.cell_value(row_idx, 1)).strip()
        rotulo_col_a = str(sheet.cell_value(row_idx, 0)).strip()
        rotulo_esperado = rotulo_col_b if rotulo_col_b else rotulo_col_a

        if item["produtoOriginal"] != rotulo_esperado:
            divergencias.append(
                f"[{cid}] Divergência em 'produtoOriginal': snapshot='{item['produtoOriginal']}' vs planilha='{rotulo_esperado}'"
            )

        # 3. Validação da unidade original na planilha
        unidade_esperada = str(sheet.cell_value(row_idx, 2)).strip()
        if item["unidadeOriginal"] != unidade_esperada:
            divergencias.append(
                f"[{cid}] Divergência em 'unidadeOriginal': snapshot='{item['unidadeOriginal']}' vs planilha='{unidade_esperada}'"
            )

    # 4. Validação da data de referência oficial propagada para os serviços da API
    precos_api = carregar_precos_publicos()
    assert len(precos_api) == 21
    for preco in precos_api:
        if preco.dataReferencia != snapshot["dataReferencia"]:
            divergencias.append(
                f"[{preco.id}] Data de referência na API ({preco.dataReferencia}) diverge do snapshot ({snapshot['dataReferencia']})"
            )

    assert not divergencias, "Falha de paridade estrita XLS × Snapshot:\n" + "\n".join(divergencias)
