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


async def test_anotar_vinculos_marca_status_e_contagem():
    from imoveis.services.imovel_service import ImovelService

    service = ImovelService(AsyncMock())
    imovel = SimpleNamespace(
        propriedade_imoveis=[
            SimpleNamespace(ativo=True),
            SimpleNamespace(ativo=False),
        ]
    )

    anotado = service._anotar_vinculos(imovel)

    assert anotado.propriedades_vinculadas_count == 1
    assert anotado.vinculo_status == "VINCULADO"


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


async def test_criar_imovel_pode_vincular_propriedade():
    from imoveis.services.imovel_service import ImovelService

    session = AsyncMock()
    session.execute = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    session.add = MagicMock()
    session.flush = AsyncMock()

    service = ImovelService(session)
    service.validar_nirf_unico = AsyncMock(return_value=(True, "NIRF disponível"))
    service.car_validator.validar = MagicMock(return_value=(True, "CAR válido"))
    service.validar_area_consistente = AsyncMock(return_value=(True, "Área consistente", Decimal("100")))
    service._garantir_vinculo_propriedade_imovel = AsyncMock()

    imovel, alertas = await service.criar_imovel(
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        nome="Imóvel com vínculo",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("10"),
        propriedade_id=uuid.uuid4(),
        numero_matricula="12.345",
        created_by=uuid.uuid4(),
    )

    assert imovel.nome == "Imóvel com vínculo"
    assert alertas == []
    service._garantir_vinculo_propriedade_imovel.assert_awaited_once()


async def test_atualizar_imovel_pode_vincular_propriedade():
    from imoveis.services.imovel_service import ImovelService

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    service = ImovelService(session)
    service.validar_nirf_unico = AsyncMock(return_value=(True, "NIRF disponível"))
    service.validar_area_consistente = AsyncMock(return_value=(True, "Área consistente", Decimal("100")))
    service.calcular_situacao_cadastral = AsyncMock(return_value="pendente")
    service._garantir_vinculo_propriedade_imovel = AsyncMock()

    imovel = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        area_total_ha=Decimal("100"),
        nirf="1111111111111",
        car_numero="MT111111111111",
        situacao="pendente",
        updated_at=None,
    )

    atualizado, _ = await service.atualizar_imovel(
        imovel,
        {
            "propriedade_id": uuid.uuid4(),
            "tipo_vinculo": "PROPRIEDADE_PRINCIPAL",
        },
        usuario_id=uuid.uuid4(),
    )

    assert atualizado is imovel
    service._garantir_vinculo_propriedade_imovel.assert_awaited_once()
