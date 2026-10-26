"""Testes unitários para o script autônomo de atualização de snapshots do DERAL/SEAB-PR."""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona services/api ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from scripts import atualizar_snapshot_deral
from scripts.atualizar_snapshot_deral import (
    DEFAULT_SOURCE_URL,
    OLE2_MAGIC,
    construir_snapshot,
    executar_pipeline,
    extrair_valores_coluna_x_biff8,
    validar_snapshot_pydantic,
    validar_estrutura_planilha,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PRP_XLS = REPO_ROOT / "docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/deral-prp-2026-10-16.xls"


def test_rejeita_url_insegura_http():
    """Valida que URLs HTTP não criptografadas são estritamente rejeitadas."""
    with pytest.raises(ValueError, match="URL insegura rejeitada. Exige-se HTTPS"):
        from scripts.atualizar_snapshot_deral import baixar_arquivo_seguro
        baixar_arquivo_seguro("http://inseguro.agricultura.pr.gov.br/prp.xls")


def test_extrair_valores_coluna_x_dados_validos():
    """Valida extração nativa de células BIFF8 sem dependência de bibliotecas externas."""
    if not SAMPLE_PRP_XLS.exists():
        pytest.skip("Arquivo de auditoria local não encontrado")

    dados = SAMPLE_PRP_XLS.read_bytes()
    col_x = extrair_valores_coluna_x_biff8(dados)

    assert len(col_x) >= 21
    # Verifica commodities essenciais
    assert 12 in col_x  # Soja (Rav!X12)
    assert 11 in col_x  # Milho (Rav!X11)
    assert 7 in col_x   # Café (Rav!X7)
    assert 46 in col_x  # Boi Gordo (Rav!X46)

    assert col_x[12] > 100.0
    assert col_x[11] > 40.0
    assert col_x[7] > 1000.0


def test_rejeita_arquivo_nao_ole2():
    """Valida rejeição de arquivos corrompidos ou que não sejam OLE2/BIFF8."""
    with pytest.raises(ValueError, match="não é um documento OLE2/BIFF8 válido"):
        extrair_valores_coluna_x_biff8(b"ARQUIVO_CORROMPIDO_HTML_OU_JSON")


def test_valida_rotulos_unidades_e_cabecalho_da_planilha():
    """Garante que o fluxo oficial confere a semântica antes dos números."""
    valores = validar_estrutura_planilha(SAMPLE_PRP_XLS.read_bytes())
    assert valores[7] == pytest.approx(1380.5078)
    assert valores[50] == pytest.approx(2.8141)


def test_construir_snapshot_com_todos_os_itens():
    """Valida montagem de snapshot com 21 commodities e arredondamento HALF_UP."""
    if not SAMPLE_PRP_XLS.exists():
        pytest.skip("Arquivo de auditoria local não encontrado")

    dados = SAMPLE_PRP_XLS.read_bytes()
    col_x = extrair_valores_coluna_x_biff8(dados)
    snapshot = construir_snapshot(col_x, "a" * 64)

    assert snapshot["schemaVersion"] == 1
    assert snapshot["fonte"] == "DERAL/SEAB-PR"
    assert len(snapshot["itens"]) == 21
    assert validar_snapshot_pydantic(snapshot) is True


def test_executar_pipeline_dry_run_sucesso():
    """Valida execução em modo dry-run sem alterar arquivos no disco."""
    if not SAMPLE_PRP_XLS.exists():
        pytest.skip("Arquivo de auditoria local não encontrado")

    codigo = executar_pipeline(
        arquivo_local=SAMPLE_PRP_XLS,
        dry_run=True,
    )
    assert codigo == 0


def test_falha_de_validacao_preserva_ultimo_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Uma atualização inválida não substitui o último snapshot publicado."""
    destino = tmp_path / "deral-prp-2026-10-16.json"
    destino.write_text('{"sentinela":"snapshot-valido"}\n', encoding="utf-8")
    monkeypatch.setattr(
        atualizar_snapshot_deral,
        "validar_estrutura_planilha",
        lambda _: (_ for _ in ()).throw(ValueError("estrutura inválida")),
    )
    codigo = executar_pipeline(arquivo_local=SAMPLE_PRP_XLS, output_dir=tmp_path)
    assert codigo == 1
    assert destino.read_text(encoding="utf-8") == '{"sentinela":"snapshot-valido"}\n'
