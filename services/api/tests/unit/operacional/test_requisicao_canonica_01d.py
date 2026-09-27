"""Guardrails unitários da reserva/picking/entrega canônica 01D."""

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.exceptions import BusinessRuleError
from operacional.models.estoque import EstoqueMovimento, RequisicaoItemEvento, ReservaEstoque
from operacional.schemas.estoque import RequisicaoItemOperacaoCanonicaRequest
from operacional.services.requisicao_canonica_service import RequisicaoCanonicaService


def test_migration_01d_is_incremental_and_reversible() -> None:
    source = Path("services/api/migrations/versions/20260925_material_requisition_01d.py").read_text()
    assert 'revision: str = "20260925_material_requisition_01d"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260925_material_requisition_01c1"' in source
    assert 'op.drop_column("estoque_reservas", "client_operation_id"' in source
    assert 'uq_estoque_movimentos_tenant_req_item_evento' in source


def test_reservation_and_event_contracts_are_canonical() -> None:
    assert "quantidade_consumida" in ReservaEstoque.__table__.c
    assert "client_operation_id" in ReservaEstoque.__table__.c
    assert "requisicao_item_evento_id" in EstoqueMovimento.__table__.c
    assert "client_operation_id" in RequisicaoItemEvento.__table__.c
    names = {c.name for c in EstoqueMovimento.__table__.constraints}
    assert "uq_estoque_movimentos_tenant_req_item_evento" in names


def test_canonical_command_requires_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        RequisicaoItemOperacaoCanonicaRequest(quantidade=1)


def test_retry_payload_is_exact_and_does_not_accept_second_fact() -> None:
    item_id = uuid4()
    deposito_id = uuid4()
    event = SimpleNamespace(
        item_requisicao_id=item_id,
        tipo_evento="ENTREGA",
        quantidade=Decimal("60"),
        deposito_id=deposito_id,
        lote_id=None,
    )
    RequisicaoCanonicaService._validate_retry(
        event,
        item_id=item_id,
        tipo="ENTREGA",
        quantidade=60,
        deposito_id=None,
        lote_id=None,
    )
    with pytest.raises(BusinessRuleError):
        RequisicaoCanonicaService._validate_retry(
            event,
            item_id=item_id,
            tipo="ENTREGA",
            quantidade=61,
            deposito_id=None,
            lote_id=None,
        )


def test_reservation_remaining_is_not_the_original_quantity() -> None:
    reserva = SimpleNamespace(quantidade=100, quantidade_consumida=60)
    assert RequisicaoCanonicaService._reserva_restante(reserva) == 40
