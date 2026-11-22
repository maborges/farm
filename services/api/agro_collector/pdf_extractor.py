"""Extrator seguro de texto em documentos PDF (pypdf opcional + fallback stdlib anti-zip-bomb)."""

from __future__ import annotations

import importlib.util
import io
import re
import zlib

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_STREAM_DECOMPRESSED_BYTES = 2 * 1024 * 1024
MAX_TOTAL_EXTRACTED_CHARS = 250_000


class PdfExtractionError(ValueError):
    """Erro lançado quando o arquivo PDF é inválido, corrompido ou sem texto."""


def _decode_pdf_literal(raw_token: bytes) -> str:
    """Decodifica escapes e octais de string literal PDF em texto legível."""
    out = bytearray()
    i = 0
    n = len(raw_token)
    escape_map = {
        ord("n"): ord("\n"),
        ord("r"): ord("\n"),
        ord("t"): ord("\t"),
        ord("b"): ord("\b"),
        ord("f"): ord("\f"),
        ord("("): ord("("),
        ord(")"): ord(")"),
        ord("\\"): ord("\\"),
    }
    while i < n:
        ch = raw_token[i]
        if ch == ord("\\") and i + 1 < n:
            nxt = raw_token[i + 1]
            if nxt in escape_map:
                out.append(escape_map[nxt])
                i += 2
                continue
            if nxt in (ord("\r"), ord("\n")):
                i += 2
                if nxt == ord("\r") and i < n and raw_token[i] == ord("\n"):
                    i += 1
                continue
            if ord("0") <= nxt <= ord("7"):
                oct_digits = raw_token[i + 1 : i + 4]
                m_oct = re.match(rb"[0-7]{1,3}", oct_digits)
                if m_oct:
                    out.append(int(m_oct.group(0), 8) & 0xFF)
                    i += 1 + len(m_oct.group(0))
                    continue
        out.append(ch)
        i += 1
    return bytes(out).decode("cp1252", errors="ignore")


def _extract_tj_array_text(array_body: bytes) -> str:
    """Extrai texto de array operador ``[...] TJ`` preservando espaçamento por kerning."""
    parts: list[str] = []
    pos = 0
    n = len(array_body)
    token_re = re.compile(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)|(-?\d+(?:\.\d+)?)")
    for m in token_re.finditer(array_body[pos:n]):
        if m.group(1) is not None:
            parts.append(_decode_pdf_literal(m.group(1)))
        elif m.group(2) is not None:
            try:
                kern = float(m.group(2))
            except ValueError:
                kern = 0.0
            if kern <= -120.0 and parts and not parts[-1].endswith((" ", "\n")):
                parts.append(" ")
    return "".join(parts)


def _extract_stream_text(content: bytes) -> str:
    """Converte operadores ``BT ... ET`` de um stream PDF em linhas normalizadas."""
    if b"BT" not in content:
        return ""
    fragments: list[str] = []
    op_re = re.compile(
        rb"\[((?:[^\[\]\\]|\\.|\[[^\]]*\])*)\]\s*TJ|"
        rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*Tj|"
        rb"\b(T\*|Td|TD|ET)\b",
        re.S,
    )
    for m in op_re.finditer(content):
        if m.group(1) is not None:
            fragments.append(_extract_tj_array_text(m.group(1)))
        elif m.group(2) is not None:
            fragments.append(_decode_pdf_literal(m.group(2)))
        elif m.group(3) in {b"T*", b"Td", b"TD", b"ET"}:
            if fragments and not fragments[-1].endswith(("\n", " ")):
                fragments.append(" ")
    joined = re.sub(r"[ \t]+", " ", "".join(fragments))
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def _extract_with_stdlib(pdf_bytes: bytes, *, max_pages: int) -> str:
    """Fallback nativo stdlib para extração de texto em PDFs FlateDecode/plain."""
    stream_texts: list[str] = []
    stream_re = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
    for match in stream_re.finditer(pdf_bytes):
        raw_stream = match.group(1)
        decompressed: bytes | None = None
        if b"BT" in raw_stream and (b"Tj" in raw_stream or b"TJ" in raw_stream):
            decompressed = raw_stream
        else:
            try:
                decomp = zlib.decompressobj()
                decompressed = decomp.decompress(raw_stream, MAX_STREAM_DECOMPRESSED_BYTES)
                if decomp.unconsumed_tail:
                    continue
            except zlib.error:
                continue
        txt = _extract_stream_text(decompressed)
        if len(txt) >= 15:
            stream_texts.append(txt)
            if len(stream_texts) >= max_pages * 3:
                break
    return "\n".join(stream_texts).strip()


def extract_text_from_pdf(pdf_bytes: bytes, *, max_pages: int = 30) -> str:
    """Extrai texto legível de um PDF institucional validando assinatura e limites.

    Args:
        pdf_bytes: Conteúdo binário do PDF baixado.
        max_pages: Limite máximo de páginas/blocos processados.

    Returns:
        Texto consolidado extraído do PDF (limitado a ``MAX_TOTAL_EXTRACTED_CHARS``).

    Raises:
        PdfExtractionError: Se não for um PDF válido, exceder limite ou não houver texto.
    """
    if not pdf_bytes or not pdf_bytes[:16].lstrip().startswith(b"%PDF-"):
        raise PdfExtractionError("Conteúdo recebido não possui assinatura %PDF- válida.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise PdfExtractionError(
            f"PDF excede tamanho máximo suportado ({MAX_PDF_BYTES} bytes)."
        )

    extracted = ""
    if importlib.util.find_spec("pypdf") is not None:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [page.extract_text() or "" for page in reader.pages[:max_pages]]
        extracted = "\n".join(p.strip() for p in pages if p.strip())

    if not extracted:
        extracted = _extract_with_stdlib(pdf_bytes, max_pages=max_pages)

    cleaned = re.sub(r"\s+", " ", extracted).strip()
    if len(cleaned) < 20:
        raise PdfExtractionError(
            "PDF não possui texto extraível legível (possível PDF escaneado sem OCR)."
        )
    return extracted[:MAX_TOTAL_EXTRACTED_CHARS]
