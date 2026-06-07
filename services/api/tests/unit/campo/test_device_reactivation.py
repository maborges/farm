from __future__ import annotations

import uuid

import pytest

from campo.schemas import DeviceCreate, DeviceReactivateRequest
from campo.service import DispositivoService
from core.models.auth import Usuario


pytestmark = pytest.mark.asyncio


async def test_device_reactivation_preserves_device_id_and_emits_new_code(session, tenant_id):
    user = Usuario(
        id=uuid.uuid4(),
        email="operador@teste.com",
        username="operador_teste",
        nome_completo="Operador Teste",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    service = DispositivoService(session, tenant_id)
    device = await service.criar(
        DeviceCreate(
            nome="Tablet Campo",
            user_id=user.id,
            fazenda_ids=[uuid.uuid4()],
            modulos=["agricola"],
            expires_days=30,
        )
    )
    await session.commit()

    original_id = device.id
    original_code = device.activation_code

    await service.revogar(device.id, revoked_by=user.id)
    await session.commit()

    reactivated, new_code = await service.reativar(
        DeviceReactivateRequest(device_id=device.id, expires_days=15, motivo="Reposição do aparelho")
    )
    await session.commit()

    assert reactivated.id == original_id
    assert reactivated.status == "PENDENTE"
    assert reactivated.activation_code == new_code
    assert reactivated.activation_code != original_code
    assert reactivated.revoked_at is None
    assert reactivated.revoked_by is None
    assert reactivated.device_fingerprint is None

