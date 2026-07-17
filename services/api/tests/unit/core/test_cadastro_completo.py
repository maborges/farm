from __future__ import annotations

from types import SimpleNamespace
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from core.schemas.cadastro_completo_input import CadastroCompletoCreate, CadastroCompletoImovelInput, CadastroCompletoUpdate
from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
from core.services.cadastro_completo_service import CadastroCompletoService


@pytest.mark.asyncio
async def test_schema_adapta_payload_achatado_em_blocos_oficiais():
    """O contrato legado ainda pode entrar, mas sai separado em blocos oficiais."""
    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()
    vinculo_id = uuid.uuid4()

    dados = CadastroCompletoCreate(
        nome="Fazenda Aurora",
        tipo_propriedade="fazenda",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("120.5"),
        codigo_car="MT123456789012",
        nirf="1234567890123",
        ccir="CCIR-999",
        numero_matricula="12.345",
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_id,
        propriedade_imovel_id=vinculo_id,
    )

    assert dados.unidade_produtiva.nome == "Fazenda Aurora"
    assert dados.unidade_produtiva.municipio == "Sorriso"
    assert dados.unidade_produtiva.uf == "MT"
    assert dados.propriedade.id == propriedade_id
    assert dados.imovel_rural.id == imovel_id
    assert dados.imovel_rural.car_numero == "MT123456789012"
    assert dados.imovel_rural.ccir_numero == "CCIR-999"
    assert dados.imovel_rural.numero_matricula == "12.345"
    assert dados.propriedade_imovel.id == vinculo_id


@pytest.mark.asyncio
async def test_cadastro_completo_envia_apenas_campos_operacionais_para_up():
    """A UP não pode receber campos de coordenação ou fundiários."""
    session = SimpleNamespace()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service = CadastroCompletoService(session, tenant_id, user_id)

    captured: dict[str, dict] = {}

    async def fake_create_unidade_produtiva(dados):
        captured["up"] = dados.model_dump()
        return SimpleNamespace(
            id=uuid.uuid4(),
            nome=dados.nome,
            municipio=dados.municipio,
            uf=dados.uf,
            area_total_ha=dados.area_total_ha,
        )

    service.up_svc.create_unidade_produtiva = AsyncMock(side_effect=fake_create_unidade_produtiva)
    service.up_svc.get = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    service._resolver_propriedade = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    service._resolver_exploracao = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    service._resolver_imovel = AsyncMock(return_value=None)

    dados = CadastroCompletoCreate(
        nome="Fazenda Aurora",
        tipo_propriedade="fazenda",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("120.5"),
        codigo_car="MT123456789012",
        nirf="1234567890123",
        ccir="CCIR-999",
        numero_matricula="12.345",
    )

    await service.criar_cadastro_completo(dados)

    assert "up" in captured
    assert "propriedade_id" not in captured["up"]
    assert "imovel_rural_id" not in captured["up"]
    assert "propriedade_imovel_id" not in captured["up"]
    assert "codigo_car" not in captured["up"]
    assert "nirf" not in captured["up"]
    assert "ccir" not in captured["up"]


@pytest.mark.asyncio
async def test_detecao_de_dados_fundiarios_olha_so_o_bloco_de_imovel():
    """A presença de blocos territoriais sem imóvel não deve acionar fluxo fundiário."""
    dados_sem_imovel = CadastroCompletoUpdate(
        unidade_produtiva=None,
        propriedade=None,
        exploracao_rural=None,
        imovel_rural=None,
        propriedade_imovel=None,
    )
    dados_com_imovel = CadastroCompletoUpdate(
        unidade_produtiva=None,
        imovel_rural={"nirf": "1234567890123"},  # type: ignore[arg-type]
    )

    service = CadastroCompletoService(SimpleNamespace(), uuid.uuid4(), uuid.uuid4())

    assert service._tem_dados_fundiarios(dados_sem_imovel) is False
    assert service._tem_dados_fundiarios(dados_com_imovel) is True


