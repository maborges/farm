"""Resolução legada de provider ERP via SankhyaConfig.

Este módulo isola o fallback legado que verifica se um tenant possui
SankhyaConfig mesmo sem TenantIntegracao canônica.

Requisitos:
- NÃO é a resolução principal (a canônica é via TenantIntegracao → registry)
- NÃO assume Sankhya para Tenant vazio
- NÃO contamina o contrato runtime
- NÃO cria registros em GET
- Permite remoção futura quando a convergência estiver completa
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.sankhya.services import SankhyaSyncService


async def resolve_legacy_sankhya_provider(
    tenant_id: str,
    session: AsyncSession,
) -> bool:
    """Verifica se o tenant possui configuração Sankhya legada.

    Usado como fallback quando o runtime canônico (TenantIntegracao) não
    encontra provider configurado.

    Args:
        tenant_id: Identificador do tenant.
        session: Sessão de banco de dados.

    Returns:
        True se existe SankhyaConfig para o tenant, False caso contrário.
    """
    sync_service = SankhyaSyncService(session)
    config = await sync_service.get_config(tenant_id)
    return config is not None


__all__ = ["resolve_legacy_sankhya_provider"]
