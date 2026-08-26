import pytest
from pydantic import ValidationError
from uuid import uuid4

from ambiental.models import StatusCAR, StatusOutorga, TipoAlerta
from ambiental.router import AlertaCreate
from ambiental.router import CARCreate, CarbonoEmissaoCreate, CarbonoPeriodoQuery, CarbonoProjetoCreate, OutorgaCreate
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


def test_carbono_exige_unidade_produtiva() -> None:
    with pytest.raises(ValidationError):
        CarbonoEmissaoCreate(escopo=1, categoria="diesel", quantidade=1, unidade="L", data_referencia="2026-08-26T00:00:00")
    with pytest.raises(ValidationError):
        CarbonoProjetoCreate(nome="Projeto", tipo="reflorestamento", area_ha=1)


def test_carbono_rejeita_valores_negativos_e_textos_vazios() -> None:
    unidade_id = uuid4()
    with pytest.raises(ValidationError):
        CarbonoEmissaoCreate(
            unidade_produtiva_id=unidade_id,
            escopo=1,
            categoria="",
            quantidade=1,
            unidade="L",
            fator_emissao=-1,
            data_referencia="2026-08-26T00:00:00",
        )
    with pytest.raises(ValidationError):
        CarbonoProjetoCreate(
            unidade_produtiva_id=unidade_id,
            nome="Projeto",
            tipo="reflorestamento",
            area_ha=1,
            creditos_vendidos=-1,
        )


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
