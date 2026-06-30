"""Guardrails estáticos para implantação, onboarding e assinatura."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _slice_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_novo_assinante_cria_tenant_owner_e_assinatura() -> None:
    source = _read("services/api/core/services/onboarding_service.py")
    register_scope = _slice_between(
        source,
        "async def register_new_tenant",
        "# ========================================================",
    )

    assert "user = Usuario(" in register_scope
    assert "tenant = Tenant(" in register_scope
    assert "TenantUsuario(" in register_scope
    assert "is_owner=True" in register_scope
    assert "AssinaturaTenant(" in register_scope


def test_usuario_existente_vira_assinante_sem_duplicar_usuario() -> None:
    router_source = _read("services/api/core/routers/auth.py")
    service_source = _read("services/api/core/services/auth_service.py")
    create_scope = _slice_between(
        service_source,
        "async def create_tenant_for_user",
        "# ==================== RECUPERAÇÃO DE SENHA ====================",
    )

    assert '"/auth/create-subscription"' not in router_source
    assert "@router.post(\"/create-subscription\"" in router_source
    assert "user_id = uuid.UUID(claims[\"sub\"])" in router_source
    assert "await svc.create_tenant_for_user(" in router_source
    assert "usuario_id=user_id" in create_scope
    assert "user = Usuario(" not in create_scope
    assert "novo_usuario = Usuario(" not in create_scope
    assert "is_owner=True" in create_scope


def test_dashboard_permanece_bloqueado_sem_onboarding_ou_unidade_produtiva() -> None:
    guard_source = _read("apps/web/src/components/auth/onboarding-guard.tsx")
    status_source = _read("services/api/core/routers/onboarding.py")
    complete_rule = (
        "completo = bool(tenant and tenant.onboarding_configuracao_completo) "
        "or (etapa1 and etapa2)"
    )

    assert 'apiFetch<OnboardingStatusResponse>("/onboarding/status"' in guard_source
    assert 'router.replace("/onboarding/configurar")' in guard_source
    assert "Fazenda.tenant_id == tenant_id" in status_source
    assert "Fazenda.ativo == True" in status_source
    assert "etapa2 = fazenda_result.scalar_one_or_none() is not None" in status_source
    assert complete_rule in status_source


def test_fluxos_convergem_sem_tratar_onboarding_tecnico_como_up() -> None:
    register_form_source = _read("apps/web/src/components/auth/register-form.tsx")
    login_form_source = _read("apps/web/src/components/auth/login-form.tsx")
    new_subscription_source = _read("apps/web/src/components/auth/new-subscription-wizard.tsx")
    config_source = _read("services/api/core/routers/configuration.py")
    onboarding_route = 'router.push("/onboarding/configurar")'

    assert onboarding_route in register_form_source
    assert 'nextRoute = "/onboarding/configurar"' in login_form_source
    assert 'window.location.href = "/dashboard"' in new_subscription_source
    assert "tenant.onboarding_configuracao_completo = True" in config_source
    assert "criar_unidade_produtiva" not in config_source
