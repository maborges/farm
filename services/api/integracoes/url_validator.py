"""Validador central de URLs de integração contra SSRF (Política A)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import anyio


class InvalidProviderURLError(ValueError):
    """Exceção levantada quando a URL do provedor viola as políticas de segurança."""

    pass


async def validate_provider_url(value: str | None, field_name: str = "url") -> str | None:
    """
    Valida e normaliza a URL do provedor ERP garantindo a Política A contra SSRF.

    - Rejeita URLs com userinfo (username:password).
    - Permite apenas http, https, ws, wss.
    - Normaliza removendo trailing slashes.
    - Resolve o DNS do host e rejeita ativamente caso resolva para IPs privados,
      loopback, link-local ou metadados de nuvem.
    """
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        parsed = urlparse(value)
    except Exception:
        raise InvalidProviderURLError(f"O formato da URL no campo {field_name} é inválido.")

    if parsed.scheme not in ("http", "https", "ws", "wss"):
        raise InvalidProviderURLError(
            f"O protocolo '{parsed.scheme}' não é permitido em {field_name}."
        )

    if parsed.username or parsed.password:
        raise InvalidProviderURLError(f"A URL no campo {field_name} não deve conter credenciais.")

    hostname = parsed.hostname
    if not hostname:
        raise InvalidProviderURLError(f"O host não foi informado no campo {field_name}.")

    # Resolve o DNS via anyio/trio para não bloquear o event loop
    try:
        # Pega a porta padrao para nao falhar a resolução se porta vazia
        port = parsed.port or (443 if parsed.scheme in ("https", "wss") else 80)
        with anyio.fail_after(5.0):  # 5 segundos de timeout
            # getaddrinfo pode retornar IPv4 ou IPv6
            # Formato do retorno: [(family, type, proto, canonname, sockaddr), ...]
            addr_info = await anyio.to_thread.run_sync(
                socket.getaddrinfo, hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
    except TimeoutError:
        raise InvalidProviderURLError(
            f"Timeout na resolução DNS para {hostname} no campo {field_name}."
        )
    except socket.gaierror:
        raise InvalidProviderURLError(
            f"Não foi possível resolver o hostname {hostname} no campo {field_name}."
        )
    except Exception:
        raise InvalidProviderURLError(f"Falha de rede ao validar {hostname} no campo {field_name}.")

    if not addr_info:
        raise InvalidProviderURLError(
            f"Nenhum endereço encontrado para {hostname} no campo {field_name}."
        )

    for info in addr_info:
        sockaddr = info[4]
        ip_str = sockaddr[0]  # O primeiro item é o IP

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Bloqueios rigorosos da Política A (somente internet pública)
        if ip_obj.is_loopback:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP de loopback não permitido."
            )

        if ip_obj.is_link_local:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP link-local não permitido."
            )

        if ip_obj.is_private:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP privado não permitido (Política de rede restrita)."
            )

        if ip_obj.is_multicast:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP multicast não permitido."
            )

        if ip_obj.is_reserved:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP reservado não permitido."
            )

        if ip_obj.is_unspecified:
            raise InvalidProviderURLError(
                f"A URL no campo {field_name} resolve para um IP não especificado."
            )

        # Metadata cloud AWS/GCP/Azure IPv4 (169.254.169.254) já é coberto por is_link_local,
        # mas faremos checagem extra se surgir outros metadados.

    # Normalizar removendo o trailing slash do path original
    # urlunparse não é perfeitamente ideal para recompilar se quisermos só dar um rstrip,
    # mas o .rstrip('/') direto na string original atende a necessidade e mantém cases que o usuário enviou.
    normalized = value.rstrip("/")
    return normalized
