"""Guardrails estáticos para o domínio do Wizard de implantação."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

WIZARD_ARCH = (
    "docs/architecture/WIZARD-ARCH-01-ASSISTENTE-IMPLANTACAO.md"
)
WIZARD_DOMAIN = (
    "docs/architecture/WIZARD-DOMAIN-01-MODELO-CANONICO-IMPLANTACAO.md"
)
WIZARD_GOV = "docs/architecture/WIZARD-GOV-01-GUARDRAILS.md"

OFFICIAL_STATES = [
    "NOT_STARTED",
    "IN_PROGRESS",
    "PAUSED",
    "BLOCKED",
    "READY_FOR_GO_LIVE",
    "GO_LIVE",
    "STABILIZATION",
    "COMPLETED",
    "CANCELLED",
]

OFFICIAL_STEPS = [
    "Diagnóstico",
    "UnidadeProdutiva",
    "Território",
    "Atividades",
    "Agricultura",
    "Pecuária",
    "Estoque",
    "Financeiro",
    "Máquinas",
    "Equipe",
    "Revisão",
    "Go-live",
    "Estabilização",
]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_wizard_permanece_separado_de_auth_billing_tenant_e_convites() -> None:
    wizard_arch = _read(WIZARD_ARCH)
    wizard_gov = _read(WIZARD_GOV)

    forbidden_responsibilities = [
        "não criar `Usuario`",
        "não criar `Tenant`",
        "não criar `Assinatura`",
        "não criar `TenantUsuario`",
        "não criar credenciais, senha, MFA ou identidade de autenticação",
        "não gerenciar billing",
        "Wizard nunca envia convites",
        "Wizard nunca cria identidade",
    ]

    for item in forbidden_responsibilities:
        assert item in f"{wizard_arch}\n{wizard_gov}"


def test_agregado_raiz_e_modelo_canonico_permanece_estavel() -> None:
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    assert "`ImplantacaoOperacional` é a entidade canônica" in wizard_domain
    assert "O agregado raiz oficial do domínio Wizard permanece:" in wizard_gov
    assert "- `ImplantacaoOperacional`" in wizard_gov

    canonical_entities = [
        "`ImplantacaoOperacional`",
        "`ImplantacaoEtapa`",
        "`ImplantacaoChecklistItem`",
        "`ImplantacaoPendencia`",
        "`ImplantacaoHistorico`",
    ]

    for entity in canonical_entities:
        assert entity in wizard_domain
        assert entity in wizard_gov


def test_unicidade_e_idempotencia_por_tenant_permanece_obrigatoria() -> None:
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    assert "deve existir no máximo uma `ImplantacaoOperacional` ativa" in wizard_domain
    assert "1 ImplantacaoOperacional ativa por Tenant" in wizard_gov
    assert "reinício, retomada ou reexecução do Wizard não podem criar" in wizard_gov
    assert "- criar nova implantação;" in wizard_gov
    assert "- duplicar etapas;" in wizard_gov
    assert "- duplicar checklist;" in wizard_gov
    assert "- duplicar pendências;" in wizard_gov
    assert "- duplicar histórico estrutural." in wizard_gov


def test_ready_for_go_live_e_go_live_exigem_unidade_produtiva() -> None:
    wizard_arch = _read(WIZARD_ARCH)
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    expected_rules = [
        "`UnidadeProdutiva` é a âncora operacional mínima do Wizard.",
        "antes de `READY_FOR_GO_LIVE`, uma `UnidadeProdutiva` principal deve estar definida;",
        "`READY_FOR_GO_LIVE` e `GO_LIVE` somente podem existir quando houver:",
        "- `UnidadeProdutiva` válida;",
        "- `UnidadeProdutiva` ativa.",
    ]

    combined = f"{wizard_arch}\n{wizard_domain}\n{wizard_gov}"
    for rule in expected_rules:
        assert rule in combined


def test_blocked_impede_ready_for_go_live_e_go_live() -> None:
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    assert "Decisão recomendada: **sim, o modelo deve suportar `BLOCKED`**." in wizard_domain
    assert "- `BLOCKED`: implantação impedida por requisito crítico ausente" in wizard_domain
    assert "- `BLOCKED` impede transição para `READY_FOR_GO_LIVE` e `GO_LIVE`." in wizard_domain
    assert "enquanto `BLOCKED` existir, nunca permitir:" in wizard_gov
    assert "- `READY_FOR_GO_LIVE`" in wizard_gov
    assert "- `GO_LIVE`" in wizard_gov


def test_equipe_permanece_opcional_e_nao_bloqueia_go_live_minimo() -> None:
    wizard_arch = _read(WIZARD_ARCH)
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    combined = f"{wizard_arch}\n{wizard_domain}\n{wizard_gov}"
    assert "equipe operacional é opcional e progressiva;" in combined
    assert "Equipe continua sendo:" in wizard_gov
    assert "- opcional" in wizard_gov
    assert "equipe incompleta não pode impedir go-live mínimo;" in wizard_gov
    assert "pendência de equipe não pode, por si só, impedir o go-live mínimo;" in wizard_domain


def test_checklist_exige_evidencia_e_estado_real_do_tenant() -> None:
    wizard_arch = _read(WIZARD_ARCH)
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    assert "o avanço deve depender de evidência de dados já existentes" in wizard_arch
    evidence_rule = (
        "itens obrigatórios de go-live não podem ser “marcados como "
        "concluídos” sem evidência compatível;"
    )
    manual_rule = (
        "Checklist obrigatório nunca poderá ser satisfeito apenas por "
        "marcação manual."
    )

    assert evidence_rule in wizard_domain
    assert manual_rule in wizard_gov
    assert "O Wizard trabalha sobre:" in wizard_gov
    assert "- estado real do tenant" in wizard_gov


def test_historico_permanece_append_only() -> None:
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    assert "alterações críticas não devem depender apenas de `updated_at`." in wizard_domain
    assert "`ImplantacaoHistorico` deve ser:" in wizard_gov
    assert "- append-only" in wizard_gov
    assert "- editar histórico;" in wizard_gov
    assert "- reescrever histórico;" in wizard_gov
    assert "- apagar transições críticas." in wizard_gov


def test_estados_oficiais_permanece_estaveis() -> None:
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)

    for state in OFFICIAL_STATES:
        assert f"`{state}`" in wizard_domain
        assert f"`{state}`" in wizard_gov


def test_etapas_oficiais_permanece_estaveis() -> None:
    wizard_arch = _read(WIZARD_ARCH)
    wizard_domain = _read(WIZARD_DOMAIN)
    wizard_gov = _read(WIZARD_GOV)
    combined = f"{wizard_arch}\n{wizard_domain}\n{wizard_gov}"

    for step in OFFICIAL_STEPS:
        assert step in combined
