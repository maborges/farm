"""Roteador FastAPI para o Cofre Segregado BYOK e Proxy Seguro de Cotações."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_global_user_claims, get_session
from core.schemas.agro_config_schemas import KEY_FLAGS
from core.services.agro_config_service import agro_config_service
from .byok_proxy import ByokProxyService
from .byok_vault import ByokVaultService
from .schemas import (
    AgroMessageResponse,
    ByokCotacaoResponse,
    ByokCredentialCreateRequest,
    ByokCredentialResponse,
    ByokProviderInfo,
    ByokRotateKeysResponse,
    TipoMercado,
)

router = APIRouter(prefix="/agro/byok", tags=["Agro - Cofre BYOK & Proxy de Cotações"])


def verify_byok_enabled() -> None:
    """Verifica se a funcionalidade BYOK está ativa nas Feature Flags operacionais."""
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("byok_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Módulo BYOK temporariamente desabilitado pela administração.",
        )


def get_vault_service(db: AsyncSession = Depends(get_session)) -> ByokVaultService:
    """Injeta instância de ByokVaultService conectada à sessão do banco de dados central."""
    verify_byok_enabled()
    return ByokVaultService(db=db)


def get_proxy_service(
    vault: ByokVaultService = Depends(get_vault_service),
) -> ByokProxyService:
    """Injeta instância de ByokProxyService configurada."""
    verify_byok_enabled()
    return ByokProxyService(vault_service=vault)



@router.get("/providers", response_model=list[ByokProviderInfo])
async def list_providers(
    proxy: ByokProxyService = Depends(get_proxy_service),
    current_user: dict = Depends(get_global_user_claims),
) -> list[ByokProviderInfo]:
    """Lista os provedores do catálogo oficial, destacando status de licença e homologação."""
    return proxy.get_providers_catalog()


@router.get("/credentials", response_model=list[ByokCredentialResponse])
async def list_credentials(
    current_user: dict = Depends(get_global_user_claims),
    vault: ByokVaultService = Depends(get_vault_service),
) -> list[ByokCredentialResponse]:
    """Lista todas as credenciais cadastradas no cofre individual com mascaramento estrito."""
    return await vault.list_credentials(uuid.UUID(current_user["sub"]))


@router.post("/credentials", response_model=ByokCredentialResponse, status_code=status.HTTP_201_CREATED)
async def store_credential(
    payload: ByokCredentialCreateRequest,
    current_user: dict = Depends(get_global_user_claims),
    vault: ByokVaultService = Depends(get_vault_service),
) -> ByokCredentialResponse:
    """Armazena ou atualiza uma credencial cifrada com Envelope Encryption (AES-256-GCM + KMS)."""
    return await vault.save_credential(
        usuario_id=uuid.UUID(current_user["sub"]),
        provider_slug=payload.providerSlug,
        api_key=payload.apiKey,
    )


@router.delete("/credentials/{provider_slug}", response_model=AgroMessageResponse)
async def delete_credential(
    provider_slug: str,
    current_user: dict = Depends(get_global_user_claims),
    vault: ByokVaultService = Depends(get_vault_service),
) -> AgroMessageResponse:
    """Exclui permanentemente uma credencial do cofre do usuário."""
    sucesso = await vault.delete_credential(uuid.UUID(current_user["sub"]), provider_slug)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credencial para o provedor '{provider_slug}' não encontrada.",
        )
    return AgroMessageResponse(
        sucesso=True,
        mensagem=f"Credencial do provedor '{provider_slug}' excluída permanentemente com sucesso.",
    )


@router.post("/credentials/{provider_slug}/revoke", response_model=AgroMessageResponse)
async def revoke_credential(
    provider_slug: str,
    current_user: dict = Depends(get_global_user_claims),
    vault: ByokVaultService = Depends(get_vault_service),
) -> AgroMessageResponse:
    """Revoga a credencial, impedindo seu uso imediato sem deletar o histórico de auditoria."""
    sucesso = await vault.revoke_credential(uuid.UUID(current_user["sub"]), provider_slug)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credencial para o provedor '{provider_slug}' não encontrada.",
        )
    return AgroMessageResponse(
        sucesso=True,
        mensagem=f"Credencial do provedor '{provider_slug}' revogada com sucesso.",
    )


@router.post("/credentials/rotate-keys", response_model=ByokRotateKeysResponse)
async def rotate_keys(
    nova_versao: int = Query(2, ge=1, le=10, description="Nova versão da KEK de destino"),
    current_user: dict = Depends(get_global_user_claims),
    vault: ByokVaultService = Depends(get_vault_service),
) -> ByokRotateKeysResponse:
    """Executa a rotação de versão da KEK de todas as credenciais do usuário."""
    total = await vault.rotate_keys(uuid.UUID(current_user["sub"]), new_version=nova_versao)
    return ByokRotateKeysResponse(
        sucesso=True,
        mensagem=f"Rotação de KEK concluída com sucesso para versão v{nova_versao}.",
        versaoDestino=nova_versao,
        credenciaisRotacionadas=total,
    )


@router.get("/cotacoes/{commodity:path}", response_model=ByokCotacaoResponse)
async def get_byok_quote(
    commodity: str,
    tipo_mercado: TipoMercado = Query(TipoMercado.FISICO, description="Mercado FÍSICO nacional ou FUTURO internacional/B3"),
    provedor: str = Query("SIMULATED", description="Slug do provedor de cotações"),
    current_user: dict = Depends(get_global_user_claims),
    proxy: ByokProxyService = Depends(get_proxy_service),
) -> ByokCotacaoResponse:
    """Consulta cotações agropecuárias via Proxy BYOK com titularidade segregada."""
    return await proxy.fetch_quote(
        usuario_id=uuid.UUID(current_user["sub"]),
        commodity_raw=commodity,
        tipo_mercado=tipo_mercado,
        provider_slug_raw=provedor,
    )
