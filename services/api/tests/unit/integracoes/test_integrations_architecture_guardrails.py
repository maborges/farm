"""Guardrails estáticos do domínio de Integrações."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]

ARCH_01 = "docs/architecture/INTEGRATIONS-ARCH-01.md"
ARCH_02 = "docs/architecture/INTEGRATIONS-ARCH-02.md"
REPORT = "docs/implementation/reports/" "INTEGRATIONS-GOV-01-GUARDRAILS-DOMINIO-INTEGRACOES.md"
SANKHYA_MODELS = "services/api/integracoes/sankhya/models/__init__.py"
SANKHYA_ROUTERS = "services/api/integracoes/sankhya/routers/__init__.py"
SANKHYA_PAGE = "apps/web/src/components/integracoes/sankhya-console.tsx"
BACKOFFICE_ERP_PAGE = "apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx"
TENANT_SIDEBAR = "apps/web/src/components/layout/app-sidebar.tsx"
PERMISSIONS_TS = "apps/web/src/lib/permissions.ts"
CORE_DB = "services/api/core/database.py"
CORE_DEPS = "services/api/core/dependencies.py"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_erp_nao_pode_usar_unidade_produtiva_como_escopo_de_configuracao() -> None:
    arch_01 = _read(ARCH_01)
    arch_02 = _read(ARCH_02)
    sankhya_models = _read(SANKHYA_MODELS)

    assert "ERP nunca é configurado por Unidade Produtiva." in arch_01
    assert "ERP nunca por `UnidadeProdutiva`" in arch_02
    assert "unidade_produtiva_id" not in sankhya_models


def test_escopos_oficiais_permanecem_limitados_a_platform_tenant_estabelecimento_usuario() -> None:
    arch_01 = _read(ARCH_01)

    expected_scopes = [
        "`PLATFORM`",
        "`TENANT`",
        "`ESTABELECIMENTO`",
        "`USUARIO`",
    ]

    for scope in expected_scopes:
        assert scope in arch_01


def test_connection_e_credential_permancem_conceitos_separados() -> None:
    arch_02 = _read(ARCH_02)

    assert (
        "`IntegrationConnection` representa parâmetros técnicos de conexão não secretos." in arch_02
    )
    assert "`IntegrationCredential` representa segredos e credenciais." in arch_02
    assert "credencial nunca deve ser confundida com `IntegrationConnection`" in arch_02


def test_campos_sensiveis_nao_podem_ser_tratados_como_connection() -> None:
    arch_02 = _read(ARCH_02)

    sensitive_fields = [
        "`password`",
        "`token`",
        "`app_secret`",
        "`private_key`",
        "`certificate`",
    ]

    assert "`Connection` não contém senha, token, chave privada ou certificado secreto" in arch_02
    for field in sensitive_fields:
        assert field in arch_02


def test_provider_e_provider_definition_nao_podem_armazenar_credenciais_reais_de_cliente() -> None:
    arch_02 = _read(ARCH_02)

    assert "`IntegrationProvider` é o catálogo oficial de tipos de integração." in arch_02
    assert "ele não contém o segredo do cliente" in arch_02
    assert "`IntegrationProviderDefinition` é a definição arquitetural do provider." in arch_02
    assert "schemas do provider pertencem à definição do provider" in arch_02
    assert "não pertencem diretamente à configuração do tenant" in arch_02


def test_backoffice_nao_pode_ser_console_principal_de_configuracao_do_cliente() -> None:
    arch_01 = _read(ARCH_01)
    report = _read(REPORT)
    backoffice_page = _read(BACKOFFICE_ERP_PAGE)

    assert "console de configuração do cliente não deve morar no backoffice" in arch_01
    assert (
        "a configuração atual no backoffice não está correta como ponto principal de governança."
        in report.lower()
    )
    assert "Backoffice" in backoffice_page
    assert "Integrações ERP" in backoffice_page


def test_permissoes_de_tenant_nao_devem_depender_de_permissoes_backoffice() -> None:
    arch_01 = _read(ARCH_01)
    permissions = _read(PERMISSIONS_TS)
    tenant_sidebar = _read(TENANT_SIDEBAR)

    assert "uma tela de tenant não deve depender de permissão de backoffice" in arch_01
    assert "tenant:settings:view" in permissions
    assert "backoffice:config:view" in permissions
    assert 'href: "/dashboard/settings/tenant"' in tenant_sidebar


def test_sankhya_permanece_classificado_como_erp() -> None:
    arch_02 = _read(ARCH_02)
    sankhya_page = _read(SANKHYA_PAGE)

    assert "Sankhya é apenas um provider do tipo `ERP`." in arch_02
    assert "Integração Sankhya" in sankhya_page


def test_sankhya_nao_deve_exigir_unidade_produtiva_e_deve_aceitar_tenant_preparado_para_estabelecimento() -> None:  # noqa: E501
    arch_01 = _read(ARCH_01)
    arch_02 = _read(ARCH_02)
    report = _read(REPORT)
    sankhya_routers = _read(SANKHYA_ROUTERS)
    sankhya_models = _read(SANKHYA_MODELS)

    combined = f"{arch_01}\n{arch_02}\n{report}"
    assert "escopo padrão do Sankhya deve ser `TENANT`" in combined
    assert (
        "quando o tenant possuir matriz/filiais fiscalmente distintas, o escopo recomendado "
        "passa a ser `ESTABELECIMENTO`" in combined
    )
    assert "unidade produtiva: inexistente" in report
    assert "tenant_id" in sankhya_models
    assert "tenant_id: uuid.UUID = Depends(get_tenant_id)" in sankhya_routers
    assert "unidade_produtiva_id" not in sankhya_routers


def test_credenciais_exigem_criptografia_masking_ou_contrato_equivalente() -> None:
    arch_01 = _read(ARCH_01)
    arch_02 = _read(ARCH_02)
    sankhya_models = _read(SANKHYA_MODELS)
    sync_service = _read("services/api/integracoes/sankhya/services/sync_service.py")

    combined = f"{arch_01}\n{arch_02}"
    assert "credenciais nunca devem ser persistidas em texto puro" in combined
    assert "mascarar valores" in combined
    assert "permitir rotação" in combined
    assert "client_secret = Column(String(200))  # Criptografado" in sankhya_models
    assert "x_token = Column(String(200))  # Criptografado" in sankhya_models
    assert "encrypt_integration_secret(" in sync_service
    assert "mask_integration_secret(config.password)" in sync_service
    assert "mask_integration_secret(config.client_secret)" in sync_service


def test_rotas_tenant_scoped_devem_usar_sessao_rls() -> None:
    routers = _read(SANKHYA_ROUTERS)
    core_deps = _read(CORE_DEPS)

    assert "SET LOCAL app.current_tenant_id" in core_deps
    assert "Depends(get_session)" in routers
    assert "Depends(get_db)" not in routers


def test_logs_e_health_possuem_tenant_id_ou_escopo_equivalente() -> None:
    arch_01 = _read(ARCH_01)
    sankhya_models = _read(SANKHYA_MODELS)
    sankhya_routers = _read(SANKHYA_ROUTERS)

    assert "`IntegrationHealth`" in arch_01
    assert "tenant_id = Column(String(50), nullable=False, index=True)" in sankhya_models
    assert "status_conexao" in sankhya_routers
    assert "ultimo_sync" in sankhya_routers


def test_sync_jobs_registram_tenant_id_ou_escopo_equivalente() -> None:
    sankhya_models = _read(SANKHYA_MODELS)
    sankhya_routers = _read(SANKHYA_ROUTERS)

    assert "class SankhyaSyncLog" in sankhya_models
    assert "tenant_id = Column(String(50), nullable=False, index=True)" in sankhya_models
    assert (
        'log = await sync_service.iniciar_sync_log(tenant_scope, "pessoas", "import")'
        in sankhya_routers
    )
    assert (
        'log = await sync_service.iniciar_sync_log(tenant_scope, "produtos", "import")'
        in sankhya_routers
    )
