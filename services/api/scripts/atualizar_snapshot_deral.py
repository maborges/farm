"""Comando isolado e seguro para ingestão e atualização dos snapshots DERAL/SEAB-PR.

Atende integralmente aos 10 requisitos da Etapa D (DEEPFARMS-AGRO-FREE-01E2F-B5B):
1. HTTPS com validação rigorosa de certificados TLS.
2. Download e verificação estrutural do arquivo oficial (.xls).
3. Registro de hash SHA-256 e data/hora de coleta.
4. Conferência de estrutura, cabeçalhos, células e unidades.
5. Geração de snapshot temporário isolado.
6. Validação integral com schema Pydantic antes de publicar.
7. Publicação atômica (replace) apenas de snapshots aprovados.
8. Preservação do último snapshot válido em caso de falha.
9. Registro de logs estruturados em JSON para auditoria.
10. Sinalização de dados defasados sem introduzir números fictícios.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import struct
import sys
import tempfile
import unicodedata
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

# Adiciona services/api ao sys.path para import dos modelos de contrato
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import xlrd
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_SOURCE_URL = "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"
DEFAULT_OUTPUT_DIR = API_ROOT / "public_mercado" / "data"

OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

COMMODITIES_HOMOLOGADAS: list[tuple[str, str, str, int, str, str]] = [
    # 7 B4 (P0)
    ("arroz", "Arroz em Casca", "Arroz em casca irrigado", 6, "Saca de 60 kg", "60 kg"),
    ("cafe-arabica", "Café Beneficiado (Produtor)", "Café beneficiado produtor", 7, "Saca de 60 kg", "60 kg"),
    ("feijao", "Feijão de Cor", "Feijao de cor", 9, "Saca de 60 kg", "60 kg"),
    ("milho", "Milho Físico", "Milho", 11, "Saca de 60 kg", "60 kg"),
    ("soja", "Soja em Grão", "Soja", 12, "Saca de 60 kg", "60 kg"),
    ("trigo", "Trigo em Grão", "Trigo", 17, "Saca de 60 kg", "60 kg"),
    ("boi-gordo", "Boi Gordo", "Boi gordo", 46, "Arroba (@ de 15 kg)", "arroba"),
    # 14 P1 Novos
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


class ItemSnapshotDeral(BaseModel):
    """Registro bruto auditável extraído de uma célula do DERAL."""

    model_config = ConfigDict(extra="forbid")
    id: str
    commodityNome: str
    produtoOriginal: str
    classificacao: str
    valor: float = Field(gt=0, allow_inf_nan=False)
    valorOriginal: float = Field(gt=0, allow_inf_nan=False)
    unidade: str
    unidadeOriginal: str
    registroOriginal: str


class SnapshotDeral(BaseModel):
    """Contrato persistido de uma edição semanal do DERAL."""

    model_config = ConfigDict(extra="forbid")
    schemaVersion: int
    fonte: str
    documentoOficial: str
    documentoHashSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tituloDocumento: str
    semana: str
    periodo: str
    dataReferencia: str
    dataPublicacao: None
    planilha: str
    colunaValor: str
    transformacaoAplicada: str
    itens: list[ItemSnapshotDeral]


def log_estruturado(nivel: str, evento: str, **detalhes: Any) -> None:
    """Emite log estruturado em formato JSON legível por SIEM e pipelines de CI/CD."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nivel": nivel,
        "evento": evento,
        **detalhes,
    }
    print(json.dumps(payload, ensure_ascii=False))


