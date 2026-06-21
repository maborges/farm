import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from core.cadastros.propriedades import visao_router as territorial_router_module
from core.cadastros.propriedade_imovel.visao_schemas import (
    ImovelFundiarioResumo,
    PropriedadeVisaoResumo,
    VisaoFundiariaRead,
    VisaoTerritorialRead,
    VinculoTerritorialResumo,
)
from imoveis import visao_router as fundiaria_router_module


def _build_client(router):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _make_vinculo():
    imovel_id = uuid.uuid4()
    propriedade_id = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tipo_vinculo="ARRENDAMENTO",
        ativo=True,
        data_inicio=date(2026, 1, 1),
        data_fim=None,
        area_vinculada=Decimal("200.0000"),
        percentual_vinculado=Decimal("20.00"),
        vinculo_principal=True,
        origem_documental="Contrato validado",
        origem_referencia="Livro 01",
        status_documental="VALIDO",
        propriedade=SimpleNamespace(id=propriedade_id, nome="Propriedade A", ativo=True),
        imovel_rural=SimpleNamespace(
            id=imovel_id,
            tenant_id=uuid.uuid4(),
            unidade_produtiva_id=uuid.uuid4(),
            nome="Fazenda Nova",
            municipio="Sorriso",
            uf="MT",
            area_total_ha=Decimal("1000.0000"),
            area_app_ha=None,
            area_rl_ha=None,
            nirf="123",
            car_numero="CAR-001",
            ccir_numero="CCIR-001",
            numero_matricula="12.345",
            cartorio=None,
            documentos=[],
            matriculas_resumo=[],
        ),
    )


def _make_imovel_resumo(imovel):
    return ImovelFundiarioResumo(
        id=imovel.id,
        tenant_id=imovel.tenant_id,
        unidade_produtiva_id=imovel.unidade_produtiva_id,
        nome=imovel.nome,
        municipio=imovel.municipio,
        uf=imovel.uf,
        area_total_ha=imovel.area_total_ha,
        area_app_ha=imovel.area_app_ha,
        area_rl_ha=imovel.area_rl_ha,
        nirf=imovel.nirf,
        car_numero=imovel.car_numero,
        ccir_numero=imovel.ccir_numero,
        numero_matricula=imovel.numero_matricula,
        cartorio=None,
        documentos_resumo=[],
        matriculas_resumo=[],
    )


def test_endpoints_agregados_registrados_no_router():
    client = _build_client(territorial_router_module.router)
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/propriedades/{propriedade_id}/visao-territorial" in paths

    client = _build_client(fundiaria_router_module.router)
    paths = {route.path for route in client.app.routes}
    assert "/api/v1/imoveis-rurais/{imovel_id}/visao-fundiaria" in paths


@pytest.mark.asyncio
async def test_visao_territorial_endpoint_retorna_leitura_agregada():
    tenant = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo()
    imovel_resumo = _make_imovel_resumo(vinculo.imovel_rural)
    resposta = VisaoTerritorialRead(
        propriedade=PropriedadeVisaoResumo(
            id=vinculo.propriedade.id,
            nome="Propriedade A",
            ativo=True,
            cpf_cnpj="12345678901",
            inscricao_estadual="ISENTO",
        ),
        areas_operacionais=[],
        exploracoes_rurais=[],
        imoveis_rurais=[imovel_resumo],
        vinculos=[VinculoTerritorialResumo(
            id=vinculo.id,
            tenant_id=vinculo.tenant_id,
            tipo_vinculo=vinculo.tipo_vinculo,
            ativo=vinculo.ativo,
            data_inicio=vinculo.data_inicio,
            data_fim=vinculo.data_fim,
            area_vinculada=vinculo.area_vinculada,
            percentual_vinculado=vinculo.percentual_vinculado,
            vinculo_principal=vinculo.vinculo_principal,
            origem_documental=vinculo.origem_documental,
            origem_referencia=vinculo.origem_referencia,
            status_documental=vinculo.status_documental,
            propriedade=PropriedadeVisaoResumo(
                id=vinculo.propriedade.id,
                nome=vinculo.propriedade.nome,
                ativo=vinculo.propriedade.ativo,
            ),
            imovel_rural=imovel_resumo,
        )],
    )
    service = AsyncMock()

    with patch("core.cadastros.propriedades.visao_router.VisaoTerritorialService") as service_cls:
        service_cls.return_value = service
        service.obter_visao_territorial = AsyncMock(return_value=resposta)

        response = await territorial_router_module.visao_territorial(
            propriedade_id=vinculo.propriedade.id,
            tenant_id=tenant.id,
            session=session,
        )

    assert response.propriedade.nome == "Propriedade A"
    assert response.vinculos[0].tipo_vinculo == "ARRENDAMENTO"
    service.obter_visao_territorial.assert_awaited_once_with(vinculo.propriedade.id)


@pytest.mark.asyncio
async def test_visao_fundiaria_endpoint_retorna_leitura_agregada():
    tenant = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    vinculo = _make_vinculo()
    imovel = _make_imovel_resumo(vinculo.imovel_rural)
    service = AsyncMock()

    with patch("imoveis.visao_router.VisaoTerritorialService") as service_cls:
        service_cls.return_value = service
        service.obter_visao_fundiaria = AsyncMock(
            return_value=VisaoFundiariaRead(
                imovel_rural=ImovelFundiarioResumo(
                    id=imovel.id,
                    tenant_id=imovel.tenant_id,
                    unidade_produtiva_id=imovel.unidade_produtiva_id,
                    nome=imovel.nome,
                    municipio=imovel.municipio,
                    uf=imovel.uf,
                    area_total_ha=imovel.area_total_ha,
                    area_app_ha=imovel.area_app_ha,
                    area_rl_ha=imovel.area_rl_ha,
                    nirf=imovel.nirf,
                    car_numero=imovel.car_numero,
                    ccir_numero=imovel.ccir_numero,
                    numero_matricula=imovel.numero_matricula,
                    cartorio=None,
                    documentos_resumo=[],
                    matriculas_resumo=[],
                ),
                propriedades_vinculadas=[
                    PropriedadeVisaoResumo(
                        id=vinculo.propriedade.id,
                        nome=vinculo.propriedade.nome,
                        ativo=True,
                    )
                ],
                vinculos=[
                    VinculoTerritorialResumo(
                        id=vinculo.id,
                        tenant_id=vinculo.tenant_id,
                        tipo_vinculo=vinculo.tipo_vinculo,
                        ativo=vinculo.ativo,
                        data_inicio=vinculo.data_inicio,
                        data_fim=vinculo.data_fim,
                        area_vinculada=vinculo.area_vinculada,
                        percentual_vinculado=vinculo.percentual_vinculado,
                        vinculo_principal=vinculo.vinculo_principal,
                        origem_documental=vinculo.origem_documental,
                        origem_referencia=vinculo.origem_referencia,
                        status_documental=vinculo.status_documental,
                        propriedade=PropriedadeVisaoResumo(
                            id=vinculo.propriedade.id,
                            nome=vinculo.propriedade.nome,
                            ativo=True,
                        ),
                        imovel_rural=imovel,
                    )
                ],
            )
        )

        response = await fundiaria_router_module.visao_fundiaria(
            imovel_id=imovel.id,
            tenant_id=tenant.id,
            session=session,
        )

    assert response.imovel_rural.nome == "Fazenda Nova"
    assert response.propriedades_vinculadas[0].nome == "Propriedade A"
    service.obter_visao_fundiaria.assert_awaited_once_with(imovel.id)
