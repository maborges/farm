import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel
from core.cadastros.propriedade_imovel import router as router_module
from main import app


def _make_vinculo(tenant_id: uuid.UUID, propriedade_id: uuid.UUID, imovel_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO.value,
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        origem_documental="Contrato validado",
        observacoes="Vínculo operacional",
        area_vinculada=Decimal("120.0000"),
        percentual_vinculado=Decimal("20.00"),
        vinculo_principal=False,
        origem_referencia="Livro 01",
        status_documental="VALIDO",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
        propriedade=SimpleNamespace(id=propriedade_id, nome="Propriedade A", ativo=True),
        imovel_rural=SimpleNamespace(id=imovel_id, nome="Imóvel A", municipio="Sorriso", uf="MT"),
    )


@pytest.mark.asyncio
async def test_criar_vinculo_201():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo(tenant.id, uuid.uuid4(), uuid.uuid4())

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        service.criar = AsyncMock(return_value=vinculo)

        response = await router_module.criar(
            data=router_module.PropriedadeImovelCreate(
                propriedade_id=vinculo.propriedade_id,
                imovel_rural_id=vinculo.imovel_rural_id,
                tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
                ativo=True,
                data_inicio=date(2026, 1, 1),
                origem_documental="Contrato validado",
                observacoes="Vínculo operacional",
                area_vinculada=Decimal("120.0000"),
                percentual_vinculado=Decimal("20.00"),
                vinculo_principal=False,
                origem_referencia="Livro 01",
                status_documental="VALIDO",
            ),
            tenant_id=tenant.id,
            user=user,
            session=session,
        )

    assert response.tipo_vinculo == TipoVinculoPropriedadeImovel.ARRENDAMENTO.value
    service.criar.assert_awaited_once()
    assert service.criar.await_args.kwargs["usuario_id"] == user.id


@pytest.mark.asyncio
async def test_listar_vinculos_filtra_por_tenant_e_tipo():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo(tenant.id, uuid.uuid4(), uuid.uuid4())

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        service.listar = AsyncMock(return_value=[vinculo])

        response = await router_module.listar(
            tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
            ativo=True,
            tenant_id=tenant.id,
            session=session,
        )

    assert len(response) == 1
    service.listar.assert_awaited_once()
    kwargs = service.listar.await_args.args
    assert kwargs[2] == TipoVinculoPropriedadeImovel.ARRENDAMENTO


@pytest.mark.asyncio
async def test_obter_vinculo_200():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo(tenant.id, uuid.uuid4(), uuid.uuid4())

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        service.obter = AsyncMock(return_value=vinculo)

        response = await router_module.obter(vinculo_id=vinculo.id, tenant_id=tenant.id, session=session)

    assert response.id == vinculo.id
    service.obter.assert_awaited_once_with(vinculo.id)


@pytest.mark.asyncio
async def test_atualizar_vinculo_200():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo(tenant.id, uuid.uuid4(), uuid.uuid4())

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        service.atualizar = AsyncMock(return_value=vinculo)

        response = await router_module.atualizar(
            vinculo_id=vinculo.id,
            data=router_module.PropriedadeImovelUpdate(observacoes="Atualizado"),
            tenant_id=tenant.id,
            user=user,
            session=session,
        )

    assert response.observacoes == "Vínculo operacional"
    service.atualizar.assert_awaited_once()
    assert service.atualizar.await_args.args[0] == vinculo.id


@pytest.mark.asyncio
async def test_inativar_vinculo_204():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo(tenant.id, uuid.uuid4(), uuid.uuid4())

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        service.inativar = AsyncMock(return_value=None)

        response = await router_module.inativar(vinculo_id=vinculo.id, tenant_id=tenant.id, user=user, session=session)

    assert response is None
    service.inativar.assert_awaited_once_with(vinculo.id, usuario_id=user.id)


@pytest.mark.asyncio
async def test_cross_tenant_404():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()

    with patch("core.cadastros.propriedade_imovel.router.PropriedadeImovelService") as service_cls:
        service = service_cls.return_value
        from core.exceptions import EntityNotFoundError

        service.obter = AsyncMock(side_effect=EntityNotFoundError("Vínculo propriedade-imóvel não encontrado."))

        with pytest.raises(router_module.HTTPException) as exc_info:
            await router_module.obter(vinculo_id=uuid.uuid4(), tenant_id=tenant.id, session=session)

    assert exc_info.value.status_code == 404


def test_router_registrado_no_main_app():
    paths = {route.path for route in app.routes}
    assert "/api/v1/propriedade-imovel" in paths