def baixar_arquivo_seguro(url: str, timeout: int = 30) -> tuple[bytes, str]:
    """Baixa o arquivo binário via HTTPS com verificação estrita de TLS.

    Args:
        url: URL segura para download.
        timeout: Limite de tempo em segundos.

    Returns:
        Tupla com os bytes baixados e o hash SHA-256.

    Raises:
        ValueError: Caso a URL não utilize HTTPS ou o download falhe.
    """
    if not url.startswith("https://"):
        raise ValueError(f"URL insegura rejeitada. Exige-se HTTPS: {url}")

    # Cria contexto SSL seguro com validação rigorosa de certificados da CA
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DeepFarms-Agro-Updater/1.0 (+https://deepfarms.agro)"},
    )

    with urllib.request.urlopen(req, timeout=timeout, context=context) as resposta:
        status = getattr(resposta, "status", 200)
        if status != 200:
            raise ValueError(f"Servidor retornou status HTTP {status} para {url}")
        dados = resposta.read()

    sha256 = hashlib.sha256(dados).hexdigest()
    return dados, sha256


def extrair_valores_coluna_x_biff8(dados_xls: bytes) -> dict[int, float]:
    """Decodifica as células da Coluna X (índice 23) do stream BIFF8 usando struct.

    Args:
        dados_xls: Bytes brutos do arquivo .xls (OLE2).

    Returns:
        Dicionário mapeando número da linha (1-based, ex: 12 para X12) ao valor float.

    Raises:
        ValueError: Se o arquivo não possuir cabeçalho OLE2 válido.
    """
    if not dados_xls.startswith(OLE2_MAGIC):
        raise ValueError("Arquivo baixado não é um documento OLE2/BIFF8 válido")

    col_x: dict[int, float] = {}

    # 1. Registros NUMBER (0x0203)
    pos = 0
    while True:
        pos = dados_xls.find(b"\x03\x02\x0e\x00", pos)
        if pos == -1:
            break
        chunk = dados_xls[pos + 4 : pos + 18]
        if len(chunk) == 14:
            row, col, _ = struct.unpack("<HHH", chunk[:6])
            if col == 0x0017:  # Coluna X (23)
                val = struct.unpack("<d", chunk[6:14])[0]
                col_x[row + 1] = val
        pos += 4

    # 2. Registros MULRK (0x00BD)
    pos = 0
    while True:
        pos = dados_xls.find(b"\xbd\x00", pos)
        if pos == -1:
            break
        if pos + 4 <= len(dados_xls):
            rlen = struct.unpack("<H", dados_xls[pos + 2 : pos + 4])[0]
            body = dados_xls[pos + 4 : pos + 4 + rlen]
            if len(body) >= 6:
                row, col_first = struct.unpack("<HH", body[:4])
                col_last = struct.unpack("<H", body[-2:])[0]
                offset = 4
                col = col_first
                while col <= col_last and offset + 6 <= len(body):
                    _, rk_raw = struct.unpack("<HI", body[offset : offset + 6])
                    if rk_raw & 0x02:
                        val = float(rk_raw >> 2)
                    else:
                        val = struct.unpack("<d", struct.pack("<II", 0, rk_raw & 0xFFFFFFFC))[0]
                    if rk_raw & 0x01:
                        val /= 100.0
                    if col == 0x0017:
                        col_x[row + 1] = val
                    col += 1
                    offset += 6
        pos += 2

    # 3. Registros RK simples (0x027E)
    pos = 0
    while True:
        pos = dados_xls.find(b"\x7e\x02", pos)
        if pos == -1:
            break
        if pos + 4 <= len(dados_xls):
            rlen = struct.unpack("<H", dados_xls[pos + 2 : pos + 4])[0]
            if rlen >= 10:
                row, col, _ = struct.unpack("<HHH", dados_xls[pos + 4 : pos + 10])
                if col == 0x0017:
                    rk_raw = struct.unpack("<I", dados_xls[pos + 10 : pos + 14])[0]
                    if rk_raw & 0x02:
                        val = float(rk_raw >> 2)
                    else:
                        val = struct.unpack("<d", struct.pack("<II", 0, rk_raw & 0xFFFFFFFC))[0]
                    if rk_raw & 0x01:
                        val /= 100.0
                    col_x[row + 1] = val
        pos += 2

    return col_x


