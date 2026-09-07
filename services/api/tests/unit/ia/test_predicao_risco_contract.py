from uuid import uuid4

import pytest

from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.schemas import IAPredicaoRiscoResponse


@pytest.mark.asyncio
async def test_fallback_sem_historico_atende_contrato_de_resposta() -> None:
    service = IAPredicaoRiscoService(object(), uuid4())
    service._obter_serie_custos = _empty_series  # type: ignore[method-assign]
    service._obter_serie_receitas = _empty_series  # type: ignore[method-assign]

    result = await service.prever_risco_financeiro(uuid4())
    response = IAPredicaoRiscoResponse(**result)

    assert response.tempo_estimado == "N/A"
    assert response.tendencia_custo == 0.0
    assert response.tendencia_receita == 0.0


async def _empty_series(*_args: object, **_kwargs: object) -> list[float]:
    return []
