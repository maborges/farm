"""Leitura e geração segura de planilhas CSV, XLSX e XLS para Pecuária."""
# TODO(security): varredura antivírus/CDR dispensada pois arquivos são parseados
# apenas como dados tabulares em memória e descartados imediatamente sem persistência em disco.

from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.parsers import expat
from xml.sax.saxutils import escape as xml_escape

import xlrd

from core.exceptions import BusinessRuleError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
MAX_XLSX_ENTRIES = 200
MAX_IMPORT_ROWS = 5000
EXTENSOES_PERMITIDAS = frozenset({".csv", ".xlsx", ".xls"})

_MAGIC_ZIP = b"PK\x03\x04"
_MAGIC_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_RE_COL_REF = re.compile(r"^([A-Za-z]+)")
_RE_MOEDA_LIMPAR = re.compile(r"[Rr]\$\s*|\s+")
_EXCEL_DATE_IDS = frozenset({14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47})
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class PlanilhaBruta:
    """Representação tabular extraída em memória de um arquivo enviado."""

    headers: list[str]
    rows: list[tuple[int, dict[str, str]]]
    formato: str


def normalizar_texto_chave(texto: str) -> str:
    """Normaliza rótulos e identificadores para comparação tolerante a acentos."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acentos = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acentos.strip().lower())
    return limpo.strip("_")


def sanitizar_celula_csv(valor: object) -> str:
    """Neutraliza CSV/Excel formula injection preservando números puros."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return str(valor)
    texto = str(valor)
    if texto.startswith(_FORMULA_PREFIXES):
        return f"'{texto}"
    return texto


def validar_xml_seguro(conteudo: bytes) -> None:
    """Valida XML contra XXE, DTD, entidades externas e XInclude antes do parse.

    Args:
        conteudo: Conteúdo bruto XML extraído do pacote XLSX.

    Raises:
        BusinessRuleError: Se o XML contiver DOCTYPE, ENTITY, XInclude ou sintaxe inválida.
    """
    cabecalho = conteudo[:8192].lower()
    if b"<!doctype" in cabecalho or b"<!entity" in cabecalho or b"xi:include" in conteudo.lower():
        raise BusinessRuleError("Arquivo XLSX bloqueado por conter diretivas XML não permitidas.")

    def _bloquear(*_args: object, **_kwargs: object) -> int:
        raise BusinessRuleError("Arquivo XLSX bloqueado por conter DTD ou entidade externa.")

    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _bloquear
    parser.EntityDeclHandler = _bloquear
    parser.UnparsedEntityDeclHandler = _bloquear
    parser.ExternalEntityRefHandler = _bloquear
    try:
        parser.Parse(conteudo, True)
    except BusinessRuleError:
        raise
    except expat.ExpatError as exc:
        raise BusinessRuleError("Estrutura XML do arquivo XLSX é inválida.") from exc


def parse_float_br(raw: str | None) -> float | None:
    """Converte string numérica pt-BR ou EN para float."""
    if raw is None:
        return None
    limpo = _RE_MOEDA_LIMPAR.sub("", raw.strip())
    if not limpo:
        return None
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".") if limpo.rfind(",") > limpo.rfind(".") else limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", "") if limpo.count(",") > 1 else limpo.replace(",", ".")
    elif limpo.count(".") > 1:
        limpo = limpo.replace(".", "")
    try:
        return float(limpo)
    except ValueError as exc:
        raise ValueError(f"Valor numérico inválido: {raw}") from exc


def parse_int_br(raw: str | None) -> int | None:
    """Converte string inteira garantindo ausência de fração não zero."""
    valor = parse_float_br(raw)
    if valor is None:
        return None
    if not valor.is_integer():
        raise ValueError(f"Valor inteiro esperado, recebido '{raw}'.")
    return int(valor)


