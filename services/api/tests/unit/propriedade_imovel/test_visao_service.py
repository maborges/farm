import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.cadastros.propriedade_imovel.visao_service import VisaoTerritorialService
from core.exceptions import EntityNotFoundError


pytestmark = pytest.mark.asyncio


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def session():
    sess = AsyncMock()
    sess.execute = AsyncMock()
    return sess


@pytest.fixture
def service(session, tenant_id):
    return VisaoTerritorialService(session, tenant_id)


def _make_cartorio():
    return SimpleNamespace(id=uuid.uuid4(), nome="Cartório Central", comarca="Sorriso", uf="MT")


def _make_documento():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tipo="CAR",
        descricao="Cadastro Ambiental Rural",
        numero_documento="MT-123",
        status="VALIDO",
        versao=1,
        data_emissao=date(2026, 1, 1),
        data_vencimento=None,
        restrito=False,
        created_at=datetime.now(timezone.utc),
    )


def _make_matricula():
    return SimpleNamespace(
        id=uuid.uuid4(),
        numero_matricula="12.345",
        cartorio_nome=None,
        area_matricula_ha=Decimal("100.5000"),
        data_transmissao=date(2025, 6, 1),
        tipo_transmissao="compra",
        ativo=True,
        cartorio=_make_cartorio(),
    )


def _make_imovel(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        nome="Fazenda Nova",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("1000.0000"),
        area_app_ha=Decimal("50.0000"),
        area_rl_ha=Decimal("120.0000"),
        nirf="1234567890",
        car_numero="CAR-001",
        ccir_numero="CCIR-001",
        numero_matricula="12.345",
        sigef_codigo="SIGEF-001",
        cartorio=_make_cartorio(),
        documentos=[_make_documento()],
    )


def _make_vinculo(tenant_id: uuid.UUID, propriedade_id: uuid.UUID, imovel=None):
    imovel = imovel or _make_imovel(tenant_id)
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        tipo_vinculo="ARRENDAMENTO",
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        area_vinculada=Decimal("250.0000"),
        percentual_vinculado=Decimal("25.00"),
        vinculo_principal=True,
        origem_documental="Contrato validado",
        origem_referencia="Livro 01",
        status_documental="VALIDO",
        propriedade=SimpleNamespace(id=propriedade_id, nome="Propriedade A", ativo=True),
        imovel_rural=imovel,
    )


def _make_propriedade(tenant_id: uuid.UUID, vinculo=None):
    propriedade_id = uuid.uuid4()
    vinculo = vinculo or _make_vinculo(tenant_id, propriedade_id)
    exploracao = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        propriedade_id=propriedade_id,
        unidade_produtiva_id=vinculo.imovel_rural.unidade_produtiva_id,
        natureza="propria",
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        numero_contrato=None,
        valor_anual=Decimal("0"),
        percentual_producao=Decimal("0"),
        area_explorada_ha=Decimal("100.0000"),
        ativo=True,
        observacoes=None,
    )
    return SimpleNamespace(
        id=propriedade_id,
        tenant_id=tenant_id,
        nome="Propriedade A",
        ativo=True,
        cpf_cnpj="12345678901",
        inscricao_estadual="ISENTO",
        exploracoes=[exploracao],
        propriedade_imoveis=[vinculo],
    )


async def test_obter_visao_territorial_agrega_dados(service, tenant_id, session):
    imovel = _make_imovel(tenant_id)
    vinculo = _make_vinculo(tenant_id, uuid.uuid4(), imovel=imovel)
    propriedade = _make_propriedade(tenant_id, vinculo=vinculo)

    service._obter_propriedade = AsyncMock(return_value=propriedade)
    service._listar_areas_operacionais = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=imovel.unidade_produtiva_id,
                parent_id=None,
                tipo="PROPRIEDADE",
                nome="Núcleo",
                codigo="PROD-01",
                area_hectares=Decimal("1000.0000"),
                ativo=True,
            )
        ]
    )

    visao = await service.obter_visao_territorial(propriedade.id)

    assert visao.propriedade.nome == "Propriedade A"
    assert len(visao.areas_operacionais) == 1
    assert visao.areas_operacionais[0].nome == "Núcleo"
    assert len(visao.exploracoes_rurais) == 1
    assert visao.imoveis_rurais[0].nome == "Fazenda Nova"
    assert visao.vinculos[0].tipo_vinculo == "ARRENDAMENTO"
    service._obter_propriedade.assert_awaited_once_with(propriedade.id)


