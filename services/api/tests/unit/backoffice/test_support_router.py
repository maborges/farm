from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.routers import backoffice as backoffice_router


def _build_client(session, claims):
    app = FastAPI()
    app.include_router(backoffice_router.router, prefix="/api/v1")
    app.dependency_overrides[backoffice_router.get_current_admin] = lambda: claims
    app.dependency_overrides[backoffice_router.get_session] = lambda: session
    return TestClient(app)


def test_admin_reply_to_ticket_uses_claims_sub_as_user_id():
    ticket_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    chamado = SimpleNamespace(id=ticket_id)
    session = AsyncMock()
    session.get = AsyncMock(return_value=chamado)
    session.commit = AsyncMock()
    session.add = Mock(side_effect=lambda msg: (
        setattr(msg, "id", uuid.uuid4()),
        setattr(msg, "created_at", datetime.now(timezone.utc)),
    ))

    claims = {"sub": str(admin_id), "is_superuser": True}
    client = _build_client(session, claims)

    response = client.post(
        f"/api/v1/backoffice/tickets/{ticket_id}/reply",
        json={"conteudo": "Resposta do suporte"},
    )

    assert response.status_code == 200
    assert response.json()["usuario_id"] == str(admin_id)
    assert response.json()["chamado_id"] == str(ticket_id)
    session.get.assert_awaited_once()
    session.commit.assert_awaited_once()
