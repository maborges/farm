"""Serviço de persistência e cache da configuração global de Demonstração (`configuracoes_saas`)."""

from __future__ import annotations

import time
import unicodedata
import uuid

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    DEMO_CRM_STAGE_NAME,
    DEMO_DEFAULT_DURATION_DAYS,
    DEMO_DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEMO_IDLE_TIMEOUT_MINUTES,
    DEMO_TENANT_CANONICAL_NAME,
)
from core.models.configuration import ConfiguracaoSaaS
from core.models.tenant import Tenant

DEMO_SAAS_CONFIG_KEY = "demonstracao"
DEFAULT_DEMO_BUSY_MESSAGE = (
    "Muitos usuários de demonstração estão usando a plataforma no momento. "
    "Por favor, aguarde alguns minutos e tente novamente mais tarde."
)
_DEMO_CONFIG_TTL_SECONDS = 30.0

_cached_demo_config: DemoSaasConfigSchema | None = None
_cached_demo_config_at: float = 0.0


def _normalize_name(value: str | None) -> str:
    """Normaliza texto para comparação case/accent-insensitive."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(ascii_only.strip().lower().split())


class DemoSaasConfigSchema(BaseModel):
    """Schema tipado da chave `demonstracao` persistida em `configuracoes_saas`."""

    tenant_id: str | None = None
    max_sessoes_simultaneas: int = Field(default=DEMO_DEFAULT_MAX_CONCURRENT_SESSIONS, ge=1, le=500)
    duracao_inicial_dias: int = Field(default=DEMO_DEFAULT_DURATION_DAYS, ge=1, le=365)
    dias_prorrogacao_padrao: int = Field(default=DEMO_DEFAULT_DURATION_DAYS, ge=1, le=90)
    timeout_inatividade_minutos: int = Field(default=DEMO_IDLE_TIMEOUT_MINUTES, ge=5, le=240)
    estagio_crm_nome: str = Field(default=DEMO_CRM_STAGE_NAME, min_length=2, max_length=100)
    mensagem_limite_simultaneo: str = Field(default=DEFAULT_DEMO_BUSY_MESSAGE, min_length=10, max_length=400)
    permitir_solicitacao_prorrogacao: bool = True

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return str(uuid.UUID(text))

    @field_validator("estagio_crm_nome", "mensagem_limite_simultaneo")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Campo obrigatório não pode ficar vazio.")
        return cleaned


def invalidate_demo_config_cache() -> None:
    """
    Invalida o cache em memória da configuração de demonstração.

    Args:
        Nenhum.

    Return:
        None.

    Raises:
        Nunca lança exceções.
    """
    global _cached_demo_config, _cached_demo_config_at
    _cached_demo_config = None
    _cached_demo_config_at = 0.0


def validate_and_normalize_demo_config(raw: dict) -> dict:
    """
    Valida e normaliza o payload da configuração `demonstracao`.

    Args:
        raw: Dicionário recebido via API administrativa.

    Return:
        Dicionário validado pronto para persistência em `configuracoes_saas`.

    Raises:
        HTTPException: 422 quando qualquer parâmetro viola limites ou formato UUID.
    """
    try:
        parsed = DemoSaasConfigSchema.model_validate(raw or {})
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Configuração de demonstração inválida: {exc}",
        ) from exc
    return parsed.model_dump()


async def get_demo_saas_config(
    session: AsyncSession,
    *,
    use_cache: bool = True,
) -> DemoSaasConfigSchema:
    """
    Obtém os parâmetros globais de demonstração com cache curto e fallback seguro.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        use_cache: Quando True, reutiliza snapshot em memória dentro de 30s.

    Return:
        Instância validada de `DemoSaasConfigSchema`.

    Raises:
        SQLAlchemyError: Em falha de comunicação com o banco.
    """
    global _cached_demo_config, _cached_demo_config_at
    agora = time.monotonic()
    if (
        use_cache
        and _cached_demo_config is not None
        and (agora - _cached_demo_config_at) < _DEMO_CONFIG_TTL_SECONDS
    ):
        return _cached_demo_config

    raw = (
        await session.execute(
            select(ConfiguracaoSaaS.valor).where(
                ConfiguracaoSaaS.chave == DEMO_SAAS_CONFIG_KEY,
                ConfiguracaoSaaS.ativo.is_(True),
            )
        )
    ).scalar_one_or_none()

    if isinstance(raw, dict):
        try:
            config = DemoSaasConfigSchema.model_validate(raw)
        except (ValidationError, ValueError):
            config = DemoSaasConfigSchema()
    else:
        config = DemoSaasConfigSchema()

    if use_cache:
        _cached_demo_config = config
        _cached_demo_config_at = agora
    return config


async def sync_demo_config_to_tenant(session: AsyncSession, normalized: dict) -> None:
    """
    Sincroniza `tenants.is_demo` e `demo_max_sessoes_simultaneas` a partir de `configuracoes_saas`.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        normalized: Dicionário normalizado de `DemoSaasConfigSchema`.

    Return:
        None.

    Raises:
        HTTPException: 404 se `tenant_id` informado não existir na tabela `tenants`.
    """
    limite = int(normalized["max_sessoes_simultaneas"])
    target_id_str = normalized.get("tenant_id")
    all_demo_tenants = (
        await session.execute(select(Tenant).where(Tenant.is_demo.is_(True)))
    ).scalars().all()

    if target_id_str:
        target_uuid = uuid.UUID(target_id_str)
        target_tenant = await session.get(Tenant, target_uuid)
        if not target_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant selecionado para demonstração não encontrado.",
            )
        for existing in all_demo_tenants:
            if existing.id != target_uuid:
                existing.is_demo = False
        target_tenant.is_demo = True
        target_tenant.demo_max_sessoes_simultaneas = limite
        return

    if all_demo_tenants:
        for existing in all_demo_tenants:
            existing.demo_max_sessoes_simultaneas = limite
        return

    canonical = _normalize_name(DEMO_TENANT_CANONICAL_NAME)
    tenants = (await session.execute(select(Tenant))).scalars().all()
    for tenant in tenants:
        if _normalize_name(tenant.nome) == canonical:
            tenant.is_demo = True
            tenant.demo_max_sessoes_simultaneas = limite
            break


async def upsert_demo_saas_config_from_tenant(session: AsyncSession, tenant: Tenant) -> None:
    """
    Espelha alterações feitas via `/backoffice/tenants/{id}/demo-config` para `configuracoes_saas`.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        tenant: Registro atualizado do tenant de demonstração.

    Return:
        None.

    Raises:
        SQLAlchemyError: Em falha de persistência no banco.
    """
    record = (
        await session.execute(
            select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == DEMO_SAAS_CONFIG_KEY)
        )
    ).scalar_one_or_none()

    current = (
        validate_and_normalize_demo_config(record.valor)
        if record and isinstance(record.valor, dict)
        else DemoSaasConfigSchema().model_dump()
    )

    if tenant.demo_max_sessoes_simultaneas is not None:
        current["max_sessoes_simultaneas"] = int(tenant.demo_max_sessoes_simultaneas)
    if tenant.is_demo:
        current["tenant_id"] = str(tenant.id)
    elif current.get("tenant_id") == str(tenant.id):
        current["tenant_id"] = None

    if record is None:
        session.add(
            ConfiguracaoSaaS(
                chave=DEMO_SAAS_CONFIG_KEY,
                valor=current,
                descricao="Parâmetros globais do ambiente de demonstração",
                ativo=True,
            )
        )
    else:
        record.valor = current
        record.ativo = True