def validar_estrutura_planilha(dados_xls: bytes) -> dict[int, float]:
    """Valida aba, cabeçalhos, produtos e unidades antes de ler as médias.

    Args:
        dados_xls: Conteúdo integral do documento oficial OLE2/BIFF8.

    Returns:
        Valores da coluna X indexados pela linha 1-based.

    Raises:
        ValueError: Se a estrutura ou qualquer registro homologado divergir.
    """
    if not dados_xls.startswith(OLE2_MAGIC):
        raise ValueError("Arquivo baixado não é um documento OLE2/BIFF8 válido")
    try:
        aba = xlrd.open_workbook(file_contents=dados_xls).sheet_by_name("Rav")
    except (xlrd.XLRDError, IndexError) as exc:
        raise ValueError("Aba oficial 'Rav' ausente ou ilegível") from exc
    if "PREÇOS MÉDIOS SEMANAIS" not in str(aba.cell_value(0, 0)):
        raise ValueError("Título oficial do DERAL não confere")
    if str(aba.cell_value(1, 23)).strip() != "MÉDIA":
        raise ValueError("Cabeçalho Rav!X2 deve ser 'MÉDIA'")
    linhas = _indexar_linhas_produtos(aba)
    valores: dict[int, float] = {}
    for cid, _, produto, linha_historica, _, unidade in COMMODITIES_HOMOLOGADAS:
        assinatura = (_normalizar_rotulo(produto), _normalizar_rotulo(unidade))
        linha = linhas.get(assinatura)
        if linha is None:
            raise ValueError(f"Produto ou unidade divergente para '{cid}' (linha histórica {linha_historica})")
        valores[linha] = float(aba.cell_value(linha - 1, 23))
    return valores


def _normalizar_rotulo(valor: object) -> str:
    """Normaliza rótulos para tolerar acentos, caixa e espaços da planilha."""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.casefold().split())


def _indexar_linhas_produtos(aba: Any) -> dict[tuple[str, str], int]:
    """Localiza as commodities pela identificação textual em vez de linha fixa."""
    return {
        (_normalizar_rotulo(aba.cell_value(row, 1)), _normalizar_rotulo(aba.cell_value(row, 2))): row + 1
        for row in range(2, aba.nrows)
        if str(aba.cell_value(row, 1)).strip() and str(aba.cell_value(row, 2)).strip()
    }


def _linhas_por_id(dados_xls: bytes) -> dict[str, int]:
    """Retorna as coordenadas atuais de cada commodity homologada."""
    aba = xlrd.open_workbook(file_contents=dados_xls).sheet_by_name("Rav")
    linhas = _indexar_linhas_produtos(aba)
    return {
        cid: linhas[(_normalizar_rotulo(produto), _normalizar_rotulo(unidade))]
        for cid, _, produto, _, _, unidade in COMMODITIES_HOMOLOGADAS
    }


def extrair_metadados_planilha(dados_xls: bytes) -> tuple[str, str, str]:
    """Extrai semana, período e data final de referência da aba oficial."""
    aba = xlrd.open_workbook(file_contents=dados_xls).sheet_by_name("Rav")
    semana = str(aba.cell_value(0, 9)).removeprefix("SEMANA: ").strip()
    periodo = str(aba.cell_value(0, 15)).removeprefix("PERÍODO: ").strip()
    try:
        fim = periodo.rsplit(" a ", 1)[1]
        data_referencia = datetime.strptime(fim, "%d/%m/%Y").date().isoformat()
    except (IndexError, ValueError) as exc:
        raise ValueError("Período da planilha DERAL é inválido") from exc
    if not semana:
        raise ValueError("Semana da planilha DERAL não informada")
    return semana, periodo, data_referencia


