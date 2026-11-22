"""Fetcher HTTP seguro (anti-SSRF, TLS estrito e limite de payload) e compressão gzip."""

from __future__ import annotations

import gzip
import hashlib
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlencode, urljoin, urlsplit

import httpx

from .contracts import FetchResult

DEFAULT_MAX_BYTES = 15 * 1024 * 1024
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT_SEC = 25.0
DEFAULT_USER_AGENT = "DeepFarms-AgroCollector/1.0 (+https://deepfarms.com.br)"
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_T = TypeVar("_T")


class UnsafeSourceUrlError(ValueError):
    """Erro lançado quando uma URL viola HTTPS, whitelist ou proteção anti-SSRF."""


class PayloadTooLargeError(ValueError):
    """Erro lançado quando o documento excede o limite de bytes permitido."""


def compute_sha256(data: bytes) -> str:
    """Calcula hash SHA-256 hexadecimal do conteúdo bruto.

    Args:
        data: Conteúdo binário baixado.

    Returns:
        Digest hexadecimal SHA-256 com 64 caracteres.
    """
    return hashlib.sha256(data).hexdigest()


def compress_artifact(data: bytes) -> bytes:
    """Comprime payload binário em formato gzip para armazenamento forense.

    Args:
        data: Bytes originais do arquivo coletado.

    Returns:
        Bytes comprimidos em gzip.
    """
    return gzip.compress(data, compresslevel=6)


def decompress_artifact(data: bytes) -> bytes:
    """Descomprime payload gzip recuperado de ``agro_ingestion_artifacts``.

    Args:
        data: Bytes comprimidos em gzip.

    Returns:
        Bytes originais restaurados.
    """
    return gzip.decompress(data)


def _is_host_in_whitelist(hostname: str, whitelist: Sequence[str]) -> bool:
    host_norm = hostname.lower().rstrip(".")
    for raw_domain in whitelist:
        domain = str(raw_domain).strip().lower().lstrip("*.") .rstrip(".")
        if not domain:
            continue
        if host_norm == domain or host_norm.endswith(f".{domain}"):
            return True
    return False


def _assert_global_ip(address_text: str) -> None:
    ip = ipaddress.ip_address(address_text.split("%")[0])
    is_public = (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
    )
    if not is_public:
        raise UnsafeSourceUrlError(
            f"Endereço IP resolvido não público bloqueado (anti-SSRF): {ip}"
        )


