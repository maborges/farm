import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel
from core.cadastros.propriedade_imovel.schemas import PropriedadeImovelCreate, PropriedadeImovelUpdate
from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from core.exceptions import BusinessRuleError, EntityNotFoundError


pytestmark = pytest.mark.asyncio


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def session():
    sess = AsyncMock()
    sess.execute = AsyncMock()
    sess.commit = AsyncMock()
    sess.refresh = AsyncMock()
    sess.add = MagicMock()
    return sess


@pytest.fixture
def service(session, tenant_id):
    return PropriedadeImovelService(session, tenant_id)


def _create_payload(**overrides):
    base = dict(
        propriedade_id=uuid.uuid4(),
        imovel_rural_id=uuid.uuid4(),
        tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        origem_documental="Contrato de arrendamento registrado em cartório.",
        observacoes="Vínculo operacional",
        area_vinculada=Decimal("100.0000"),
        percentual_vinculado=Decimal("25.00"),
        vinculo_principal=False,
        origem_referencia="Livro 01, folha 20",
        status_documental="VALIDO",
    )
    base.update(overrides)
    return PropriedadeImovelCreate(**base)


async def test_criar_vinculo_valido(service, session, tenant_id):
    mock_propriedade = SimpleNamespace(id=uuid.uuid4(), nome="Propriedade A", ativo=True)
    mock_imovel = SimpleNamespace(id=uuid.uuid4(), nome="Imóvel A", municipio="Sorriso", uf="MT")
    service._buscar_propriedade = AsyncMock(return_value=mock_propriedade)
    service._buscar_imovel = AsyncMock(return_value=mock_imovel)

    payload = _create_payload()
    resultado = await service.criar(payload, usuario_id=uuid.uuid4())

    assert resultado.tenant_id == tenant_id
    assert resultado.propriedade_id == payload.propriedade_id
    assert resultado.imovel_rural_id == payload.imovel_rural_id
    assert resultado.tipo_vinculo == TipoVinculoPropriedadeImovel.ARRENDAMENTO.value
    session.add.assert_called_once()
    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


async def test_origem_documental_ausente_gera_erro(service):
    payload = PropriedadeImovelCreate.model_construct(
        propriedade_id=uuid.uuid4(),
        imovel_rural_id=uuid.uuid4(),
        tipo_vinculo=TipoVinculoPropriedadeImovel.ARRENDAMENTO,
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        origem_documental="   ",
        observacoes=None,
        area_vinculada=None,
        percentual_vinculado=None,
        vinculo_principal=False,
        origem_referencia=None,
        status_documental=None,
    )

    service._buscar_propriedade = AsyncMock(return_value=SimpleNamespace(id=payload.propriedade_id, ativo=True))
    service._buscar_imovel = AsyncMock(return_value=SimpleNamespace(id=payload.imovel_rural_id))

    with pytest.raises(BusinessRuleError, match="origem_documental"):
        await service.criar(payload, usuario_id=uuid.uuid4())


async def test_propriedade_inexistente_gera_erro(service):
    payload = _create_payload()
    service._buscar_propriedade = AsyncMock(return_value=None)
    service._buscar_imovel = AsyncMock(return_value=SimpleNamespace(id=payload.imovel_rural_id))

    with pytest.raises(EntityNotFoundError, match="Propriedade não encontrada"):
        await service.criar(payload, usuario_id=uuid.uuid4())


async def test_imovel_inexistente_gera_erro(service):
    payload = _create_payload()
    service._buscar_propriedade = AsyncMock(return_value=SimpleNamespace(id=payload.propriedade_id, ativo=True))
    service._buscar_imovel = AsyncMock(return_value=None)

    with pytest.raises(EntityNotFoundError, match="Imóvel rural não encontrado"):
        await service.criar(payload, usuario_id=uuid.uuid4())


async def test_tenant_divergente_gera_erro(service):
    payload = _create_payload()
    service._buscar_propriedade = AsyncMock(return_value=SimpleNamespace(id=payload.propriedade_id, ativo=True))
    service._buscar_imovel = AsyncMock(return_value=None)

    with pytest.raises(EntityNotFoundError, match="tenant atual"):
        await service.criar(payload, usuario_id=uuid.uuid4())


async def test_percentual_invalido_gera_erro(service):
    with pytest.raises(BusinessRuleError, match="percentual_vinculado"):
        service._validar_campos_numericos({"percentual_vinculado": Decimal("101")})


async def test_area_negativa_gera_erro(service):
    with pytest.raises(BusinessRuleError, match="area_vinculada"):
        service._validar_campos_numericos({"area_vinculada": Decimal("-1")})


async def test_data_fim_menor_gera_erro(service):
    with pytest.raises(BusinessRuleError, match="data_fim"):
        service._validar_vigencia(date(2026, 1, 10), date(2026, 1, 1))


async def test_segundo_vinculo_principal_invalido(service, session):
    payload = _create_payload(vinculo_principal=True)
    service._buscar_propriedade = AsyncMock(return_value=SimpleNamespace(id=payload.propriedade_id, ativo=True))
    service._buscar_imovel = AsyncMock(return_value=SimpleNamespace(id=payload.imovel_rural_id))

    existente = SimpleNamespace(
        id=uuid.uuid4(),
        data_inicio=date(2026, 1, 1),
        data_fim=None,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existente]
    session.execute.return_value = mock_result

    with pytest.raises(BusinessRuleError, match="vínculo principal ativo"):
        await service.criar(payload, usuario_id=uuid.uuid4())


async def test_vinculo_secundario_valido(service):
    payload = _create_payload(vinculo_principal=False)
    service._buscar_propriedade = AsyncMock(return_value=SimpleNamespace(id=payload.propriedade_id, ativo=True))
    service._buscar_imovel = AsyncMock(return_value=SimpleNamespace(id=payload.imovel_rural_id))
    service._validar_principalidade = AsyncMock(return_value=None)
    service.session.add = MagicMock()
    service.session.commit = AsyncMock()
    service.session.refresh = AsyncMock()

    resultado = await service.criar(payload, usuario_id=uuid.uuid4())

    assert resultado.vinculo_principal is False
    service._validar_principalidade.assert_awaited_once()


async def test_garantir_vinculo_ativo_reaproveita_vinculo_existente(service, session):
    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    existente = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=service.tenant_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        ativo=True,
        data_fim=None,
        data_inicio=date(2026, 1, 1),
        tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existente
    session.execute = AsyncMock(return_value=mock_result)
    service._validar_referencias = AsyncMock()

    resultado = await service.garantir_vinculo_ativo(
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        usuario_id=uuid.uuid4(),
    )

    assert resultado is existente
    session.add.assert_not_called()
    service._validar_referencias.assert_awaited_once_with(propriedade_id, imovel_id)