@pytest.mark.asyncio
async def test_resolver_imovel_reaproveita_principal_existente_sem_id():
    """Sem imovel_rural.id, o service deve reutilizar o principal ativo já vinculado."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service = CadastroCompletoService(SimpleNamespace(), tenant_id, user_id)

    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()

    service.vinculo_svc.listar = AsyncMock(
        return_value=[SimpleNamespace(id=uuid.uuid4(), vinculo_principal=True, data_fim=None, imovel_rural_id=imovel_id)]
    )
    service.imovel_svc.get_imovel_by_id = AsyncMock(
        return_value=SimpleNamespace(id=imovel_id, tenant_id=tenant_id, nome="Imóvel oficial")
    )
    service.imovel_svc.criar_imovel = AsyncMock()
    service.imovel_svc.atualizar_imovel = AsyncMock(
        return_value=(SimpleNamespace(id=imovel_id, tenant_id=tenant_id, nome="Imóvel atualizado"), [])
    )

    unidade = SimpleNamespace(id=uuid.uuid4(), nome="UP", municipio="Sorriso", uf="MT", area_total_ha=Decimal("100"))
    propriedade = SimpleNamespace(id=propriedade_id)
    bloco = CadastroCompletoImovelInput(
        nome="Imóvel atualizado",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("120"),
        nirf="1234567890123",
        car_numero="MT123",
        ccir_numero="CCIR-1",
        numero_matricula="12.345",
    )

    imovel = await service._resolver_imovel(unidade, propriedade, bloco, None)

    assert imovel.id == imovel_id
    service.imovel_svc.get_imovel_by_id.assert_awaited_once_with(imovel_id, tenant_id)
    service.imovel_svc.criar_imovel.assert_not_awaited()
    service.imovel_svc.atualizar_imovel.assert_awaited_once()


@pytest.mark.asyncio
async def test_atualizacao_da_up_sincroniza_campos_compartilhados_no_imovel_principal():
    """Mudanças na UP devem refletir no imóvel principal quando o bloco fundiário não veio no payload."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service = CadastroCompletoService(SimpleNamespace(), tenant_id, user_id)

    unidade_id = uuid.uuid4()
    propriedade_id = uuid.uuid4()
    imovel_id = uuid.uuid4()

    service._atualizar_unidade_produtiva = AsyncMock(
        return_value=SimpleNamespace(
            id=unidade_id,
            nome="Fazenda Aurora Atualizada",
            municipio="Sorriso",
            uf="MT",
            area_total_ha=Decimal("150.25"),
            area_app_ha=Decimal("4.50"),
            area_rl_ha=Decimal("8.75"),
            coordenadas_sede="-11.1234,-55.5678",
        )
    )
    service._resolver_propriedade = AsyncMock(return_value=SimpleNamespace(id=propriedade_id))
    service._resolver_exploracao = AsyncMock(return_value=None)
    service._resolver_imovel = AsyncMock(
        return_value=SimpleNamespace(
            id=imovel_id,
            nome="Fazenda Aurora Antiga",
            municipio="Sinop",
            uf="MS",
            area_total_ha=Decimal("120.00"),
            area_app_ha=Decimal("2.00"),
            area_rl_ha=Decimal("6.00"),
            latitude=Decimal("-10.0000"),
            longitude=Decimal("-54.0000"),
        )
    )
    service._resolver_vinculo = AsyncMock(return_value=None)
    service._resolver_vinculo_por_id = AsyncMock()
    service.up_svc.get = AsyncMock(return_value=SimpleNamespace(id=unidade_id))
    service.imovel_svc.atualizar_imovel = AsyncMock(
        return_value=(
            SimpleNamespace(
                id=imovel_id,
                nome="Fazenda Aurora Atualizada",
                municipio="Sorriso",
                uf="MT",
                area_total_ha=Decimal("150.25"),
                area_app_ha=Decimal("4.50"),
                area_rl_ha=Decimal("8.75"),
                latitude=Decimal("-11.1234"),
                longitude=Decimal("-55.5678"),
            ),
            [],
        )
    )

    dados = CadastroCompletoUpdate(
        unidade_produtiva=UnidadeProdutivaUpdate(
            nome="Fazenda Aurora Atualizada",
            municipio="Sorriso",
            uf="MT",
        ),
        imovel_rural=None,
        propriedade=None,
        exploracao_rural=None,
        propriedade_imovel=None,
    )

    await service.atualizar_cadastro_completo(unidade_id, dados)

    service.imovel_svc.atualizar_imovel.assert_awaited_once_with(
        service._resolver_imovel.return_value,
        {
            "nome": "Fazenda Aurora Atualizada",
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_ha": Decimal("150.25"),
            "area_app_ha": Decimal("4.50"),
            "area_rl_ha": Decimal("8.75"),
            "latitude": Decimal("-11.1234"),
            "longitude": Decimal("-55.5678"),
            "motivo_alteracao_area": "Sincronizado a partir da atualização da Unidade Produtiva.",
        },
        user_id,
    )


@pytest.mark.asyncio
async def test_sincronizacao_nao_dispara_justificativa_quando_area_equivalente():
    """Valores numéricos equivalentes não podem gerar alteração de área implícita."""
    service = CadastroCompletoService(SimpleNamespace(), uuid.uuid4(), uuid.uuid4())

    unidade = SimpleNamespace(
        nome="Fazenda Aurora",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=120,
        area_app_ha=Decimal("4.50"),
        area_rl_ha=Decimal("8.75"),
        coordenadas_sede=None,
    )
    imovel = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Fazenda Aurora",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("120.0000"),
        area_app_ha=Decimal("4.50"),
        area_rl_ha=Decimal("8.75"),
    )

    service.imovel_svc.atualizar_imovel = AsyncMock()

    resultado = await service._sincronizar_imovel_principal_com_unidade(unidade, imovel)

    assert resultado is imovel
    service.imovel_svc.atualizar_imovel.assert_not_awaited()
