from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from pecuaria.advanced_service import PecuariaAdvancedService

pytestmark = pytest.mark.asyncio


async def test_resumo_reproducao_calcula_indicadores(monkeypatch) -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    service = PecuariaAdvancedService(session, tenant_id)

    monkeypatch.setattr(
        service, "_contar_eventos_reproducao", AsyncMock(side_effect=[12, 5, 4, 8, 3])
    )
    monkeypatch.setattr(service, "_media_peso_evento", AsyncMock(side_effect=[34.5, 182.3]))
    monkeypatch.setattr(service, "_media_idade_desmama", AsyncMock(return_value=187.2))
    monkeypatch.setattr(service, "_intervalo_medio_partos", AsyncMock(return_value=390.4))
    monkeypatch.setattr(service, "_contar_diagnosticos_prenhes", AsyncMock(return_value=4))
    monkeypatch.setattr(service, "_contar_perdas_reprodutivas", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_contar_matrizes", AsyncMock(return_value=10))

    resumo = await service._resumo_reproducao()

    assert resumo["total_coberturas"] == 12
    assert resumo["total_diagnosticos_prenhez"] == 5
    assert resumo["total_partos"] == 4
    assert resumo["total_nascimentos"] == 8
    assert resumo["total_desmamas"] == 3
    assert resumo["taxa_prenhez_pct"] == 80.0
    assert resumo["taxa_natalidade_pct"] == 66.67
    assert resumo["taxa_desmama_pct"] == 37.5
    assert resumo["intervalo_medio_partos_dias"] == 390.4
    assert resumo["peso_nascimento_medio_kg"] == 34.5
    assert resumo["peso_desmama_medio_kg"] == 182.3
    assert resumo["idade_media_desmama_dias"] == 187.2
    assert resumo["crias_por_matriz"] == 0.8
    assert resumo["perdas_reprodutivas"] == 1
