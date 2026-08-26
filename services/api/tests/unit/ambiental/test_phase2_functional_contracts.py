import uuid
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import TypeAdapter, ValidationError

from ambiental import router as ambiental_router
from ambiental.models import (
    SeveridadeAlerta,
    StatusAlerta,
    StatusCAR,
    StatusOutorga,
    TipoAlerta,
)
from core.exceptions import EntityNotFoundError


@pytest.mark.parametrize("enum_type", [StatusCAR])
def test_filtro_car_rejeita_valor_de_dominio_invalido(enum_type: type) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(enum_type).validate_python("INVALIDO")


@pytest.mark.parametrize(
    ("enum_type", "query"),
    [
        (StatusAlerta, "status=INVALIDO"),
        (SeveridadeAlerta, "severidade=INVALIDO"),
        (TipoAlerta, "tipo=INVALIDO"),
        (StatusOutorga, "status=INVALIDO"),
    ],
)
def test_listas_rejeitam_filtros_de_dominio_invalidos(enum_type: type, query: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(enum_type).validate_python("INVALIDO")


@pytest.mark.parametrize(
    "payload",
    [
        {"area_ha": -1},
        {"latitude": 91},
        {"longitude": -181},
    ],
)
def test_alerta_rejeita_medidas_geograficas_invalidas(payload: dict) -> None:
    with pytest.raises(ValueError):
        ambiental_router.AlertaCreate(**payload)


def test_outorga_rejeita_vazao_negativa() -> None:
    with pytest.raises(ValueError):
        ambiental_router.OutorgaCreate(numero_outorga="OUT-1", vazao_outorgada_ls=-0.1)


def test_schemas_expoem_enums_de_dominio() -> None:
    car = ambiental_router.CARCreate(fazenda_nome="F", codigo_car="CAR", uf="SP")
    assert car.status is StatusCAR.PENDENTE
    assert ambiental_router.AlertaCreate().tipo is TipoAlerta.DESMATAMENTO
    assert ambiental_router.AlertaCreate().severidade is SeveridadeAlerta.MEDIA
    assert ambiental_router.OutorgaCreate(numero_outorga="OUT-1").tipo_uso.value == "IRRIGACAO"
    alerta = ambiental_router.AlertaUpdate(status=StatusAlerta.RESOLVIDO)
    assert alerta.status is StatusAlerta.RESOLVIDO


@pytest.mark.asyncio
async def test_exportacao_retorna_404_quando_relatorio_nao_existe() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    export = patch.object(
        ambiental_router.AmbientalService,
        "exportar_pdf_carbono",
        new=AsyncMock(side_effect=EntityNotFoundError("ausente")),
    )
    with export:
        with pytest.raises(ambiental_router.HTTPException) as error:
            await ambiental_router.exportar_relatorio_carbono_pdf(
                relatorio_id=999,
                tenant_id=tenant_id,
                session=session,
            )

    assert error.value.status_code == 404