def construir_snapshot(
    valores_col_x: dict[int, float],
    hash_sha256: str,
    data_referencia: str = "2026-10-16",
    semana: str = "42-2026",
    periodo: str = "12/10/2026 a 16/10/2026",
    linhas_por_id: dict[str, int] | None = None,
) -> dict[str, object]:
    """Constrói o payload JSON do snapshot oficial a partir das células extraídas.

    Args:
        valores_col_x: Mapeamento de linha para cotação bruta na coluna X.
        hash_sha256: Hash criptográfico do documento original.
        data_referencia: Data ISO final do período observado.
        semana: Código da semana agrícola.
        periodo: Descrição textual do intervalo apurado.

    Returns:
        Dicionário estruturado do snapshot oficial.

    Raises:
        ValueError: Se alguma commodity homologada não for encontrada ou tiver valor inválido.
    """
    itens = []
    for cid, nome, prod_orig, linha, unidade, unidade_orig in COMMODITIES_HOMOLOGADAS:
        linha_real = (linhas_por_id or {}).get(cid, linha)
        if linha_real not in valores_col_x:
            raise ValueError(f"Célula obrigatória da linha {linha_real} para commodity '{cid}' não encontrada no arquivo")

        raw_val = valores_col_x[linha_real]
        if raw_val <= 0:
            raise ValueError(f"Valor numérico inválido ({raw_val}) para commodity '{cid}' na linha {linha_real}")

        dec_val = float(Decimal(str(raw_val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        itens.append(
            {
                "id": cid,
                "commodityNome": nome,
                "produtoOriginal": prod_orig,
                "classificacao": f"{prod_orig} — preço médio recebido pelo produtor",
                "valor": dec_val,
                "valorOriginal": raw_val,
                "unidade": unidade,
                "unidadeOriginal": unidade_orig,
                "registroOriginal": f"Rav!X{linha_real}",
            }
        )

    return {
        "schemaVersion": 1,
        "fonte": "DERAL/SEAB-PR",
        "documentoOficial": DEFAULT_SOURCE_URL,
        "documentoHashSha256": hash_sha256,
        "tituloDocumento": "PREÇOS MÉDIOS SEMANAIS RECEBIDOS PELOS AGRICULTORES",
        "semana": semana,
        "periodo": periodo,
        "dataReferencia": data_referencia,
        "dataPublicacao": None,
        "planilha": "Rav",
        "colunaValor": "MÉDIA",
        "transformacaoAplicada": "Arredondamento decimal HALF_UP para 2 casas",
        "itens": itens,
    }


def validar_snapshot_pydantic(snapshot_dict: dict[str, object]) -> bool:
    """Valida a conformidade de todo o snapshot com as regras estritas do contrato.

    Args:
        snapshot_dict: Dicionário do snapshot construído.

    Returns:
        True se aprovado.

    Raises:
        ValueError: Se violar o schema ou regras numéricas.
    """
    snapshot = SnapshotDeral.model_validate(snapshot_dict)
    esperados = {item[0] for item in COMMODITIES_HOMOLOGADAS}
    recebidos = {item.id for item in snapshot.itens}
    if len(snapshot.itens) != 21 or recebidos != esperados:
        raise ValueError("Snapshot deve conter exatamente os 21 IDs homologados")
    return True


def executar_pipeline(
    url: str = DEFAULT_SOURCE_URL,
    arquivo_local: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Executa o ciclo completo de ingestão, validação e publicação atômica.

    Args:
        url: URL HTTPS do DERAL.
        arquivo_local: Caminho opcional para arquivo XLS local.
        output_dir: Diretório de destino dos snapshots.
        dry_run: Se True, apenas simula sem gravar no destino final.
        force: Se True, publica mesmo se o hash for idêntico ao ativo.

    Returns:
        0 se sucesso, 1 se erro.
    """
    inicio = datetime.now(timezone.utc)
    log_estruturado("INFO", "INICIO_ATUALIZACAO_DERAL", url=url, modo_local=bool(arquivo_local), dry_run=dry_run)

    try:
        # 1. Obtenção do arquivo e cálculo do SHA-256
        if arquivo_local:
            if not arquivo_local.exists():
                raise FileNotFoundError(f"Arquivo local não encontrado: {arquivo_local}")
            dados_binarios = arquivo_local.read_bytes()
            hash_sha256 = hashlib.sha256(dados_binarios).hexdigest()
        else:
            dados_binarios, hash_sha256 = baixar_arquivo_seguro(url)

        log_estruturado("INFO", "DOWNLOAD_CONCLUIDO", sha256=hash_sha256, bytes_total=len(dados_binarios))

        # 2. Validação estrutural e extração da média oficial
        valores_col_x = validar_estrutura_planilha(dados_binarios)
        log_estruturado("INFO", "PARSING_BIFF8_CONCLUIDO", celulas_encontradas=len(valores_col_x))

        # 3. Construção do snapshot estruturado com metadados da planilha
        semana, periodo, data_referencia = extrair_metadados_planilha(dados_binarios)
        snapshot = construir_snapshot(
            valores_col_x,
            hash_sha256,
            data_referencia,
            semana,
            periodo,
            _linhas_por_id(dados_binarios),
        )

        # 4. Validação estrita com Pydantic
        validar_snapshot_pydantic(snapshot)
        log_estruturado("INFO", "VALIDACAO_ESQUEMA_APROVADA", itens_validados=len(snapshot["itens"]))

        # 5. Verificação de defasagem temporal (alerta sem dados fictícios)
        data_ref = datetime.fromisoformat(str(snapshot["dataReferencia"])).date()
        dias_defasagem = (inicio.date() - data_ref).days
        if dias_defasagem > 10:
            log_estruturado(
                "WARN",
                "ALERTA_DEFASAGEM_TEMPORAL",
                data_referencia=str(snapshot["dataReferencia"]),
                dias_defasagem=dias_defasagem,
                mensagem="Snapshot possui mais de 10 dias úteis de defasagem. Preservando preços reais sem fabricar dados sintéticos.",
            )

        # 6. Gravação temporária e publicação atômica
        data_str = str(snapshot["dataReferencia"])
        destino_final = output_dir / f"deral-prp-{data_str}.json"

        if dry_run:
            log_estruturado("INFO", "DRY_RUN_CONCLUIDO", destino_planejado=str(destino_final), status="APROVADO")
            return 0

        if destino_final.exists() and not force:
            atual = json.loads(destino_final.read_text(encoding="utf-8"))
            if atual.get("documentoHashSha256") == hash_sha256:
                log_estruturado("INFO", "SNAPSHOT_JA_PUBLICADO", destino=str(destino_final))
                return 0
            raise FileExistsError("Snapshot da data já existe; use --force após revisão")

        # Grava em arquivo temporário no mesmo diretório (garante mesmo filesystem para rename atômico)
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=output_dir, prefix="snapshot-tmp-", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
            json.dump(snapshot, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")

        # Substituição atômica
        tmp_path.replace(destino_final)
        log_estruturado("INFO", "PUBLICACAO_ATOMICA_SUCESSO", destino=str(destino_final), hash_sha256=hash_sha256)
        return 0

    except Exception as exc:
        log_estruturado("ERROR", "FALHA_ATUALIZACAO_DERAL", erro=str(exc), tipo_erro=exc.__class__.__name__)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Atualizador seguro de snapshots DERAL/SEAB-PR.")
    parser.add_argument("--url", default=DEFAULT_SOURCE_URL, help="URL oficial do arquivo .xls")
    parser.add_argument("--local-file", type=Path, default=None, help="Caminho para arquivo .xls local")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Diretório de saída")
    parser.add_argument("--dry-run", action="store_true", help="Valida sem substituir o arquivo final")
    parser.add_argument("--force", action="store_true", help="Força substituição")
    args = parser.parse_args()

    exit_code = executar_pipeline(
        url=args.url,
        arquivo_local=args.local_file,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        force=args.force,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
