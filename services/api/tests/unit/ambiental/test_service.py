import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from ambiental.models import RegistroCAR, OrigemDadosCAR, SituacaoSICAR, StatusCAR
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


async def test_consultar_sicar_atualiza_somente_metadados_ambientais(monkeypatch) -> None:
    car = MagicMock(spec=RegistroCAR)
    car.codigo_car = "SP-1234567-ABCDEFGH.IJKL.MNOP/2024-01"
    car.fazenda_nome = "Fazenda"
    car.imovel_rural_id = uuid.uuid4()
    car.unidade_produtiva_id = uuid.uuid4()
    service = AmbientalService(AsyncMock(), uuid.uuid4())
    service._get_car = AsyncMock(return_value=car)
    monkeypatch.setattr(
        "integracoes.regulatorias.service.validar_formato_car", lambda _: True
    )
    monkeypatch.setattr(
        "integracoes.regulatorias.service.consultar_car",
        AsyncMock(return_value={"status": "AT", "area_ha": 120.5}),
    )

    result = await service.consultar_sicar(car.id)

    assert result is car
    assert car.situacao_sicar == SituacaoSICAR.VALIDO.value
    assert car.origem_dados == OrigemDadosCAR.SICAR.value
    assert car.status == StatusCAR.ATIVO.value
    assert car.data_ultima_consulta_sicar == date.today()
    assert car.codigo_car == "SP-1234567-ABCDEFGH.IJKL.MNOP/2024-01"
    assert car.imovel_rural_id is not None


async def test_consultar_sicar_registra_erro_sem_alterar_identificacao(monkeypatch) -> None:
    car = MagicMock(spec=RegistroCAR)
    car.codigo_car = "SP-1234567-ABCDEFGH.IJKL.MNOP/2024-01"
    car.imovel_rural_id = uuid.uuid4()
    service = AmbientalService(AsyncMock(), uuid.uuid4())
    service._get_car = AsyncMock(return_value=car)
    monkeypatch.setattr(
        "integracoes.regulatorias.service.validar_formato_car", lambda _: True
    )
    monkeypatch.setattr(
        "integracoes.regulatorias.service.consultar_car",
        AsyncMock(return_value=None),
    )

    await service.consultar_sicar(car.id)

    assert car.situacao_sicar == SituacaoSICAR.ERRO_CONSULTA.value
    assert car.data_ultima_consulta_sicar == date.today()
    assert car.codigo_car == "SP-1234567-ABCDEFGH.IJKL.MNOP/2024-01"
    assert car.imovel_rural_id is not None
