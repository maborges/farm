import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel
from imoveis.models.imovel import SituacaoImovel
from imoveis.routers import imovel as router_module


pytestmark = pytest.mark.asyncio


def _make_imovel() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        nome="Imóvel teste",
        nirf="1234567890123",
        car_numero="SP123456789012",
        ccir_numero="CCIR-01",
        area_total_ha=Decimal("10.0000"),
        area_aproveitavel_ha=None,
        area_app_ha=None,
        area_rl_ha=None,
        modulos_fiscais=None,
        municipio="Teste",
        uf="SP",
        latitude=None,
        longitude=None,
        tipo=router_module.TipoImovel.RURAL,
        situacao=SituacaoImovel.PENDENTE,
        geometria=None,
        observacao=None,
    )


async def test_list_imoveis_aceita_situacao_all() -> None:
    """`situacao=all` deve listar todos os imóveis sem erro de enum."""
    tenant = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    imovel = _make_imovel()

    with patch("imoveis.routers.imovel.ImovelService") as service_cls:
        service = service_cls.return_value
        service.get_imoveis_by_fazenda = AsyncMock(return_value=[imovel])

        resultado = await router_module.list_imoveis(
            unidade_produtiva_id=None,
            situacao="all",
            tenant=tenant,
            session=session,
        )

    assert resultado == [imovel]
    service.get_imoveis_by_fazenda.assert_awaited_once_with(None, tenant.id)


async def test_list_imoveis_aplica_filtro_de_situacao() -> None:
    """Filtro explícito deve continuar funcionando com o enum oficial."""
    tenant = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    imovel = _make_imovel()
    imovel.situacao = SituacaoImovel.REGULAR

    with patch("imoveis.routers.imovel.ImovelService") as service_cls:
        service = service_cls.return_value
        service.get_imoveis_by_fazenda = AsyncMock(return_value=[imovel])

        resultado = await router_module.list_imoveis(
            unidade_produtiva_id=None,
            situacao="regular",
            tenant=tenant,
            session=session,
        )

    assert resultado == [imovel]
    service.get_imoveis_by_fazenda.assert_awaited_once_with(None, tenant.id)


async def test_create_imovel_repassa_propriedade_id_e_tipo_vinculo() -> None:
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    imovel = _make_imovel()

    payload = router_module.ImovelCreate(
        nome="Imóvel teste",
        unidade_produtiva_id=uuid.uuid4(),
        area_total_ha=Decimal("10"),
        municipio="Teste",
        uf="SP",
        propriedade_id=uuid.uuid4(),
        tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL,
    )

    with patch("imoveis.routers.imovel.ImovelService") as service_cls:
        service = service_cls.return_value
        service.criar_imovel = AsyncMock(return_value=(imovel, []))

        resultado = await router_module.create_imovel(
            data=payload,
            tenant=tenant,
            user=user,
            session=session,
        )

    assert resultado.id == imovel.id
    service.criar_imovel.assert_awaited_once()
    kwargs = service.criar_imovel.await_args.kwargs
    assert kwargs["propriedade_id"] == payload.propriedade_id
    assert kwargs["tipo_vinculo"] == payload.tipo_vinculo


async def test_update_imovel_repassa_propriedade_id_e_tipo_vinculo() -> None:
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    imovel = _make_imovel()

    payload = router_module.ImovelUpdate(
        propriedade_id=uuid.uuid4(),
        tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL,
    )

    with patch("imoveis.routers.imovel.ImovelService") as service_cls:
        service = service_cls.return_value
        service.get_imovel_by_id = AsyncMock(return_value=imovel)
        service.atualizar_imovel = AsyncMock(return_value=(imovel, []))

        resultado = await router_module.update_imovel(
            imovel_id=imovel.id,
            data=payload,
            tenant=tenant,
            user=user,
            session=session,
        )

    assert resultado.id == imovel.id
    service.atualizar_imovel.assert_awaited_once()
    args = service.atualizar_imovel.await_args.args
    assert args[1]["propriedade_id"] == payload.propriedade_id
    assert args[1]["tipo_vinculo"] == payload.tipo_vinculo
