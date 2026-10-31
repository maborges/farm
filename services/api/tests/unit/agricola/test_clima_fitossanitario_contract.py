from datetime import date, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from agricola.climatico.models import RegistroClima
from agricola.climatico.schemas import (
    ClimaInteligenciaResponse,
    ModeloFitossanitarioCreate,
    RiscoDoencaResponse,
)
from agricola.climatico.service import ClimaService

TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _model(tenant_id, cultura, doenca, limite):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        cultura=cultura,
        doenca=doenca,
        regras_risco={
            "condicoes": [
                {"variavel": "temp_media_c", "operador": ">=", "valor": limite}
            ]
        },
    )


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.statements = []

    async def execute(self, statement, *args):
        self.statements.append(statement)
        return _Result(self.responses.pop(0))


def _seven_days(**values):
    base = date(2026, 10, 1)
    return [
        RegistroClima(
            tenant_id=TENANT_A,
            unidade_produtiva_id=uuid4(),
            data_registro=base + timedelta(days=offset),
            fonte="TEST",
            **values,
        )
        for offset in range(7)
    ]


def test_missing_climate_variable_is_not_converted_to_zero():
    stats, invalid = ClimaService._calcular_stats_climaticas(
        _seven_days(temp_media_c=None)
    )

    assert stats["temp_media_c"] is None
    assert "temp_media_c" not in invalid


def test_legitimate_zero_climate_measurement_is_preserved():
    stats, invalid = ClimaService._calcular_stats_climaticas(
        _seven_days(temp_media_c=0.0)
    )

    assert stats["temp_media_c"] == 0.0
    assert "temp_media_c" not in invalid


def test_non_finite_climate_value_is_reported_as_invalid():
    stats, invalid = ClimaService._calcular_stats_climaticas(
        _seven_days(temp_media_c=float("nan"))
    )

    assert stats["temp_media_c"] is None
    assert "temp_media_c" in invalid


def test_model_evaluation_does_not_score_missing_required_variable():
    rules = {
        "condicoes": [
            {"variavel": "temp_media_c", "operador": "<=", "valor": 0}
        ]
    }

    assert ClimaService._avaliar_modelo(rules, {"temp_media_c": None}) is None


def test_zero_measurement_can_satisfy_a_valid_zero_threshold():
    rules = {
        "condicoes": [
            {"variavel": "temp_media_c", "operador": "<=", "valor": 0}
        ]
    }

    assert ClimaService._avaliar_modelo(rules, {"temp_media_c": 0.0}) == 100


def test_legacy_score_fields_are_deprecated_compatibility_aliases():
    schema = RiscoDoencaResponse.model_json_schema()

    assert schema["properties"]["probabilidade_pct"]["deprecated"] is True
    assert schema["properties"]["favorabilidade_pct"]


def test_invalid_model_json_is_rejected_by_write_schema():
    with pytest.raises(ValidationError):
        ModeloFitossanitarioCreate(
            cultura="Café",
            doenca="Ferrugem",
            regras_risco={
                "condicoes": [
                    {"variavel": "umidade_rel_pct", "operador": "approx", "valor": 80}
                ]
            },
        )


@pytest.mark.parametrize(
    "rules",
    [
        {"condicoes": []},
        {"condicoes": [{"variavel": "vento_kmh", "operador": ">=", "valor": 1}]},
        {"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": float("inf")}]},
        {"condicoes": [{"variavel": "temp_media_c", "operador": "between", "min": 25, "max": 20}]},
        {"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 20, "peso": 0}]},
        {
            "condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 20}],
            "nivel_medio_pct": 70,
            "nivel_alto_pct": 60,
        },
    ],
)
def test_invalid_model_rule_shapes_are_rejected(rules):
    with pytest.raises(ValidationError):
        ModeloFitossanitarioCreate(cultura="Café", doenca="Ferrugem", regras_risco=rules)


@pytest.mark.asyncio
async def test_active_crop_without_models_has_explicit_status():
    session = _Session([("Café",)], [], [])
    result = await ClimaService(session, TENANT_A)._calcular_risco_doencas(
        uuid4(), _seven_days(temp_media_c=22)
    )

    assert result.status == "SEM_MODELO_APLICAVEL"
    assert result.resultados == []


@pytest.mark.asyncio
async def test_no_active_crop_has_distinct_status():
    session = _Session([])
    result = await ClimaService(session, TENANT_A)._calcular_risco_doencas(
        uuid4(), []
    )

    assert result.status == "SEM_CULTURA_ATIVA"


@pytest.mark.asyncio
async def test_public_intelligence_response_exposes_insufficient_history_state():
    session = _Session(None, [], [], [("Café",)], [], [_model(None, "Café", "Ferrugem", 18)])
    raw = await ClimaService(session, TENANT_A).get_analise_avancada(uuid4())
    response = ClimaInteligenciaResponse.model_validate(raw)

    assert response.risco_fitossanitario_status == "DADOS_CLIMATICOS_INSUFICIENTES"
    assert response.agricultura is None


@pytest.mark.asyncio
async def test_insufficient_history_does_not_emit_a_low_score():
    global_model = _model(None, "Café", "Ferrugem", 18)
    session = _Session([("Café",)], [], [global_model])
    result = await ClimaService(session, TENANT_A)._calcular_risco_doencas(
        uuid4(), _seven_days(temp_media_c=22)[:3]
    )

    assert result.status == "DADOS_CLIMATICOS_INSUFICIENTES"
    assert result.resultados == []


@pytest.mark.asyncio
async def test_invalid_required_climate_value_has_explicit_status():
    global_model = _model(None, "Café", "Ferrugem", 18)
    session = _Session([("Café",)], [], [global_model])
    result = await ClimaService(session, TENANT_A)._calcular_risco_doencas(
        uuid4(), _seven_days(temp_media_c=float("nan"))
    )

    assert result.status == "DADOS_CLIMATICOS_INVALIDOS"
    assert result.resultados == []


@pytest.mark.asyncio
async def test_tenant_rule_overrides_only_matching_disease_and_is_tenant_scoped():
    tenant_model = _model(TENANT_A, "Café", "Ferrugem", 30)
    global_rust = _model(None, "Café", "Ferrugem", 10)
    global_cercospora = _model(None, "Café", "Cercosporiose", 10)
    session = _Session(
        [("Café",)],
        [tenant_model],
        [global_rust, global_cercospora],
    )

    result = await ClimaService(session, TENANT_A)._calcular_risco_doencas(
        uuid4(), _seven_days(temp_media_c=22)
    )

    by_disease = {item["doenca"]: item for item in result.resultados}
    assert result.status == "CALCULADO"
    assert by_disease["Ferrugem"]["favorabilidade_pct"] == 0
    assert by_disease["Cercosporiose"]["favorabilidade_pct"] == 100
    tenant_query = session.statements[1].compile(dialect=postgresql.dialect())
    assert str(TENANT_A) in str(tenant_query.params)
    assert str(TENANT_B) not in str(tenant_query.params)
