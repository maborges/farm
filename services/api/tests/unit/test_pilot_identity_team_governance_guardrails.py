"""Guardrails estáticos para identidade global, convites e equipe."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _slice_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_usuario_permanece_identidade_global_sem_tenant_embutido() -> None:
    auth_model_source = _read("services/api/core/models/auth.py")

    usuario_scope = _slice_between(
        auth_model_source,
        "class Usuario(Base):",
        "class PerfilAcesso(Base):",
    )

    assert '__tablename__ = "usuarios"' in usuario_scope
    assert "tenant_id" not in usuario_scope
    assert "email:" in usuario_scope
    assert "username:" in usuario_scope


def test_acesso_ao_tenant_permanece_exclusivo_via_tenant_usuario() -> None:
    auth_model_source = _read("services/api/core/models/auth.py")
    dependencies_source = _read("services/api/core/dependencies.py")

    assert 'class TenantUsuario(Base):' in auth_model_source
    assert '__tablename__ = "tenant_usuarios"' in auth_model_source
    assert "TenantUsuario.tenant_id == tenant_id" in dependencies_source
    assert "TenantUsuario.usuario_id == user.id" in dependencies_source


def test_escopo_operacional_permanece_via_unidade_produtiva_usuario() -> None:
    auth_model_source = _read("services/api/core/models/auth.py")
    operational_context_source = _read("services/api/core/operational_context.py")
    access_check = "UnidadeProdutivaUsuario.unidade_produtiva_id == resolved_id"

    assert 'class UnidadeProdutivaUsuario(Base):' in auth_model_source
    assert '__tablename__ = "unidade_produtiva_usuarios"' in auth_model_source
    assert access_check in operational_context_source
    assert "Usuário sem acesso à fazenda informada." in operational_context_source


def test_convites_e_assinaturas_reaproveitam_usuario_sem_duplicidade() -> None:
    onboarding_service_source = _read("services/api/core/services/onboarding_service.py")
    auth_service_source = _read("services/api/core/services/auth_service.py")

    invite_register_scope = _slice_between(
        onboarding_service_source,
        "async def registrar_via_convite",
        "async def aceitar_convite",
    )
    subscription_scope = _slice_between(
        auth_service_source,
        "async def create_tenant_for_user",
        "# ==================== RECUPERAÇÃO DE SENHA ====================",
    )
    duplicate_email_guard = (
        "Este e-mail já possui conta. Faça login e aceite o convite."
    )
    existing_user_lookup = (
        "stmt_user = select(Usuario).where(Usuario.email == convite.email_convidado)"
    )

    assert duplicate_email_guard in invite_register_scope
    assert existing_user_lookup in invite_register_scope
    assert "usuario_id=user_id" in subscription_scope
    assert "user = Usuario(" not in subscription_scope
    assert "novo_usuario = Usuario(" not in subscription_scope


def test_implantacao_inicial_nao_depende_da_equipe_completa() -> None:
    onboarding_router_source = _read("services/api/core/routers/onboarding.py")
    completion_rule = (
        "completo = bool(tenant and tenant.onboarding_configuracao_completo) "
        "or (etapa1 and etapa2)"
    )

    assert "etapa3 = len(usuarios_result.fetchall()) > 1" in onboarding_router_source
    assert completion_rule in onboarding_router_source
    assert "etapa3_equipe=etapa3" in onboarding_router_source


def test_gestao_de_equipe_permanece_fluxo_independente_por_convite() -> None:
    team_router_source = _read("services/api/core/routers/team.py")

    assert '@router.post(' in team_router_source
    assert '"/invite",' in team_router_source
    assert "async def invite_team_member" in team_router_source
    assert "Este usuário já faz parte da equipe." in team_router_source
    assert "Já existe um convite pendente para este e-mail." in team_router_source
    assert '@router.get("/users"' in team_router_source
    assert '@router.post("/invites/{invite_id}/resend"' in team_router_source
    assert '@router.delete("/users/{tenant_usuario_id}"' in team_router_source
    assert '@router.post("/users"' not in team_router_source
