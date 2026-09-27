from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.exceptions import BusinessRuleError
from operacional.domain.requisicao_material import (
    CompatibilidadeLegado,
    NaturezaItem,
    TipoRequisicaoItemEvento,
)
from operacional.models.estoque import (
    ItemRequisicao,
    RequisicaoItemEvento,
    RequisicaoMaterial,
)
from operacional.schemas.estoque import RequisicaoItemEventoCreate
from operacional.services.requisicao_fundacao_service import (
    RequisicaoItemEventoService,
)


def _valid_event_data(**overrides: object) -> RequisicaoItemEventoCreate:
    values: dict[str, object] = {
        "item_id": uuid4(),
        "tipo_evento": TipoRequisicaoItemEvento.SEPARACAO,
        "quantidade": Decimal("2.5"),
        "unidade": "KG",
        "client_operation_id": "device-op-001",
    }
    values.update(overrides)
    return RequisicaoItemEventoCreate.model_validate(values)


def test_canonical_enums_and_item_snapshot_are_explicit() -> None:
    assert NaturezaItem.CONSUMIVEL.value == "CONSUMIVEL"
    assert NaturezaItem.RETORNAVEL.value == "RETORNAVEL"
    assert TipoRequisicaoItemEvento.ENTREGA.value == "ENTREGA"
    assert CompatibilidadeLegado.LEGACY_DELIVERED.value == "LEGACY_DELIVERED"
    assert "tenant_id" in ItemRequisicao.__table__.c
    assert "natureza_item" in ItemRequisicao.__table__.c


def test_event_schema_rejects_invalid_quantity_and_unknown_type() -> None:
    with pytest.raises(ValidationError):
        _valid_event_data(quantidade=0)

    with pytest.raises(ValidationError):
        _valid_event_data(tipo_evento="CONSUMO_INEXISTENTE")


def test_event_schema_supports_expected_aggregate_version() -> None:
    data = _valid_event_data(versao_requisicao_esperada=3)
    assert data.versao_requisicao_esperada == 3


def test_event_model_declares_append_only_payload_and_idempotency_key() -> None:
    columns = RequisicaoItemEvento.__table__.c
    assert {"tenant_id", "requisicao_id", "item_requisicao_id"}.issubset(columns.keys())
    assert {"versao_requisicao", "client_operation_id", "provenance"}.issubset(columns.keys())
    unique_names = {constraint.name for constraint in RequisicaoItemEvento.__table__.constraints}
    assert "uq_req_item_evento_tenant_client_operation" in unique_names


def test_event_service_rejects_same_key_with_different_fact() -> None:
    existing = RequisicaoItemEvento(
        tenant_id=uuid4(),
        requisicao_id=uuid4(),
        item_requisicao_id=uuid4(),
        tipo_evento=TipoRequisicaoItemEvento.SEPARACAO.value,
        quantidade=Decimal("2.5"),
        unidade="KG",
        client_operation_id="device-op-001",
    )
    data = _valid_event_data(item_id=uuid4())

    with pytest.raises(BusinessRuleError, match="client_operation_id"):
        RequisicaoItemEventoService.validar_retentativa(existing, data)


def test_event_service_accepts_exact_retry_without_new_fact() -> None:
    item_id = uuid4()
    data = _valid_event_data(item_id=item_id)
    existing = RequisicaoItemEvento(
        tenant_id=uuid4(),
        requisicao_id=uuid4(),
        item_requisicao_id=item_id,
        tipo_evento=data.tipo_evento.value,
        quantidade=data.quantidade,
        unidade=data.unidade,
        client_operation_id=data.client_operation_id,
    )

    assert RequisicaoItemEventoService.validar_retentativa(existing, data) is None


def test_event_service_rejects_stale_aggregate_version() -> None:
    request = RequisicaoMaterial(version=4)
    data = _valid_event_data(versao_requisicao_esperada=3)

    with pytest.raises(BusinessRuleError, match="obsoleta"):
        RequisicaoItemEventoService._validate_expected_version(request, data)


def test_service_source_enforces_tenant_on_request_and_item_lookup() -> None:
    source = Path("services/api/operacional/services/requisicao_fundacao_service.py").read_text(
        encoding="utf-8"
    )
    assert "RequisicaoMaterial.tenant_id == self.tenant_id" in source
    assert "ItemRequisicao.tenant_id == self.tenant_id" in source


def test_request_has_single_aggregate_version_and_legacy_classification() -> None:
    columns = RequisicaoMaterial.__table__.c
    assert "version" in columns
    assert "compatibilidade_legado" in columns
    assert "versao_requisicao" not in ItemRequisicao.__table__.c
