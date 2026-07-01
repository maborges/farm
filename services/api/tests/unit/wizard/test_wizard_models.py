from __future__ import annotations

from pathlib import Path

from wizard.models import (
    ACTIVE_WIZARD_STATUSES,
    FINAL_WIZARD_STATUSES,
    ImplantacaoChecklistItem,
    ImplantacaoEtapa,
    ImplantacaoHistorico,
    ImplantacaoOperacional,
    ImplantacaoPendencia,
    WizardStageCode,
    WizardStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_wizard_status_enum_oficial() -> None:
    assert [status.value for status in WizardStatus] == [
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


def test_wizard_stage_code_enum_oficial() -> None:
    assert [stage.value for stage in WizardStageCode] == [
        "DIAGNOSTICO",
        "UNIDADE_PRODUTIVA",
        "TERRITORIO",
        "ATIVIDADES",
        "AGRICULTURA",
        "PECUARIA",
        "ESTOQUE",
        "FINANCEIRO",
        "MAQUINAS",
        "EQUIPE",
        "REVISAO",
        "GO_LIVE",
        "ESTABILIZACAO",
    ]


def test_statuses_ativos_e_finais_permanece_estaveis() -> None:
    assert ACTIVE_WIZARD_STATUSES == (
        "NOT_STARTED",
        "IN_PROGRESS",
        "PAUSED",
        "BLOCKED",
        "READY_FOR_GO_LIVE",
        "GO_LIVE",
        "STABILIZATION",
    )
    assert FINAL_WIZARD_STATUSES == ("COMPLETED", "CANCELLED")


def test_etapa_equipe_permanece_opcional_por_modelagem() -> None:
    etapa = ImplantacaoEtapa(
        codigo_etapa=WizardStageCode.EQUIPE.value,
        nome="Equipe",
        obrigatoria=False,
        ordem=10,
        percentual_peso=0,
    )

    assert etapa.codigo_etapa == "EQUIPE"
    assert etapa.obrigatoria is False


def test_entidades_canonicas_do_wizard_existem() -> None:
    assert ImplantacaoOperacional.__tablename__ == "wizard_implantacoes_operacionais"
    assert ImplantacaoEtapa.__tablename__ == "wizard_implantacoes_etapas"
    assert (
        ImplantacaoChecklistItem.__tablename__
        == "wizard_implantacoes_checklist_itens"
    )
    assert ImplantacaoPendencia.__tablename__ == "wizard_implantacoes_pendencias"
    assert ImplantacaoHistorico.__tablename__ == "wizard_implantacoes_historico"


def test_relacionamentos_basicos_estao_definidos() -> None:
    etapa_relationships = ImplantacaoEtapa.__mapper__.relationships.keys()
    implantacao_relationships = (
        ImplantacaoOperacional.__mapper__.relationships.keys()
    )

    assert "etapas" in implantacao_relationships
    assert "checklist_itens" in implantacao_relationships
    assert "pendencias" in implantacao_relationships
    assert "historico" in implantacao_relationships
    assert "implantacao" in etapa_relationships


def test_models_wizard_nao_importam_billing_auth_ou_convites_como_dependencia() -> None:
    source = (
        REPO_ROOT / "services" / "api" / "wizard" / "models.py"
    ).read_text(encoding="utf-8")

    forbidden_imports = [
        "from core.models.auth",
        "from core.models.billing",
        "AssinaturaTenant",
        "ConviteAcesso",
        "TenantUsuario",
        "Pessoa",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source


def test_constraint_source_reforca_go_live_e_blocked() -> None:
    source = (
        REPO_ROOT / "services" / "api" / "wizard" / "models.py"
    ).read_text(encoding="utf-8")

    assert "ck_wizard_implantacao_status_requires_unidade" in source
    assert "READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION', 'COMPLETED'" in source
    assert "ck_wizard_implantacao_blocked_requires_blocked_at" in source
    assert "uq_wizard_implantacao_ativa_por_tenant" in source
