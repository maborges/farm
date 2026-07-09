from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import TenantRoles
from core.models.auth import PerfilAcesso, TenantUsuario
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.tenant import Tenant
from core.models.auth import Usuario
from core.services.auth_service import AuthService
from core.services.onboarding_service import OnboardingService
from core.schemas.onboarding_schemas import AssinanteRegisterRequest


async def _noop_async(*args, **kwargs) -> None:
    return None


@pytest.mark.asyncio
async def test_register_new_tenant_cria_usuario_tenant_e_assinatura(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.services.onboarding_service.email_service.send_trial_notice", _noop_async)
    monkeypatch.setattr("core.services.onboarding_service.email_service.send_welcome", _noop_async)
    monkeypatch.setattr("core.services.onboarding_service.email_service.send_registration_confirmation", _noop_async)

    unique_suffix = uuid.uuid4().hex[:8]
    plano = PlanoAssinatura(
        nome="Plano Teste",
        preco_mensal=99.9,
        preco_anual=999.0,
        is_free=False,
        tem_trial=True,
        dias_trial=14,
        modulos_inclusos=["CORE"],
        max_fazendas=1,
        ativo=True,
    )
    session.add(plano)
    await session.flush()

    perfil_owner = (
        await session.execute(
            select(PerfilAcesso).where(
                PerfilAcesso.tenant_id.is_(None),
                PerfilAcesso.is_custom == False,
                PerfilAcesso.nome == TenantRoles.OWNER,
            )
        )
    ).scalars().first()
    assert perfil_owner is not None

    auth_svc = AuthService(session)
    onboard_svc = OnboardingService(session, auth_svc)
    payload = AssinanteRegisterRequest(
        email=f"novo-{unique_suffix}@exemplo.com",
        username=f"novo_produtor_{unique_suffix}",
        nome_completo="Novo Produtor",
        apelido="Novo",
        senha="senha123",
        cpf=None,
        telefone="11999999999",
        nome_produtor="Fazenda Nova",
        cnpj_tenant=None,
        plano_id=plano.id,
        ciclo="MENSAL",
    )

    user = await onboard_svc.register_new_tenant(payload)

    assert user.email == payload.email

    tenant = await session.scalar(
        select(Tenant)
        .join(TenantUsuario, TenantUsuario.tenant_id == Tenant.id)
        .where(TenantUsuario.usuario_id == user.id)
    )
    assert tenant is not None
    assert tenant.nome == "Fazenda Nova"
    assert tenant.email_responsavel == payload.email
    assert tenant.telefone_responsavel == payload.telefone
    assert tenant.activation_token is not None
    assert tenant.activation_expires_at is not None

    tenant_usuario = await session.scalar(
        select(TenantUsuario).where(
            TenantUsuario.tenant_id == tenant.id,
            TenantUsuario.usuario_id == user.id,
        )
    )
    assert tenant_usuario is not None
    assert tenant_usuario.is_owner is True
    assert tenant_usuario.perfil_id == perfil_owner.id

    assinatura = await session.scalar(select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant.id))
    assert assinatura is not None
    assert assinatura.plano_id == plano.id

    persisted_user = await session.scalar(select(Usuario).where(Usuario.id == user.id))
    assert persisted_user is not None


@pytest.mark.asyncio
async def test_register_new_tenant_rejeita_cpf_ja_cadastrado(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.services.onboarding_service.email_service.send_registration_confirmation", _noop_async)

    unique_suffix = uuid.uuid4().hex[:8]
    plano = PlanoAssinatura(
        nome="Plano Teste CPF",
        preco_mensal=99.9,
        preco_anual=999.0,
        is_free=False,
        tem_trial=True,
        dias_trial=14,
        modulos_inclusos=["CORE"],
        max_fazendas=1,
        ativo=True,
    )
    session.add(plano)

    usuario_existente = Usuario(
        email=f"existente-{unique_suffix}@exemplo.com",
        username=f"existente_{unique_suffix}",
        nome_completo="Usuario Existente",
        apelido="Existente",
        senha_hash="hash",
        cpf="04245459859",
        ativo=True,
    )
    session.add(usuario_existente)
    await session.flush()

    auth_svc = AuthService(session)
    onboard_svc = OnboardingService(session, auth_svc)
    payload = AssinanteRegisterRequest(
        email=f"novo-cpf-{unique_suffix}@exemplo.com",
        username=f"novo_cpf_{unique_suffix}",
        nome_completo="Novo Produtor",
        apelido="Novo",
        senha="senha123",
        cpf="04245459859",
        telefone="11999999999",
        nome_produtor="Fazenda Nova",
        cnpj_tenant=None,
        plano_id=plano.id,
        ciclo="MENSAL",
    )

    with pytest.raises(Exception) as exc_info:
        await onboard_svc.register_new_tenant(payload)

    assert "Este CPF já está cadastrado no sistema." in str(exc_info.value)
