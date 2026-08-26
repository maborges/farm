import pytest
from pydantic import ValidationError
from uuid import uuid4

from ambiental.models import StatusCAR, StatusOutorga, TipoAlerta
from ambiental.router import AlertaCreate
from ambiental.router import CARCreate, CarbonoPeriodoQuery, OutorgaCreate
from core.constants import TenantPermissions


def test_car_create_uses_canonical_status_and_normalizes_contract() -> None:
    payload = CARCreate(
        fazenda_nome="Fazenda Norte",
        codigo_car="CAR-001",
        uf="sp",
        unidade_produtiva_id=uuid4(),
        imovel_rural_id=uuid4(),
    )

    assert payload.status is StatusCAR.PENDENTE
    assert payload.uf == "sp"


@pytest.mark.parametrize(
    "schema_factory",
    [
        lambda: CARCreate(fazenda_nome="F", codigo_car="CAR", uf="SP"),
        lambda: AlertaCreate(),
        lambda: OutorgaCreate(numero_outorga="OUT-1"),
    ],
)
def test_registros_ambientais_exigem_unidade_produtiva(schema_factory) -> None:
    with pytest.raises(ValidationError):
        schema_factory()


def test_outorga_rejects_unknown_use_type() -> None:
    with pytest.raises(ValidationError):
        OutorgaCreate(numero_outorga="OUT-001", tipo_uso="CAPTACAO_INEXISTENTE")


def test_alerta_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        from ambiental.router import AlertaCreate

        AlertaCreate(tipo="TIPO_INEXISTENTE")


def test_carbon_period_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        CarbonoPeriodoQuery(periodo_inicio="2026-02-01", periodo_fim="2026-01-31")


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        ("admin", "ambiental:car:delete"),
        ("gerente", "ambiental:outorgas:create"),
        ("agronomo", "ambiental:monitoramento:create"),
        ("consultor", "ambiental:car:list"),
        ("auditor", "ambiental:carbono:export"),
    ],
)
def test_default_roles_receive_expected_ambiental_permissions(role: str, permission: str) -> None:
    assert TenantPermissions.has_permission(role, permission)


def test_read_only_roles_do_not_receive_ambiental_write_permission() -> None:
    assert not TenantPermissions.has_permission("consultor", "ambiental:car:create")
    assert not TenantPermissions.has_permission("auditor", "ambiental:outorgas:edit")
