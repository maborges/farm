from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from wizard.models import ACTIVE_WIZARD_STATUSES, FINAL_WIZARD_STATUSES, ImplantacaoOperacional
from wizard.state_engine import (
    _TRANSICOES,
    WizardTransitionError,
    can_transition,
    transicionar_implantacao,
)

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


REPO_ROOT = Path(__file__).resolve().parents[5]


def _make_implantacao(
    status: str = "NOT_STARTED",
    *,
    unidade_produtiva_id=None,
) -> ImplantacaoOperacional:
    return ImplantacaoOperacional(
        tenant_id=uuid4(),
        owner_usuario_id=uuid4(),
        status=status,
        etapa_atual="DIAGNOSTICO",
        unidade_produtiva_id=unidade_produtiva_id,
    )


def test_state_engine_reutiliza_estados_oficiais_da_foundation() -> None:
    assert set(_TRANSICOES) == set(ACTIVE_WIZARD_STATUSES) | set(FINAL_WIZARD_STATUSES)


def test_transicoes_oficiais_validas_funcionam() -> None:
    transitions = [
        ("NOT_STARTED", "IN_PROGRESS"),
        ("IN_PROGRESS", "PAUSED"),
        ("PAUSED", "IN_PROGRESS"),
        ("IN_PROGRESS", "BLOCKED"),
        ("BLOCKED", "IN_PROGRESS"),
        ("IN_PROGRESS", "READY_FOR_GO_LIVE"),
        ("READY_FOR_GO_LIVE", "GO_LIVE"),
        ("GO_LIVE", "STABILIZATION"),
        ("STABILIZATION", "COMPLETED"),
    ]

    for current, target in transitions:
        unidade = (
            uuid4()
            if target in {"READY_FOR_GO_LIVE", "GO_LIVE", "STABILIZATION", "COMPLETED"}
            else None
        )
        implantacao = _make_implantacao(current, unidade_produtiva_id=unidade)
        assert can_transition(implantacao, target) is True


def test_transicao_invalida_e_bloqueada() -> None:
    implantacao = _make_implantacao("NOT_STARTED")

    with pytest.raises(WizardTransitionError, match="nao permitida"):
        transicionar_implantacao(implantacao, "GO_LIVE")


def test_estados_finais_nao_transicionam() -> None:
    for current in ("COMPLETED", "CANCELLED"):
        implantacao = _make_implantacao(current, unidade_produtiva_id=uuid4())
        with pytest.raises(WizardTransitionError, match="terminal"):
            transicionar_implantacao(implantacao, "IN_PROGRESS")


def test_blocked_nao_vai_direto_para_ready_for_go_live() -> None:
    implantacao = _make_implantacao("BLOCKED", unidade_produtiva_id=uuid4())

    with pytest.raises(WizardTransitionError, match="nao permitida"):
        transicionar_implantacao(implantacao, "READY_FOR_GO_LIVE")


def test_blocked_nao_vai_direto_para_go_live() -> None:
    implantacao = _make_implantacao("BLOCKED", unidade_produtiva_id=uuid4())

    with pytest.raises(WizardTransitionError, match="nao permitida"):
        transicionar_implantacao(implantacao, "GO_LIVE")


@pytest.mark.parametrize(
    ("target_status", "from_status"),
    [
        ("READY_FOR_GO_LIVE", "IN_PROGRESS"),
        ("GO_LIVE", "READY_FOR_GO_LIVE"),
        ("STABILIZATION", "GO_LIVE"),
        ("COMPLETED", "STABILIZATION"),
    ],
)
def test_statuses_criticos_exigem_unidade_produtiva(
    target_status: str,
    from_status: str,
) -> None:
    implantacao = _make_implantacao(from_status)

    with pytest.raises(WizardTransitionError, match="exige unidade_produtiva_id"):
        transicionar_implantacao(implantacao, target_status)


def test_pendencia_critica_aberta_bloqueia_prontidao() -> None:
    implantacao = _make_implantacao("IN_PROGRESS", unidade_produtiva_id=uuid4())

    with pytest.raises(WizardTransitionError, match="pendencia critica aberta"):
        transicionar_implantacao(
            implantacao,
            "READY_FOR_GO_LIVE",
            has_open_critical_blockers=True,
        )


def test_checklist_minimo_falso_bloqueia_prontidao() -> None:
    implantacao = _make_implantacao("IN_PROGRESS", unidade_produtiva_id=uuid4())

    with pytest.raises(WizardTransitionError, match="checklist minimo satisfeito"):
        transicionar_implantacao(
            implantacao,
            "READY_FOR_GO_LIVE",
            minimum_checklist_satisfied=False,
        )


def test_transicao_valida_gera_payload_de_historico() -> None:
    actor_id = uuid4()
    now = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    implantacao = _make_implantacao("NOT_STARTED")

    result = transicionar_implantacao(
        implantacao,
        "IN_PROGRESS",
        ator_usuario_id=actor_id,
        payload_snapshot={"origem": "teste"},
        now=now,
    )

    assert implantacao.status == "IN_PROGRESS"
    assert implantacao.started_at == now
    assert result.campos_atualizados["status"] == "IN_PROGRESS"
    assert result.historico == {
        "evento": "wizard.implantacao.started",
        "status_anterior": "NOT_STARTED",
        "status_novo": "IN_PROGRESS",
        "etapa_anterior": "DIAGNOSTICO",
        "etapa_nova": "DIAGNOSTICO",
        "ator_usuario_id": actor_id,
        "payload_snapshot": {"origem": "teste"},
    }


def test_transicao_para_blocked_marca_semantica_propria() -> None:
    now = datetime(2026, 6, 30, 12, 30, tzinfo=UTC)
    implantacao = _make_implantacao("IN_PROGRESS")

    result = transicionar_implantacao(implantacao, "BLOCKED", now=now)

    assert implantacao.status == "BLOCKED"
    assert implantacao.blocked_at == now
    assert implantacao.bloqueio_critico_aberto is True
    assert result.historico["evento"] == "wizard.implantacao.blocked"


def test_retomada_remove_marcadores_de_pausa_e_bloqueio() -> None:
    now = datetime(2026, 6, 30, 13, 0, tzinfo=UTC)
    implantacao = _make_implantacao("BLOCKED")
    implantacao.blocked_at = datetime(2026, 6, 30, 11, 0, tzinfo=UTC)
    implantacao.paused_at = datetime(2026, 6, 30, 10, 0, tzinfo=UTC)

    transicionar_implantacao(implantacao, "IN_PROGRESS", now=now)

    assert implantacao.status == "IN_PROGRESS"
    assert implantacao.blocked_at is None
    assert implantacao.paused_at is None


def test_cancelamento_permitido_em_qualquer_estado_ativo() -> None:
    for current in ACTIVE_WIZARD_STATUSES:
        unidade = uuid4() if current in {"READY_FOR_GO_LIVE", "GO_LIVE", "STABILIZATION"} else None
        implantacao = _make_implantacao(current, unidade_produtiva_id=unidade)
        result = transicionar_implantacao(implantacao, "CANCELLED")
        assert implantacao.status == "CANCELLED"
        assert result.historico["status_novo"] == "CANCELLED"


def test_state_engine_nao_importa_auth_billing_convites_ou_routers() -> None:
    source = (
        REPO_ROOT / "services" / "api" / "wizard" / "state_engine.py"
    ).read_text(encoding="utf-8")

    forbidden_imports = [
        "from core.models.auth",
        "from core.models.billing",
        "AssinaturaTenant",
        "ConviteAcesso",
        "TenantUsuario",
        "from fastapi",
        "APIRouter",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
