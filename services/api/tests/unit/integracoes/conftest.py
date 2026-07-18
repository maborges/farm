# A fixture `session` (PostgreSQL oficial, schema `farms`) é herdada de
# `tests/conftest.py` — não é redefinida aqui. Um engine SQLite em memória
# com um subconjunto manual de tabelas era declarado neste arquivo e não
# incluía `farms.tenants`, causando `NoReferencedTableError` para qualquer
# model com FK real para `tenant_id` (ver INTEGRATIONS-TEST-INFRA-01).
import socket
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def criar_tenant_real(
    session: AsyncSession,
    *,
    nome: str = "Tenant Teste Integracoes",
) -> str:
    """Insere um tenant real em `tenants` e ativa a RLS da sessão.

    Helper compartilhado por INTEGRATIONS-TEST-INFRA-03A: evita tenants
    fictícios (`"tenant-legado"`, `"tenant-1"`, etc.) que nunca existem em
    `tenants`, causando `ForeignKeyViolationError` contra o PostgreSQL oficial.
    Cada chamada gera um UUID novo — chamar uma única vez por tenant lógico
    dentro do teste e reutilizar o valor retornado quando o cenário exigir o
    mesmo tenant em múltiplas operações.
    """
    tenant_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
            "storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now())"
        ),
        {"id": tenant_id, "nome": nome, "doc": tenant_id[:11]},
    )
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
    return tenant_id


@pytest.fixture(autouse=True)
def mock_dns_globally(monkeypatch):
    def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Mapeamento para os testes de integracoes
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

        # Para outros testes no pacote, retorna um IP publico dummy válido
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
