from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from integracoes.models import BalancaWebhookCredential
from integracoes.security import decrypt_integration_secret, encrypt_integration_secret


async def resolve_webhook_secret(
    session: AsyncSession, envelope, account_id: UUID, config: Settings
) -> str:
    """Resolve a persisted HMAC secret for the tenant/account pair."""
    tenant_id = _tenant_id(envelope.client_tenant_id)
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
        {"tenant": str(tenant_id)},
    )
    result = await session.execute(select(BalancaWebhookCredential).where(
        BalancaWebhookCredential.tenant_id == tenant_id,
        BalancaWebhookCredential.balanca_account_id == account_id,
        BalancaWebhookCredential.status == "ATIVO",
    ))
    credential = result.scalar_one_or_none()
    if credential:
        return decrypt_integration_secret(credential.segredo_criptografado)
    return config.balanca_webhook_secret_for(str(account_id))


async def upsert_webhook_credential(
    session: AsyncSession, tenant_id: UUID, account_id: UUID, secret: str
) -> BalancaWebhookCredential:
    """Create or rotate the encrypted secret owned by one tenant/account."""
    result = await session.execute(select(BalancaWebhookCredential).where(
        BalancaWebhookCredential.tenant_id == tenant_id,
        BalancaWebhookCredential.balanca_account_id == account_id,
    ))
    credential = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if credential is None:
        credential = BalancaWebhookCredential(
            tenant_id=tenant_id,
            balanca_account_id=account_id,
            segredo_criptografado=encrypt_webhook_secret(secret),
            status="ATIVO",
            created_at=now,
            rotated_at=now,
            updated_at=now,
        )
        session.add(credential)
    else:
        credential.segredo_criptografado = encrypt_webhook_secret(secret)
        credential.status = "ATIVO"
        credential.rotated_at = now
        credential.updated_at = now
    await session.flush()
    return credential


def _tenant_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("client_tenant_id inválido") from exc


def encrypt_webhook_secret(secret: str) -> str:
    """Encrypt a webhook secret before persistence."""
    return encrypt_integration_secret(secret)
