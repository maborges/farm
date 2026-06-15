import uuid
from unittest.mock import AsyncMock

import pytest

from ia.ux_telemetry_service import IAUXTelemetryService


class _FailingDB:
    async def execute(self, *args, **kwargs):
        raise RuntimeError("db indisponivel")

    async def rollback(self):
        return None


@pytest.mark.asyncio
async def test_obter_perfil_usuario_ia_retorna_neutro_em_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        IAUXTelemetryService,
        "obter_metricas",
        AsyncMock(side_effect=RuntimeError("metricas indisponiveis")),
    )

    resultado = await IAUXTelemetryService.obter_perfil_usuario_ia(
        db=object(),
        tenant_id=uuid.uuid4(),
        usuario_id=uuid.uuid4(),
    )

    assert resultado["perfil"] == "NEUTRO"
    assert resultado["metadados"]["taxa_execucao"] == 0.0


@pytest.mark.asyncio
async def test_obter_explicacao_perfil_retorna_fallback_em_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        IAUXTelemetryService,
        "obter_perfil_usuario_ia",
        AsyncMock(side_effect=RuntimeError("perfil indisponivel")),
    )

    resultado = await IAUXTelemetryService.obter_explicacao_perfil(
        db=object(),
        tenant_id=uuid.uuid4(),
        usuario_id=uuid.uuid4(),
    )

    assert resultado["perfil"] == "NEUTRO"
    assert resultado["thresholds_referencia"] == {}


@pytest.mark.asyncio
async def test_calcular_progresso_usuario_ia_retorna_fallback_em_falha() -> None:
    resultado = await IAUXTelemetryService.calcular_progresso_usuario_ia(
        db=_FailingDB(),
        tenant_id=uuid.uuid4(),
        usuario_id=uuid.uuid4(),
    )

    assert resultado["progresso"]["perfil"]["atual"] == "NEUTRO"
    assert resultado["mensagem_destaque"]
