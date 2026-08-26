import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from ambiental.models import RegistroCAR
from ambiental.service import AmbientalService


pytestmark = pytest.mark.asyncio


async def test_ambiental_service_inicializa_com_modelo_correto() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    service = AmbientalService(session, tenant_id)

    assert service.model is RegistroCAR
    assert service.session is session
    assert service.tenant_id == tenant_id


async def test_listar_cars_retorna_registros_do_tenant() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    fake_car = MagicMock(spec=RegistroCAR)
    fake_car.id = uuid.uuid4()
    fake_car.tenant_id = tenant_id
    fake_car.created_at = None

    result = MagicMock()
    result.scalars.return_value.all.return_value = [fake_car]
    session.execute.return_value = result

    service = AmbientalService(session, tenant_id)

    cars = await service.listar_cars()

    assert cars == [fake_car]
    assert session.execute.await_count == 2
