from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from core.exceptions import EntityNotFoundError
from imoveis.models.imovel import ImovelRural
from imoveis.schemas.irrigacao import SistemaIrrigacaoCreate, SistemaIrrigacaoUpdate
from imoveis.services.irrigacao_service import IrrigacaoService


async def _garantir_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_imovel(session, tenant_id: uuid.UUID) -> uuid.UUID:
    imovel = ImovelRural(tenant_id=tenant_id, nome="Fazenda Teste Irrigação", municipio="Ribeirão Preto", uf="SP")
    session.add(imovel)
    await session.commit()
    await session.refresh(imovel)
    return imovel.id


@pytest.mark.asyncio
async def test_criar_sistema_irrigacao(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    imovel_id = await _criar_imovel(session, tenant_id)

    svc = IrrigacaoService(session, tenant_id)
    sistema = await svc.create(SistemaIrrigacaoCreate(
        imovel_id=imovel_id, nome="Pivô 1", tipo="PIVO_CENTRAL", area_irrigada_ha=120.5,
    ))

    assert sistema.id is not None
    assert sistema.nome == "Pivô 1"
    assert sistema.status == "ATIVO"


@pytest.mark.asyncio
async def test_listar_por_imovel(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    imovel_1 = await _criar_imovel(session, tenant_id)
    imovel_2 = await _criar_imovel(session, tenant_id)

    svc = IrrigacaoService(session, tenant_id)
    await svc.create(SistemaIrrigacaoCreate(imovel_id=imovel_1, nome="Pivô A", tipo="PIVO_CENTRAL"))
    await svc.create(SistemaIrrigacaoCreate(imovel_id=imovel_2, nome="Gotejo B", tipo="GOTEJAMENTO"))

    apenas_imovel_1 = await svc.listar_por_imovel(imovel_1)
    assert len(apenas_imovel_1) == 1
    assert apenas_imovel_1[0].nome == "Pivô A"

    todos = await svc.listar_por_imovel()
    assert len(todos) >= 2


@pytest.mark.asyncio
async def test_atualizar_sistema_irrigacao(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    imovel_id = await _criar_imovel(session, tenant_id)

    svc = IrrigacaoService(session, tenant_id)
    sistema = await svc.create(SistemaIrrigacaoCreate(imovel_id=imovel_id, nome="Pivô 2", tipo="PIVO_CENTRAL"))

    atualizado = await svc.update(sistema.id, SistemaIrrigacaoUpdate(status="MANUTENCAO").model_dump(exclude_unset=True))
    assert atualizado.status == "MANUTENCAO"


@pytest.mark.asyncio
async def test_remover_sistema_irrigacao(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    imovel_id = await _criar_imovel(session, tenant_id)

    svc = IrrigacaoService(session, tenant_id)
    sistema = await svc.create(SistemaIrrigacaoCreate(imovel_id=imovel_id, nome="Pivô 3", tipo="PIVO_CENTRAL"))
    await svc.hard_delete(sistema.id)

    with pytest.raises(EntityNotFoundError):
        await svc.get_or_fail(sistema.id)


@pytest.mark.asyncio
async def test_isolamento_tenant_irrigacao(session_a, session_b, tenant_id, outro_tenant_id):
    await _garantir_tenant(session_a, tenant_id)
    imovel_id = await _criar_imovel(session_a, tenant_id)

    svc_a = IrrigacaoService(session_a, tenant_id)
    sistema = await svc_a.create(SistemaIrrigacaoCreate(imovel_id=imovel_id, nome="Pivô Isolamento", tipo="PIVO_CENTRAL"))

    svc_b = IrrigacaoService(session_b, outro_tenant_id)
    with pytest.raises(EntityNotFoundError):
        await svc_b.get_or_fail(sistema.id)
