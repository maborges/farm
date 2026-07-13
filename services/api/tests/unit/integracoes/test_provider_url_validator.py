import socket

import pytest

from integracoes.url_validator import InvalidProviderURLError, validate_provider_url


@pytest.fixture
def mock_dns(monkeypatch):
    def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Mapeamento para os testes
        if host == "public.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        elif host == "private.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
        elif host == "loopback.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        elif host == "linklocal.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]
        elif host == "ipv6-loopback.com":
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 443))]
        elif host == "timeout.com":
            raise TimeoutError("DNS Timeout")
        elif host == "nxdomain.com":
            raise socket.gaierror("Name or service not known")

        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)


@pytest.mark.asyncio
async def test_valid_public_https(mock_dns):
    url = await validate_provider_url("https://public.com/api")
    assert url == "https://public.com/api"


@pytest.mark.asyncio
async def test_normalizes_trailing_slash(mock_dns):
    url = await validate_provider_url("https://public.com/api/")
    assert url == "https://public.com/api"


@pytest.mark.asyncio
async def test_rejects_private_ip_host(mock_dns):
    with pytest.raises(InvalidProviderURLError, match="resolve para um IP privado não permitido"):
        await validate_provider_url("https://private.com/api")


@pytest.mark.asyncio
async def test_rejects_loopback(mock_dns):
    with pytest.raises(
        InvalidProviderURLError, match="resolve para um IP de loopback não permitido"
    ):
        await validate_provider_url("https://loopback.com/api")


@pytest.mark.asyncio
async def test_rejects_ipv6_loopback(mock_dns):
    with pytest.raises(
        InvalidProviderURLError, match="resolve para um IP de loopback não permitido"
    ):
        await validate_provider_url("https://ipv6-loopback.com/api")


@pytest.mark.asyncio
async def test_rejects_linklocal_metadata(mock_dns):
    with pytest.raises(
        InvalidProviderURLError, match="resolve para um IP link-local não permitido"
    ):
        await validate_provider_url("https://linklocal.com/latest/meta-data")


@pytest.mark.asyncio
async def test_rejects_userinfo(mock_dns):
    with pytest.raises(InvalidProviderURLError, match="não deve conter credenciais"):
        await validate_provider_url("https://user:pass@public.com/api")


@pytest.mark.asyncio
async def test_rejects_invalid_protocol(mock_dns):
    with pytest.raises(InvalidProviderURLError, match="O protocolo 'ftp' não é permitido"):
        await validate_provider_url("ftp://public.com/file")


@pytest.mark.asyncio
async def test_allows_ws_wss(mock_dns):
    assert await validate_provider_url("wss://public.com/ws") == "wss://public.com/ws"
    assert await validate_provider_url("ws://public.com/ws") == "ws://public.com/ws"


@pytest.mark.asyncio
async def test_dns_timeout_is_caught(mock_dns):
    with pytest.raises(InvalidProviderURLError, match="Timeout na resolução DNS"):
        await validate_provider_url("https://timeout.com/api")


@pytest.mark.asyncio
async def test_nxdomain_is_caught(mock_dns):
    with pytest.raises(
        InvalidProviderURLError, match="Não foi possível resolver o hostname nxdomain.com"
    ):
        await validate_provider_url("https://nxdomain.com/api")


@pytest.mark.asyncio
async def test_empty_or_none_returns_none():
    assert await validate_provider_url(None) is None
    assert await validate_provider_url("") is None
    assert await validate_provider_url("   ") is None