def _resolve_and_validate_dns(hostname: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeSourceUrlError(f"Falha ao resolver DNS de {hostname}: {exc}") from exc
    if not infos:
        raise UnsafeSourceUrlError(f"DNS vazio para {hostname}")
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            _assert_global_ip(str(sockaddr[0]))


def validate_source_url(
    url: str,
    whitelist: Sequence[str],
    *,
    resolve_dns: bool = True,
) -> str:
    """Valida URL institucional contra esquema inseguro, SSRF e desvio de domínio.

    Args:
        url: URL candidata a requisição HTTP.
        whitelist: Lista de domínios autorizados para a fonte.
        resolve_dns: Quando True, resolve DNS e bloqueia IPs não públicos.

    Returns:
        URL normalizada validada.

    Raises:
        UnsafeSourceUrlError: Se a URL violar HTTPS, whitelist, IP literal ou SSRF.
    """
    cleaned = str(url or "").strip()
    if not cleaned:
        raise UnsafeSourceUrlError("URL da fonte não pode ser vazia.")
    parsed = urlsplit(cleaned)
    if parsed.scheme.lower() != "https":
        raise UnsafeSourceUrlError("Apenas URLs HTTPS são permitidas para coleta externa.")
    if parsed.username or parsed.password:
        raise UnsafeSourceUrlError("Credenciais embutidas na URL são estritamente proibidas.")
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeSourceUrlError("URL sem hostname válido.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise UnsafeSourceUrlError("IP literal na URL é proibido por política anti-SSRF.")
    if not whitelist or not _is_host_in_whitelist(hostname, whitelist):
        raise UnsafeSourceUrlError(
            f"Hostname '{hostname}' não pertence à whitelist autorizada da fonte."
        )
    if resolve_dns:
        _resolve_and_validate_dns(hostname, parsed.port or 443)
    return cleaned


def _extract_filename(url: str, response: httpx.Response) -> str:
    cd = response.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        candidate = cd.split("filename=", 1)[1].split(";")[0].strip().strip('"').strip("'")
        if candidate:
            return Path(candidate).name[:255]
    path_name = Path(urlsplit(url).path).name
    return (path_name or "payload.bin")[:255]


async def _read_bounded_body(response: httpx.Response, max_bytes: int) -> bytes:
    declared_len = response.headers.get("Content-Length")
    if declared_len and declared_len.isdigit() and int(declared_len) > max_bytes:
        raise PayloadTooLargeError(
            f"Content-Length ({declared_len}) excede o máximo permitido ({max_bytes} bytes)."
        )
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError(
                f"Resposta excedeu limite máximo de {max_bytes} bytes durante streaming."
            )
        chunks.append(chunk)
    return b"".join(chunks)


class SafeHttpFetcher:
    """Cliente HTTP assíncrono seguro com validação TLS, redirects e teto de payload."""

    def __init__(
        self,
        *,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        max_bytes: int = DEFAULT_MAX_BYTES,
        resolve_dns: bool = True,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.timeout_sec = timeout_sec
        self.max_bytes = max_bytes
        self.resolve_dns = resolve_dns
        self._client_factory = client_factory

    def _build_client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        return httpx.AsyncClient(
            verify=True,
            follow_redirects=False,
            timeout=httpx.Timeout(self.timeout_sec),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    async def _send_with_redirects(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        whitelist: Sequence[str],
        **request_kwargs: Any,
    ) -> tuple[str, httpx.Response, bytes]:
        current_url = validate_source_url(url, whitelist, resolve_dns=self.resolve_dns)
        for _ in range(MAX_REDIRECTS + 1):
            async with client.stream(method, current_url, **request_kwargs) as resp:
                if resp.status_code in _REDIRECT_CODES:
                    location = resp.headers.get("Location")
                    if not location:
                        raise UnsafeSourceUrlError("Redirect sem cabeçalho Location.")
                    next_url = urljoin(current_url, location)
                    current_url = validate_source_url(
                        next_url, whitelist, resolve_dns=self.resolve_dns
                    )
                    method = "GET"
                    request_kwargs = {}
                    continue
                if resp.status_code == 304:
                    return current_url, resp, b""
                resp.raise_for_status()
                body = await _read_bounded_body(resp, self.max_bytes)
                return current_url, resp, body
        raise UnsafeSourceUrlError(f"Excedido limite de {MAX_REDIRECTS} redirecionamentos.")

    async def fetch(
        self,
        url: str,
        whitelist: Sequence[str],
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """Executa GET seguro com suporte a ETag/If-Modified-Since e validação de redirects.

        Args:
            url: URL de destino na whitelist.
            whitelist: Domínios autorizados da fonte.
            etag: ETag anterior para envio em ``If-None-Match``.
            last_modified: Data HTTP anterior para ``If-Modified-Since``.
            headers: Cabeçalhos extras opcionais.

        Returns:
            ``FetchResult`` com bytes, headers de cache e SHA-256.
        """
        req_headers = dict(headers or {})
        if etag:
            req_headers["If-None-Match"] = etag
        if last_modified:
            req_headers["If-Modified-Since"] = last_modified
        async with self._build_client() as client:
            final_url, resp, body = await self._send_with_redirects(
                client, "GET", url, whitelist, headers=req_headers
            )
            return self._to_fetch_result(final_url, resp, body)

    async def fetch_form_post(
        self,
        get_url: str,
        post_url: str,
        whitelist: Sequence[str],
        *,
        form_builder: Callable[[str], dict[str, str] | list[tuple[str, str]]],
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[FetchResult, FetchResult]:
        """Executa GET para cookies/token e POST em formulário na mesma sessão segura.

        Args:
            get_url: URL inicial que entrega o formulário HTML e cookies.
            post_url: URL de submissão validada na mesma whitelist.
            whitelist: Domínios autorizados da fonte.
            form_builder: Função que recebe o HTML do GET e retorna pares form-urlencoded.
            extra_headers: Cabeçalhos extras para o POST (ex: X-Requested-With).

        Returns:
            Tupla ``(resultado_get, resultado_post)``.
        """
        validate_source_url(get_url, whitelist, resolve_dns=self.resolve_dns)
        validate_source_url(post_url, whitelist, resolve_dns=self.resolve_dns)
        async with self._build_client() as client:
            g_url, g_resp, g_body = await self._send_with_redirects(
                client, "GET", get_url, whitelist
            )
            g_result = self._to_fetch_result(g_url, g_resp, g_body)
            form_data = form_builder(g_body.decode("utf-8", errors="replace"))
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                **dict(extra_headers or {}),
            }
            encoded_body = urlencode(form_data).encode("utf-8")
            p_url, p_resp, p_body = await self._send_with_redirects(
                client,
                "POST",
                post_url,
                whitelist,
                content=encoded_body,
                headers=post_headers,
            )
            p_result = self._to_fetch_result(p_url, p_resp, p_body)
            return g_result, p_result

    async def run_session(
        self,
        whitelist: Sequence[str],
        runner: Callable[[SafeHttpSession], Awaitable[_T]],
    ) -> _T:
        """Executa múltiplas requisições GET/POST na mesma sessão cookie segura.

        Args:
            whitelist: Domínios autorizados aplicados em cada passo da sessão.
            runner: Corrotina que recebe ``SafeHttpSession`` com validação SSRF ativa.

        Returns:
            Resultado arbitrário produzido pela corrotina ``runner``.
        """
        async with self._build_client() as client:
            session = SafeHttpSession(self, client, whitelist)
            return await runner(session)

    def _to_fetch_result(
        self,
        final_url: str,
        resp: httpx.Response,
        body: bytes,
    ) -> FetchResult:
        is_not_modified = resp.status_code == 304
        sha = "" if is_not_modified else compute_sha256(body)
        return FetchResult(
            url_efetiva=final_url,
            http_status=resp.status_code,
            content=body,
            content_type=resp.headers.get("Content-Type"),
            etag=resp.headers.get("ETag"),
            last_modified=resp.headers.get("Last-Modified"),
            sha256=sha,
            tamanho_bytes=len(body),
            not_modified=is_not_modified,
            filename=_extract_filename(final_url, resp),
        )


class SafeHttpSession:
    """Sessão HTTP autenticada por cookies sujeita a anti-SSRF em cada chamada."""

    def __init__(
        self,
        fetcher: SafeHttpFetcher,
        client: httpx.AsyncClient,
        whitelist: Sequence[str],
    ) -> None:
        self._fetcher = fetcher
        self._client = client
        self._whitelist = whitelist

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """Executa GET validado mantendo cookies na sessão."""
        f_url, resp, body = await self._fetcher._send_with_redirects(
            self._client, "GET", url, self._whitelist, headers=dict(headers or {})
        )
        return self._fetcher._to_fetch_result(f_url, resp, body)

    async def post_form(
        self,
        url: str,
        data: dict[str, str] | list[tuple[str, str]],
        *,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        """Executa POST form-urlencoded validado mantendo cookies da sessão."""
        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            **dict(headers or {}),
        }
        encoded_body = urlencode(data).encode("utf-8")
        f_url, resp, body = await self._fetcher._send_with_redirects(
            self._client,
            "POST",
            url,
            self._whitelist,
            content=encoded_body,
            headers=post_headers,
        )
        return self._fetcher._to_fetch_result(f_url, resp, body)
