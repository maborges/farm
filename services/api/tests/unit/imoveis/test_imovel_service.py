import uuid
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_get_imoveis_by_fazenda_sem_fazenda_retorna_todos_do_tenant():
    from imoveis.services.imovel_service import ImovelService

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock

    service = ImovelService(session)
    tenant_id = uuid.uuid4()

    imoveis = await service.get_imoveis_by_fazenda(None, tenant_id)

    assert imoveis == []
    session.execute.assert_called_once()
    query_str = str(session.execute.call_args[0][0])
    assert "tenant_id" in query_str
    assert "unidade_produtiva_id = :" not in query_str


async def test_atualizar_imovel_altera_nirf_e_area_com_justificativa():
    from imoveis.models.imovel import SituacaoImovel
    from imoveis.services.imovel_service import ImovelService

    session = AsyncMock()
    service = ImovelService(session)
    service.validar_nirf_unico = AsyncMock(return_value=(True, "NIRF disponível"))
    service.validar_area_consistente = AsyncMock(return_value=(True, "Área consistente", Decimal("100")))
    service.calcular_situacao_cadastral = AsyncMock(return_value=SituacaoImovel.REGULAR)

    imovel = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        area_total_ha=Decimal("100"),
        nirf="1111111111111",
        car_numero="MT111111111111",
        motivo_alteracao_area=None,
        situacao=SituacaoImovel.PENDENTE,
        updated_at=None,
    )

    atualizado, alertas = await service.atualizar_imovel(
        imovel,
        {
            "nirf": "1234567890123",
            "area_total_ha": Decimal("110"),
            "motivo_alteracao_area": "Ajuste cadastral",
        },
        usuario_id=uuid.uuid4(),
    )

    assert atualizado.nirf == "1234567890123"
    assert atualizado.area_total_ha == Decimal("110")
    assert atualizado.motivo_alteracao_area == "Ajuste cadastral"
    assert atualizado.situacao == SituacaoImovel.REGULAR
    assert alertas == []
    service.validar_nirf_unico.assert_awaited_once()
    service.validar_area_consistente.assert_awaited_once()