async def test_obter_visao_territorial_agrega_multiplos_vinculos(service, tenant_id):
    imovel_1 = _make_imovel(tenant_id)
    imovel_2 = _make_imovel(tenant_id)
    propriedade_id_1 = uuid.uuid4()
    propriedade_id_2 = uuid.uuid4()
    vinculo_1 = _make_vinculo(tenant_id, propriedade_id_1, imovel=imovel_1)
    vinculo_2 = _make_vinculo(tenant_id, propriedade_id_2, imovel=imovel_2)
    propriedade = _make_propriedade(tenant_id, vinculo=vinculo_1)
    propriedade.propriedade_imoveis = [vinculo_1, vinculo_2]

    service._obter_propriedade = AsyncMock(return_value=propriedade)
    service._listar_areas_operacionais = AsyncMock(return_value=[])

    visao = await service.obter_visao_territorial(propriedade.id)

    assert len(visao.imoveis_rurais) == 2
    assert {item.id for item in visao.imoveis_rurais} == {imovel_1.id, imovel_2.id}
    assert len(visao.vinculos) == 2


async def test_obter_visao_fundiaria_agrega_dados(service, tenant_id):
    imovel = _make_imovel(tenant_id)
    propriedade = _make_propriedade(tenant_id)
    vinculo = _make_vinculo(tenant_id, propriedade.id, imovel=imovel)
    imovel.propriedade_imoveis = [vinculo]

    service._obter_imovel = AsyncMock(return_value=imovel)
    service._listar_matriculas = AsyncMock(return_value=[_make_matricula()])

    visao = await service.obter_visao_fundiaria(imovel.id)

    assert visao.imovel_rural.nome == "Fazenda Nova"
    assert visao.imovel_rural.cartorio.nome == "Cartório Central"
    assert len(visao.imovel_rural.documentos_resumo) == 1
    assert len(visao.imovel_rural.matriculas_resumo) == 1
    assert visao.imovel_rural.sigef_codigo == "SIGEF-001"
    assert visao.propriedades_vinculadas[0].nome == "Propriedade A"
    assert visao.vinculos[0].origem_documental == "Contrato validado"
    service._obter_imovel.assert_awaited_once_with(imovel.id)


async def test_obter_visao_fundiaria_agrega_multiplas_propriedades(service, tenant_id):
    imovel = _make_imovel(tenant_id)
    propriedade_1 = _make_propriedade(tenant_id)
    propriedade_2 = _make_propriedade(tenant_id)
    vinculo_1 = _make_vinculo(tenant_id, propriedade_1.id, imovel=imovel)
    vinculo_2 = _make_vinculo(tenant_id, propriedade_2.id, imovel=imovel)
    imovel.propriedade_imoveis = [vinculo_1, vinculo_2]

    service._obter_imovel = AsyncMock(return_value=imovel)
    service._listar_matriculas = AsyncMock(return_value=[])

    visao = await service.obter_visao_fundiaria(imovel.id)

    assert len(visao.propriedades_vinculadas) == 2
    assert {item.id for item in visao.propriedades_vinculadas} == {propriedade_1.id, propriedade_2.id}
    assert len(visao.vinculos) == 2


async def test_obter_propriedade_aplica_tenant_filter(service, tenant_id, session):
    propriedade = _make_propriedade(tenant_id)
    result = MagicMock()
    result.scalar_one_or_none.return_value = propriedade
    session.execute.return_value = result

    await service._obter_propriedade(propriedade.id)

    stmt = session.execute.await_args.args[0]
    stmt_text = str(stmt)
    assert "tenant_id" in stmt_text
    assert "cadastros_propriedades" in stmt_text


async def test_obter_propriedade_nao_resolve_id_de_imovel(service, session):
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    session.execute.return_value = result

    with pytest.raises(EntityNotFoundError):
        await service._obter_propriedade(uuid.uuid4())


async def test_obter_imovel_aplica_tenant_filter(service, tenant_id, session):
    imovel = _make_imovel(tenant_id)
    result = MagicMock()
    result.scalar_one_or_none.return_value = imovel
    session.execute.return_value = result

    await service._obter_imovel(imovel.id)

    stmt = session.execute.await_args.args[0]
    stmt_text = str(stmt)
    assert "tenant_id" in stmt_text
    assert "imoveis_rurais" in stmt_text


async def test_obter_propriedade_nao_encontrada_gera_erro(service, session):
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    session.execute.return_value = result

    with pytest.raises(EntityNotFoundError):
        await service._obter_propriedade(uuid.uuid4())
