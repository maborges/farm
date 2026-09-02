"""Regras de persistência e resolução do conector TARA."""

from __future__ import annotations

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import IntegrationCredential, MarketplaceIntegracao, TenantIntegracao
from integracoes.security import decrypt_integration_secret, encrypt_integration_secret

from .client import TaraClient
from .schemas import TaraConfigResponse, TaraConfigUpsert


class TaraNotConfigured(ValueError):
    """Indica ausência de configuração TARA para o tenant."""


async def _provider(db: AsyncSession) -> MarketplaceIntegracao:
    result = await db.execute(select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "tara"))
    provider = result.scalar_one_or_none()
    if provider:
        return provider
    provider = MarketplaceIntegracao(nome="TARA", slug="tara", provider_type="WEIGHING", oficial=True, ativa=True)
    db.add(provider)
    await db.flush()
    return provider


async def _config(db: AsyncSession, tenant_id: str, provider_id: int) -> TenantIntegracao | None:
    result = await db.execute(select(TenantIntegracao).where(
        TenantIntegracao.tenant_id == tenant_id, TenantIntegracao.integracao_id == provider_id,
        TenantIntegracao.scope_type == "TENANT", TenantIntegracao.deleted_at.is_(None),
    ))
    return result.scalar_one_or_none()


async def save_config(db: AsyncSession, tenant_id: str, payload: TaraConfigUpsert) -> TaraConfigResponse:
    """Persiste configuração TARA e criptografa o segredo do API Client."""
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": tenant_id})
    provider = await _provider(db)
    config = await _config(db, tenant_id, provider.id)
    values = {"base_url": str(payload.base_url).rstrip("/"), "tara_tenant_id": payload.tenant_id, "client_id": payload.client_id}
    if config is None:
        config = TenantIntegracao(tenant_id=tenant_id, integracao_id=provider.id, configuracoes=values, status="ativa", lifecycle_state="ACTIVE")
        db.add(config)
    else:
        config.configuracoes = values
        config.status, config.lifecycle_state = "ativa", "ACTIVE"
    if payload.client_secret:
        await _save_secret(db, tenant_id, provider.id, payload.client_secret, config)
    await db.commit()
    await db.refresh(config)
    return await config_response(db, config)


async def _save_secret(db: AsyncSession, tenant_id: str, provider_id: int, secret: str, config: TenantIntegracao) -> None:
    result = await db.execute(select(IntegrationCredential).where(
        IntegrationCredential.tenant_id == tenant_id, IntegrationCredential.provider_id == provider_id,
        IntegrationCredential.scope_type == "TENANT", IntegrationCredential.ativo.is_(True),
    ).order_by(desc(IntegrationCredential.version_number)))
    credential = result.scalars().first()
    if credential is None:
        credential = IntegrationCredential(tenant_id=tenant_id, provider_id=provider_id, scope_type="TENANT", version_number=1, segredo_criptografado=encrypt_integration_secret(secret))
        db.add(credential)
        await db.flush()
    else:
        credential.segredo_criptografado = encrypt_integration_secret(secret)
    config.credential_ref_id = credential.id


async def get_config(db: AsyncSession, tenant_id: str) -> TaraConfigResponse | None:
    """Retorna configuração mascarada do tenant."""
    provider = await _provider(db)
    config = await _config(db, tenant_id, provider.id)
    return await config_response(db, config) if config else None


async def config_response(db: AsyncSession, config: TenantIntegracao) -> TaraConfigResponse:
    """Converte configuração sem expor o segredo persistido."""
    secret = await _secret(db, config)
    values = config.configuracoes or {}
    return TaraConfigResponse(id=config.id, tenant_id=str(config.tenant_id), base_url=values.get("base_url", ""), tara_tenant_id=values.get("tara_tenant_id", ""), client_id=values.get("client_id", ""), client_secret_configured=bool(secret), status=config.lifecycle_state)


async def _secret(db: AsyncSession, config: TenantIntegracao) -> str:
    if not config.credential_ref_id:
        return ""
    credential = await db.get(IntegrationCredential, config.credential_ref_id)
    return decrypt_integration_secret(credential.segredo_criptografado if credential else None)


async def resolve_client(db: AsyncSession, tenant_id: str) -> TaraClient:
    """Resolve o cliente TARA somente a partir da configuração persistida."""
    provider = await _provider(db)
    config = await _config(db, tenant_id, provider.id)
    if not config:
        raise TaraNotConfigured("Integração TARA não configurada para o tenant.")
    secret = await _secret(db, config)
    values = config.configuracoes or {}
    if not all((values.get("base_url"), values.get("tara_tenant_id"), values.get("client_id"), secret)):
        raise TaraNotConfigured("Configuração TARA incompleta.")
    return TaraClient(values["base_url"], values["tara_tenant_id"], values["client_id"], secret)


async def sync_weighings(db: AsyncSession, tenant_id: str, limit: int = 100) -> list[dict]:
    """Recupera todas as páginas e salva o cursor apenas após cada sucesso."""
    provider = await _provider(db)
    config = await _config(db, tenant_id, provider.id)
    client = await resolve_client(db, tenant_id)
    cursor = (config.configuracoes or {}).get("weighings_next_cursor") if config else None
    items: list[dict] = []
    while True:
        page = await client.list_weighings(limit, cursor)
        items.extend(page.get("items", []))
        next_cursor = page.get("next_cursor")
        config.configuracoes = {**(config.configuracoes or {}), "weighings_next_cursor": next_cursor}
        await db.commit()
        if next_cursor is None:
            return items
        cursor = next_cursor
