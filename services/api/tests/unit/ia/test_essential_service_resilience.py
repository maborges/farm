import uuid
from unittest.mock import AsyncMock

import pytest

from ia.essential_service import IAEssentialService
from ia.ux_telemetry_service import IAUXTelemetryService


@pytest.mark.asyncio
async def test_obter_essencial_faz_fallback_quando_telemetria_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        IAUXTelemetryService,
        "obter_perfil_usuario_ia",
        AsyncMock(side_effect=RuntimeError("perfil indisponivel")),
    )
    monkeypatch.setattr(
        IAUXTelemetryService,
        "obter_contexto_decisao_recente",
        AsyncMock(side_effect=RuntimeError("contexto indisponivel")),
    )
    monkeypatch.setattr(
        IAEssentialService,
        "resolve_safra_id",
        AsyncMock(return_value=None),
    )

    resultado = await IAEssentialService.obter_essencial(
        session=None,
        tenant_id=uuid.uuid4(),
        safra_id=None,
        usuario_id=uuid.uuid4(),
    )

    assert resultado["prioridade"] == "NORMAL"
    assert resultado["tipo"] == "STATUS"
    assert resultado["titulo"] == "Aguardando Safra"
    assert resultado["rota"] == "/dashboard/agricola/safras"
    assert resultado["acao_label"] == "Cadastrar Safra: R$ 0.00"
