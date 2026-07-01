from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.exceptions import BusinessRuleError
from wizard.models import (
    FINAL_WIZARD_STATUSES,
    ImplantacaoOperacional,
    WizardStatus,
)

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


_TRANSICOES: dict[str, set[str]] = {
    WizardStatus.NOT_STARTED.value: {
        WizardStatus.IN_PROGRESS.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.IN_PROGRESS.value: {
        WizardStatus.PAUSED.value,
        WizardStatus.BLOCKED.value,
        WizardStatus.READY_FOR_GO_LIVE.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.PAUSED.value: {
        WizardStatus.IN_PROGRESS.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.BLOCKED.value: {
        WizardStatus.IN_PROGRESS.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.READY_FOR_GO_LIVE.value: {
        WizardStatus.GO_LIVE.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.GO_LIVE.value: {
        WizardStatus.STABILIZATION.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.STABILIZATION.value: {
        WizardStatus.COMPLETED.value,
        WizardStatus.CANCELLED.value,
    },
    WizardStatus.COMPLETED.value: set(),
    WizardStatus.CANCELLED.value: set(),
}

_STATUSES_COM_UNIDADE = {
    WizardStatus.READY_FOR_GO_LIVE.value,
    WizardStatus.GO_LIVE.value,
    WizardStatus.STABILIZATION.value,
    WizardStatus.COMPLETED.value,
}
_STATUSES_COM_PRONTIDAO = {
    WizardStatus.READY_FOR_GO_LIVE.value,
    WizardStatus.GO_LIVE.value,
}
_EVENTOS_TRANSICAO = {
    (WizardStatus.NOT_STARTED.value, WizardStatus.IN_PROGRESS.value): "wizard.implantacao.started",
    (WizardStatus.IN_PROGRESS.value, WizardStatus.PAUSED.value): "wizard.implantacao.paused",
    (WizardStatus.PAUSED.value, WizardStatus.IN_PROGRESS.value): "wizard.implantacao.resumed",
    (WizardStatus.IN_PROGRESS.value, WizardStatus.BLOCKED.value): "wizard.implantacao.blocked",
    (WizardStatus.BLOCKED.value, WizardStatus.IN_PROGRESS.value): "wizard.implantacao.unblocked",
    (
        WizardStatus.IN_PROGRESS.value,
        WizardStatus.READY_FOR_GO_LIVE.value,
    ): "wizard.implantacao.ready_for_go_live",
    (
        WizardStatus.READY_FOR_GO_LIVE.value,
        WizardStatus.GO_LIVE.value,
    ): "wizard.implantacao.go_live",
    (
        WizardStatus.GO_LIVE.value,
        WizardStatus.STABILIZATION.value,
    ): "wizard.implantacao.stabilization_started",
    (
        WizardStatus.STABILIZATION.value,
        WizardStatus.COMPLETED.value,
    ): "wizard.implantacao.completed",
}


class WizardTransitionError(BusinessRuleError):
    """Violacao da maquina de estados do Wizard."""


@dataclass(frozen=True)
class WizardTransitionResult:
    novo_status: str
    campos_atualizados: dict[str, Any]
    historico: dict[str, Any]


def _status_value(status: str | WizardStatus) -> str:
    return status.value if isinstance(status, WizardStatus) else status


def _ensure_status_oficial(status: str) -> None:
    if status not in _TRANSICOES:
        raise WizardTransitionError(f"Status '{status}' nao pertence ao Wizard oficial.")


def _allowed_targets(status_atual: str) -> set[str]:
    permitidos = _TRANSICOES.get(status_atual)
    if permitidos is None:
        raise WizardTransitionError(f"Status atual '{status_atual}' nao esta mapeado.")
    return permitidos


def _ensure_transition_allowed(status_atual: str, novo_status: str) -> None:
    permitidos = _allowed_targets(status_atual)
    if novo_status in permitidos:
        return
    if status_atual in FINAL_WIZARD_STATUSES:
        raise WizardTransitionError(
            f"Status final '{status_atual}' e terminal e nao permite transicoes."
        )
    raise WizardTransitionError(
        f"Transicao '{status_atual}' -> '{novo_status}' nao permitida. "
        f"Permitidos: {sorted(permitidos) or 'nenhum'}."
    )


def _ensure_unidade_produtiva(implantacao: ImplantacaoOperacional, novo_status: str) -> None:
    if novo_status not in _STATUSES_COM_UNIDADE:
        return
    if implantacao.unidade_produtiva_id is not None:
        return
    raise WizardTransitionError(
        f"Transicao para '{novo_status}' exige unidade_produtiva_id."
    )


def _ensure_prontidao(
    novo_status: str,
    *,
    minimum_checklist_satisfied: bool,
    has_open_critical_blockers: bool,
) -> None:
    if novo_status not in _STATUSES_COM_PRONTIDAO:
        return
    if has_open_critical_blockers:
        raise WizardTransitionError(
            f"Transicao para '{novo_status}' bloqueada por pendencia critica aberta."
        )
    if not minimum_checklist_satisfied:
        raise WizardTransitionError(
            f"Transicao para '{novo_status}' exige checklist minimo satisfeito."
        )


def _event_name(status_atual: str, novo_status: str) -> str:
    return _EVENTOS_TRANSICAO.get(
        (status_atual, novo_status),
        f"wizard.implantacao.status_changed.{status_atual.lower()}_to_{novo_status.lower()}",
    )


def _status_updates(
    implantacao: ImplantacaoOperacional,
    novo_status: str,
    *,
    has_open_critical_blockers: bool,
    now: datetime,
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "status": novo_status,
        "updated_at": now,
    }
    if novo_status == WizardStatus.IN_PROGRESS.value:
        updates["started_at"] = implantacao.started_at or now
        updates["paused_at"] = None
        updates["blocked_at"] = None
        updates["bloqueio_critico_aberto"] = has_open_critical_blockers
    if novo_status == WizardStatus.PAUSED.value:
        updates["paused_at"] = now
    if novo_status == WizardStatus.BLOCKED.value:
        updates["blocked_at"] = now
        updates["bloqueio_critico_aberto"] = True
    if novo_status == WizardStatus.READY_FOR_GO_LIVE.value:
        updates["ready_for_go_live_at"] = now
        updates["bloqueio_critico_aberto"] = has_open_critical_blockers
    if novo_status == WizardStatus.GO_LIVE.value:
        updates["go_live_at"] = now
    if novo_status == WizardStatus.STABILIZATION.value:
        updates["stabilization_started_at"] = now
    if novo_status == WizardStatus.COMPLETED.value:
        updates["completed_at"] = now
    if novo_status == WizardStatus.CANCELLED.value:
        updates["cancelled_at"] = now
    return updates


def _history_payload(
    implantacao: ImplantacaoOperacional,
    status_atual: str,
    novo_status: str,
    *,
    ator_usuario_id: Any,
    payload_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "evento": _event_name(status_atual, novo_status),
        "status_anterior": status_atual,
        "status_novo": novo_status,
        "etapa_anterior": implantacao.etapa_atual,
        "etapa_nova": implantacao.etapa_atual,
        "ator_usuario_id": ator_usuario_id,
        "payload_snapshot": payload_snapshot or {},
    }


def _apply_updates(
    implantacao: ImplantacaoOperacional,
    updates: dict[str, Any],
) -> None:
    for campo, valor in updates.items():
        setattr(implantacao, campo, valor)


def can_transition(
    implantacao: ImplantacaoOperacional,
    novo_status: str | WizardStatus,
    *,
    minimum_checklist_satisfied: bool = True,
    has_open_critical_blockers: bool = False,
) -> bool:
    try:
        validate_transition(
            implantacao,
            novo_status,
            minimum_checklist_satisfied=minimum_checklist_satisfied,
            has_open_critical_blockers=has_open_critical_blockers,
        )
    except WizardTransitionError:
        return False
    return True


def validate_transition(
    implantacao: ImplantacaoOperacional,
    novo_status: str | WizardStatus,
    *,
    minimum_checklist_satisfied: bool = True,
    has_open_critical_blockers: bool = False,
) -> None:
    status_atual = _status_value(implantacao.status)
    destino = _status_value(novo_status)
    _ensure_status_oficial(status_atual)
    _ensure_status_oficial(destino)
    _ensure_transition_allowed(status_atual, destino)
    _ensure_unidade_produtiva(implantacao, destino)
    _ensure_prontidao(
        destino,
        minimum_checklist_satisfied=minimum_checklist_satisfied,
        has_open_critical_blockers=has_open_critical_blockers,
    )


def transicionar_implantacao(
    implantacao: ImplantacaoOperacional,
    novo_status: str | WizardStatus,
    *,
    ator_usuario_id: Any = None,
    payload_snapshot: dict[str, Any] | None = None,
    minimum_checklist_satisfied: bool = True,
    has_open_critical_blockers: bool = False,
    now: datetime | None = None,
) -> WizardTransitionResult:
    status_atual = _status_value(implantacao.status)
    destino = _status_value(novo_status)
    instante = now or datetime.now(UTC)

    validate_transition(
        implantacao,
        destino,
        minimum_checklist_satisfied=minimum_checklist_satisfied,
        has_open_critical_blockers=has_open_critical_blockers,
    )

    updates = _status_updates(
        implantacao,
        destino,
        has_open_critical_blockers=has_open_critical_blockers,
        now=instante,
    )
    _apply_updates(implantacao, updates)
    historico = _history_payload(
        implantacao,
        status_atual,
        destino,
        ator_usuario_id=ator_usuario_id,
        payload_snapshot=payload_snapshot,
    )
    return WizardTransitionResult(
        novo_status=destino,
        campos_atualizados=updates,
        historico=historico,
    )


__all__ = [
    "WizardTransitionError",
    "WizardTransitionResult",
    "_TRANSICOES",
    "can_transition",
    "transicionar_implantacao",
    "validate_transition",
]
