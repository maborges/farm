import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agricola.caderno.schemas import EventoCadernoOfflinePayload
from agricola.caderno.service import CadernoCampoService


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


async def test_sincronizar_eventos_offline_carrega_contexto_em_lote():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    talhao_id = uuid.uuid4()

    device = SimpleNamespace(id=device_id, user_id=user_id, fazenda_ids=[unidade_produtiva_id])
    safra = SimpleNamespace(id=safra_id, tenant_id=tenant_id)
    talhao = SimpleNamespace(id=talhao_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id)
    existente = SimpleNamespace(id=uuid.uuid4(), origem_evento="PWA_OFFLINE", origem_id="loc-1", status_evento="SINCRONIZADO")

    session = AsyncMock()
    session.add = MagicMock()
    session.execute.side_effect = [
        FakeScalarResult([safra]),
        FakeScalarResult([talhao]),
        FakeScalarResult([existente]),
    ]

    now = datetime.now(timezone.utc)
    eventos = [
        EventoCadernoOfflinePayload(
            local_id="loc-1",
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo_evento="MONITORAMENTO",  # type: ignore[arg-type]
            status="PENDENTE_SINCRONIZACAO",
            client_created_at=now,
            client_updated_at=now,
            device_id=str(device_id),
            usuario_id=user_id,
            origem_evento="PWA_OFFLINE",
            origem_tecnica="SYNC_PWA",
            payload_operacional={"descricao": "monitoramento 1", "data_registro": date.today().isoformat()},
        ),
        EventoCadernoOfflinePayload(
            local_id="loc-2",
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo_evento="MONITORAMENTO",  # type: ignore[arg-type]
            status="PENDENTE_SINCRONIZACAO",
            client_created_at=now,
            client_updated_at=now,
            device_id=str(device_id),
            usuario_id=user_id,
            origem_evento="PWA_OFFLINE",
            origem_tecnica="SYNC_PWA",
            payload_operacional={"descricao": "monitoramento 2", "data_registro": date.today().isoformat()},
        ),
    ]

    svc = CadernoCampoService(session, tenant_id)
    with patch.object(CadernoCampoService, "_registrar_historico_status", AsyncMock()):
        resultado = await svc.sincronizar_eventos_offline(eventos, device=device)

    assert session.execute.await_count == 3
    assert len(resultado) == 2
    assert resultado[0].status == "SYNCED"
    assert resultado[0].server_id == existente.id
    assert resultado[1].status == "SYNCED"