def parse_date_br(raw: str | None) -> date | None:
    """Converte string de data (DD/MM/YYYY, ISO ou serial Excel) para date."""
    if raw is None:
        return None
    texto = raw.strip()
    if not texto:
        return None
    if re.fullmatch(r"\d{5}(?:\.\d+)?", texto):
        serial = float(texto)
        if 20000 <= serial <= 80000:
            return _excel_serial_para_date(serial)
    candidato = texto.split("T", 1)[0].split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(candidato, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: '{raw}'. Use DD/MM/AAAA ou AAAA-MM-DD.")


def ler_planilha_bytes(
    filename: str,
    conteudo: bytes,
    *,
    max_rows: int = MAX_IMPORT_ROWS,
) -> PlanilhaBruta:
    """Lê e valida planilha CSV, XLSX ou XLS diretamente em memória.

    Args:
        filename: Nome original do arquivo enviado para validação da extensão.
        conteudo: Bytes completos do arquivo já limitado em tamanho.
        max_rows: Limite máximo de linhas de dados aceitas.

    Returns:
        PlanilhaBruta com cabeçalhos e linhas indexadas pelo número real na planilha.

    Raises:
        BusinessRuleError: Se extensão, magic bytes, segurança ou tamanho forem inválidos.
    """
    extensao = Path(filename or "").suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise BusinessRuleError("Formato não suportado. Envie arquivo .xlsx, .xls ou .csv.")
    if not conteudo:
        raise BusinessRuleError("O arquivo enviado está vazio.")
    if len(conteudo) > MAX_UPLOAD_BYTES:
        raise BusinessRuleError("O arquivo excede o limite máximo de 5 MB.")

    if extensao == ".csv":
        return _ler_csv(conteudo, max_rows=max_rows)
    if extensao == ".xlsx":
        return _ler_xlsx(conteudo, max_rows=max_rows)
    return _ler_xls(conteudo, max_rows=max_rows)


def gerar_csv_bytes(headers: list[str], linhas: list[list[object]]) -> bytes:
    """Gera arquivo CSV UTF-8 com BOM e delimitador ';' seguro contra fórmulas."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow([sanitizar_celula_csv(h) for h in headers])
    for linha in linhas:
        writer.writerow([sanitizar_celula_csv(cel) for cel in linha])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def gerar_xlsx_bytes(nome_aba: str, headers: list[str], linhas: list[list[object]]) -> bytes:
    """Gera arquivo XLSX mínimo válido em memória sem dependências externas."""
    aba_segura = xml_escape((nome_aba or "Dados")[:31])
    sheet_xml = _construir_worksheet_xml([headers, *linhas])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _XLSX_CONTENT_TYPES)
        zf.writestr("_rels/.rels", _XLSX_ROOT_RELS)
        zf.writestr("xl/workbook.xml", _XLSX_WORKBOOK_TEMPLATE.format(sheet_name=aba_segura))
        zf.writestr("xl/_rels/workbook.xml.rels", _XLSX_WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def _ler_csv(conteudo: bytes, *, max_rows: int) -> PlanilhaBruta:
    if b"\x00" in conteudo or conteudo.startswith(_MAGIC_ZIP) or conteudo.startswith(_MAGIC_OLE):
        raise BusinessRuleError("Arquivo CSV inválido ou corrompido.")
    texto = _decodificar_texto(conteudo)
    linhas_texto = [ln for ln in texto.splitlines() if ln.strip()]
    if not linhas_texto:
        raise BusinessRuleError("A planilha CSV não contém linhas de dados.")
    delimitador = _detectar_delimitador_csv(linhas_texto[0])
    leitor = csv.reader(io.StringIO("\n".join(linhas_texto)), delimiter=delimitador)
    matriz = [[cel.strip() for cel in row] for row in leitor if any(cel.strip() for cel in row)]
    return _montar_planilha_bruta(matriz, formato="csv", max_rows=max_rows)


def _decodificar_texto(conteudo: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BusinessRuleError("Não foi possível decodificar o arquivo CSV.")


def _detectar_delimitador_csv(cabecalho: str) -> str:
    candidatos = [";", ",", "\t"]
    melhor = max(candidatos, key=lambda sep: cabecalho.count(sep))
    return melhor if cabecalho.count(melhor) > 0 else ";"


def _ler_xlsx(conteudo: bytes, *, max_rows: int) -> PlanilhaBruta:
    if not conteudo.startswith(_MAGIC_ZIP):
        raise BusinessRuleError("Arquivo .xlsx inválido (assinatura ZIP ausente).")
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo), "r") as zf:
            infos = _validar_membros_zip(zf)
            shared_strings = _ler_shared_strings(zf, infos)
            date_styles = _ler_estilos_data(zf, infos)
            sheet_path = _resolver_caminho_primeira_aba(zf, infos)
            sheet_bytes = _ler_membro_zip_seguro(zf, infos[sheet_path])
            validar_xml_seguro(sheet_bytes)
            matriz = _parsear_worksheet_xml(sheet_bytes, shared_strings, date_styles, max_rows=max_rows)
            return _montar_planilha_bruta(matriz, formato="xlsx", max_rows=max_rows)
    except zipfile.BadZipFile as exc:
        raise BusinessRuleError("Arquivo .xlsx inválido ou corrompido.") from exc


def _validar_membros_zip(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = zf.infolist()
    if len(infos) > MAX_XLSX_ENTRIES:
        raise BusinessRuleError("Arquivo .xlsx excede o limite de entradas permitidas.")
    total_descomprimido = 0
    mapa: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        nome = info.filename
        if "\\" in nome or nome.startswith("/") or ".." in Path(nome).parts:
            raise BusinessRuleError("Arquivo .xlsx rejeitado por caminho interno inválido.")
        total_descomprimido += max(0, info.file_size)
        if total_descomprimido > MAX_XLSX_UNCOMPRESSED_BYTES:
            raise BusinessRuleError("Arquivo .xlsx excede o limite descomprimido permitido.")
        mapa[nome] = info
    return mapa


def _ler_membro_zip_seguro(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    with zf.open(info, "r") as handle:
        dados = handle.read(MAX_XLSX_UNCOMPRESSED_BYTES + 1)
    if len(dados) > MAX_XLSX_UNCOMPRESSED_BYTES:
        raise BusinessRuleError("Entrada XML do .xlsx excede o tamanho seguro permitido.")
    return dados


def _ler_shared_strings(zf: zipfile.ZipFile, infos: dict[str, zipfile.ZipInfo]) -> list[str]:
    info = infos.get("xl/sharedStrings.xml")
    if info is None:
        return []
    raw = _ler_membro_zip_seguro(zf, info)
    validar_xml_seguro(raw)
    root = ET.fromstring(raw)
    strings: list[str] = []
    for si in root:
        if _local_tag(si.tag) != "si":
            continue
        partes = [elem.text or "" for elem in si.iter() if _local_tag(elem.tag) == "t"]
        strings.append("".join(partes))
    return strings


def _ler_estilos_data(zf: zipfile.ZipFile, infos: dict[str, zipfile.ZipInfo]) -> set[int]:
    info = infos.get("xl/styles.xml")
    if info is None:
        return set()
    raw = _ler_membro_zip_seguro(zf, info)
    validar_xml_seguro(raw)
    root = ET.fromstring(raw)
    custom_date_ids = _extrair_custom_date_fmt_ids(root)
    date_indices: set[int] = set()
    for elem in root.iter():
        if _local_tag(elem.tag) != "cellXfs":
            continue
        for idx, xf in enumerate(elem):
            if _local_tag(xf.tag) != "xf":
                continue
            fmt_id = int(xf.attrib.get("numFmtId", "0") or 0)
            if fmt_id in _EXCEL_DATE_IDS or fmt_id in custom_date_ids:
                date_indices.add(idx)
    return date_indices


def _extrair_custom_date_fmt_ids(root: ET.Element) -> set[int]:
    ids: set[int] = set()
    for elem in root.iter():
        if _local_tag(elem.tag) != "numFmt":
            continue
        code = (elem.attrib.get("formatCode") or "").lower()
        fmt_id = elem.attrib.get("numFmtId")
        if fmt_id and fmt_id.isdigit() and ("yy" in code or "dd" in code) and "h" not in code.replace("[h]", ""):
            ids.add(int(fmt_id))
    return ids


def _resolver_caminho_primeira_aba(zf: zipfile.ZipFile, infos: dict[str, zipfile.ZipInfo]) -> str:
    fallback = "xl/worksheets/sheet1.xml"
    wb_info = infos.get("xl/workbook.xml")
    rels_info = infos.get("xl/_rels/workbook.xml.rels")
    if wb_info is None or rels_info is None:
        if fallback not in infos:
            raise BusinessRuleError("Planilha não encontrada dentro do arquivo .xlsx.")
        return fallback
    wb_raw = _ler_membro_zip_seguro(zf, wb_info)
    rels_raw = _ler_membro_zip_seguro(zf, rels_info)
    validar_xml_seguro(wb_raw)
    validar_xml_seguro(rels_raw)
    r_id = _extrair_primeiro_sheet_rid(ET.fromstring(wb_raw))
    target = _mapear_rels(ET.fromstring(rels_raw)).get(r_id or "") if r_id else None
    if target:
        normalizado = f"xl/{target.lstrip('/')}" if not target.startswith("xl/") else target
        if normalizado in infos:
            return normalizado
    if fallback not in infos:
        raise BusinessRuleError("Planilha principal ausente no arquivo .xlsx.")
    return fallback


def _extrair_primeiro_sheet_rid(root: ET.Element) -> str | None:
    for elem in root.iter():
        if _local_tag(elem.tag) == "sheet":
            for chave, valor in elem.attrib.items():
                if chave == "r:id" or chave.endswith("}id"):
                    return valor
    return None


def _mapear_rels(root: ET.Element) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for elem in root.iter():
        if _local_tag(elem.tag) == "Relationship":
            rid = elem.attrib.get("Id")
            target = elem.attrib.get("Target")
            if rid and target:
                mapa[rid] = target
    return mapa


def _parsear_worksheet_xml(
    raw: bytes,
    shared_strings: list[str],
    date_styles: set[int],
    *,
    max_rows: int,
) -> list[list[str]]:
    root = ET.fromstring(raw)
    matriz: list[list[str]] = []
    for elem in root.iter():
        if _local_tag(elem.tag) != "row":
            continue
        linha = _parsear_linha_xlsx(elem, shared_strings, date_styles)
        if any(cel != "" for cel in linha):
            matriz.append(linha)
            if len(matriz) > max_rows + 1:
                raise BusinessRuleError(
                    f"Planilha excede o limite de {max_rows} linhas de dados por importação."
                )
    return matriz


def _parsear_linha_xlsx(
    row_elem: ET.Element,
    shared_strings: list[str],
    date_styles: set[int],
) -> list[str]:
    valores: list[str] = []
    for cel in row_elem:
        if _local_tag(cel.tag) != "c":
            continue
        idx = _col_ref_para_indice(cel.attrib.get("r"), len(valores))
        while len(valores) <= idx:
            valores.append("")
        valores[idx] = _extrair_valor_celula_xlsx(cel, shared_strings, date_styles)
    return valores


def _extrair_valor_celula_xlsx(
    cel: ET.Element,
    shared_strings: list[str],
    date_styles: set[int],
) -> str:
    tipo = cel.attrib.get("t", "n")
    estilo = cel.attrib.get("s")
    if tipo == "inlineStr":
        return "".join(t.text or "" for t in cel.iter() if _local_tag(t.tag) == "t").strip()
    val_elem = next((c for c in cel if _local_tag(c.tag) == "v"), None)
    if val_elem is None or val_elem.text is None:
        return ""
    bruto = val_elem.text.strip()
    if tipo == "s":
        pos = int(bruto) if bruto.isdigit() else -1
        return shared_strings[pos].strip() if 0 <= pos < len(shared_strings) else ""
    if tipo == "b":
        return "TRUE" if bruto == "1" else "FALSE"
    if tipo in ("n", "") and estilo and estilo.isdigit() and int(estilo) in date_styles:
        try:
            return _excel_serial_para_date(float(bruto)).isoformat()
        except ValueError:
            pass
    return _normalizar_numero_excel_str(bruto) if tipo in ("n", "") else bruto


def _normalizar_numero_excel_str(bruto: str) -> str:
    try:
        num = float(bruto)
        if num.is_integer():
            return str(int(num))
    except ValueError:
        pass
    return bruto


def _col_ref_para_indice(ref: str | None, fallback: int) -> int:
    if not ref:
        return fallback
    match = _RE_COL_REF.match(ref)
    if not match:
        return fallback
    idx = 0
    for ch in match.group(1).upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def _excel_serial_para_date(serial: float) -> date:
    if serial < 1 or serial > 2958465:
        raise ValueError("Serial Excel fora da faixa de datas.")
    return date(1899, 12, 30) + timedelta(days=int(serial))


def _ler_xls(conteudo: bytes, *, max_rows: int) -> PlanilhaBruta:
    if not conteudo.startswith(_MAGIC_OLE):
        raise BusinessRuleError("Arquivo .xls inválido (assinatura OLE2 ausente).")
    try:
        book = xlrd.open_workbook(file_contents=conteudo, on_demand=True)
        if book.nsheets < 1:
            raise BusinessRuleError("Arquivo .xls sem abas visíveis.")
        sheet = book.sheet_by_index(0)
        if sheet.nrows > max_rows + 1:
            raise BusinessRuleError(
                f"Planilha excede o limite de {max_rows} linhas de dados por importação."
            )
        matriz: list[list[str]] = []
        for row_idx in range(sheet.nrows):
            linha = [_ler_celula_xls(sheet.cell(row_idx, c), book.datemode) for c in range(sheet.ncols)]
            if any(cel != "" for cel in linha):
                matriz.append(linha)
        return _montar_planilha_bruta(matriz, formato="xls", max_rows=max_rows)
    except BusinessRuleError:
        raise
    except Exception as exc:
        raise BusinessRuleError("Não foi possível ler o arquivo .xls enviado.") from exc


def _ler_celula_xls(cell: xlrd.sheet.Cell, datemode: int) -> str:
    if cell.ctype == xlrd.XL_CELL_EMPTY:
        return ""
    if cell.ctype == xlrd.XL_CELL_DATE:
        tupla = xlrd.xldate_as_tuple(float(cell.value), datemode)
        return date(tupla[0], tupla[1], tupla[2]).isoformat()
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        num = float(cell.value)
        return str(int(num)) if num.is_integer() else str(num)
    if cell.ctype == xlrd.XL_CELL_BOOLEAN:
        return "TRUE" if cell.value else "FALSE"
    return str(cell.value).strip()


def _montar_planilha_bruta(
    matriz: list[list[str]],
    *,
    formato: str,
    max_rows: int,
) -> PlanilhaBruta:
    if not matriz:
        raise BusinessRuleError("A planilha enviada não contém cabeçalhos.")
    raw_headers = matriz[0]
    headers = [h.strip() for h in raw_headers if h.strip()]
    if not headers:
        raise BusinessRuleError("A primeira linha da planilha precisa conter os nomes das colunas.")
    if len(matriz) - 1 > max_rows:
        raise BusinessRuleError(
            f"Planilha excede o limite de {max_rows} linhas de dados por importação."
        )
    rows: list[tuple[int, dict[str, str]]] = []
    for idx, valores in enumerate(matriz[1:], start=2):
        registro = {
            cab: (valores[col_idx].strip() if col_idx < len(valores) else "")
            for col_idx, cab in enumerate(raw_headers)
            if cab.strip()
        }
        if any(valor != "" for valor in registro.values()):
            rows.append((idx, registro))
    if not rows:
        raise BusinessRuleError("A planilha não possui linhas de dados abaixo do cabeçalho.")
    return PlanilhaBruta(headers=headers, rows=rows, formato=formato)


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _indice_para_col_ref(idx_zero: int) -> str:
    resultado = ""
    num = idx_zero + 1
    while num > 0:
        num, rem = divmod(num - 1, 26)
        resultado = chr(65 + rem) + resultado
    return resultado


def _construir_worksheet_xml(matriz: list[list[object]]) -> str:
    partes = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    for row_num, linha in enumerate(matriz, start=1):
        partes.append(f'<row r="{row_num}">')
        for col_idx, valor in enumerate(linha):
            if valor is None or valor == "":
                continue
            ref = f"{_indice_para_col_ref(col_idx)}{row_num}"
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                partes.append(f'<c r="{ref}" t="n"><v>{valor}</v></c>')
            else:
                texto = xml_escape(sanitizar_celula_csv(valor))
                partes.append(f'<c r="{ref}" t="inlineStr"><is><t>{texto}</t></is></c>')
        partes.append("</row>")
    partes.append("</sheetData></worksheet>")
    return "".join(partes)


_XLSX_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    "</Types>"
)

_XLSX_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/>'
    "</Relationships>"
)

_XLSX_WORKBOOK_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
    "</workbook>"
)

_XLSX_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
    'Target="worksheets/sheet1.xml"/>'
    "</Relationships>"
)
