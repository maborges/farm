"""Guardrails unitários do recebimento canônico 01E."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.exceptions import BusinessRuleError
from operacional.models.estoque import RequisicaoItemEvento
from operacional.schemas.estoque import RecebimentoRequisicaoRequest
from operacional.services.requisicao_recebimento_service import RequisicaoRecebimentoService


def test_migration_01e_is_incremental_and_reversible() -> None:
    source = Path("services/api/migrations/versions/20260925_material_requisition_01e.py").read_text()
    assert 'revision: str = "20260925_material_requisition_01e"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260925_material_requisition_01d"' in source
    assert 'evento_entrega_id' in source
    assert 'fk_req_item_evento_tenant_entrega_origem' in source
    assert 'op.drop_column("estoque_requisicao_item_eventos", "evento_entrega_id"' in source


def test_receipt_event_has_explicit_delivery_provenance_and_result() -> None:
    assert "evento_entrega_id" in RequisicaoItemEvento.__table__.c
    assert "resultado_conferencia" in RequisicaoItemEvento.__table__.c
    names = {constraint.name for constraint in RequisicaoItemEvento.__table__.constraints}
    assert "fk_req_item_evento_tenant_entrega_origem" in names
    assert "ck_req_item_evento_resultado_conferencia" in names


def test_receipt_command_requires_version_and_idempotency() -> None:
    with pytest.raises(ValidationError):
        RecebimentoRequisicaoRequest(
            item_id=uuid4(),
            entrega_evento_id=uuid4(),
            quantidade_recebida=1,
            resultado="RECEBIDO_INTEGRAL",
        )


def test_receipt_retry_payload_is_exact() -> None:
    delivery_id = uuid4()
    item_id = uuid4()
    data = RecebimentoRequisicaoRequest(
        item_id=item_id,
        entrega_evento_id=delivery_id,
        quantidade_recebida=92,
        resultado="DIVERGENTE",
        base_version=4,
        client_operation_id="receipt-1",
        dispositivo_id=uuid4(),
        motivo="Entrega parcial",
    )
    event = SimpleNamespace(
        item_requisicao_id=item_id,
        evento_entrega_id=delivery_id,
        tipo_evento="RECEBIMENTO",
        quantidade=92,
        resultado_conferencia="DIVERGENTE",
    )
    RequisicaoRecebimentoService._validate_retry(event, data)
    with pytest.raises(BusinessRuleError):
        RequisicaoRecebimentoService._validate_retry(
            event,
            data.model_copy(update={"quantidade_recebida": 91}),
        )


def test_receipt_service_does_not_reference_physical_stock_mutation() -> None:
    source = Path(
        "services/api/operacional/services/requisicao_recebimento_service.py"
    ).read_text()
    assert "EstoqueMovimento" not in source
    assert "SaldoEstoque" not in source
    assert "LoteEstoque" not in source
    assert "ReservaEstoque" not in source


def test_receipt_retry_resolves_authorization_before_idempotent_ack() -> None:
    source = Path(
        "services/api/operacional/services/requisicao_recebimento_service.py"
    ).read_text()
    command_body = source[source.index("    async def receber("):source.index("    async def _lock_request_item")]
    assert command_body.index("_lock_request_item") < command_body.index("_find_idempotent")
    assert "existing.usuario_id != usuario_id" in command_body
