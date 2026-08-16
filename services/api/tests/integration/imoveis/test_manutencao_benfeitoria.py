from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from imoveis.models.imovel import Benfeitoria, ImovelRural
from imoveis.schemas.manutencao_benfeitoria import (
    OrdemServicoBenfeitoriaCreate,
    PlanoManutencaoBenfeitoriaCreate,
)
from imoveis.services.manutencao_benfeitoria_service import ManutencaoBenfeitoriaService


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


async def _criar_benfeitoria(session, tenant_id: uuid.UUID) -> uuid.UUID:
    imovel = ImovelRural(tenant_id=tenant_id, nome="Fazenda Teste Manutenção", municipio="Ribeirão Preto", uf="SP")
    session.add(imovel)
    await session.flush()
    # Benfeitoria.created_at tem default tz-aware sobre coluna DateTime sem
    # timezone (bug pré-existente no model, não relacionado a este workflow) —
    # setamos naive explicitamente para não bloquear o teste.
    benfeitoria = Benfeitoria(imovel_id=imovel.id, nome="Galpão Teste", tipo="GALPAO", created_at=datetime.now())
    session.add(benfeitoria)
    await session.commit()
    await session.refresh(benfeitoria)
    return benfeitoria.id


@pytest.mark.asyncio
async def test_criar_plano_manutencao(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    plano = await svc.criar_plano(PlanoManutencaoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, descricao="Pintura anual", frequencia_dias=365,
    ))

    assert plano.id is not None
    assert plano.descricao == "Pintura anual"


@pytest.mark.asyncio
async def test_abrir_os_gera_numero_sequencial_e_status_aberta(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    os_ = await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, tipo="CORRETIVA", descricao_problema="Telhado com goteira",
    ))

    assert os_.status == "ABERTA"
    assert os_.numero_os.startswith("OSB-")
    assert os_.data_conclusao is None


@pytest.mark.asyncio
async def test_concluir_os_grava_custo_e_data_conclusao(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    os_ = await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, tipo="CORRETIVA", descricao_problema="Cerca danificada",
    ))
    concluida = await svc.concluir_os(os_.id, custo_total=850.0)

    assert concluida.status == "CONCLUIDA"
    assert float(concluida.custo_total) == 850.0
    assert concluida.data_conclusao is not None


@pytest.mark.asyncio
async def test_nao_permite_concluir_os_ja_concluida(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    os_ = await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, tipo="CORRETIVA", descricao_problema="Poço com vazamento",
    ))
    await svc.concluir_os(os_.id, custo_total=100.0)

    with pytest.raises(BusinessRuleError):
        await svc.concluir_os(os_.id, custo_total=200.0)


@pytest.mark.asyncio
async def test_cancelar_os(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    os_ = await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, tipo="PREVENTIVA", descricao_problema="Revisão programada",
    ))
    cancelada = await svc.cancelar_os(os_.id)

    assert cancelada.status == "CANCELADA"


@pytest.mark.asyncio
async def test_listar_os_filtra_por_benfeitoria_e_status(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    benfeitoria_1 = await _criar_benfeitoria(session, tenant_id)
    benfeitoria_2 = await _criar_benfeitoria(session, tenant_id)

    svc = ManutencaoBenfeitoriaService(session, tenant_id)
    os_1 = await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_1, tipo="CORRETIVA", descricao_problema="A",
    ))
    await svc.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_2, tipo="CORRETIVA", descricao_problema="B",
    ))
    await svc.concluir_os(os_1.id, custo_total=10.0)

    abertas_b2 = await svc.listar_os(benfeitoria_id=benfeitoria_2, status="ABERTA")
    assert len(abertas_b2) == 1

    concluidas = await svc.listar_os(status="CONCLUIDA")
    assert any(o.id == os_1.id for o in concluidas)
    assert all(o.status == "CONCLUIDA" for o in concluidas)


@pytest.mark.asyncio
async def test_isolamento_tenant_manutencao_benfeitoria(session_a, session_b, tenant_id, outro_tenant_id):
    await _garantir_tenant(session_a, tenant_id)
    benfeitoria_id = await _criar_benfeitoria(session_a, tenant_id)

    svc_a = ManutencaoBenfeitoriaService(session_a, tenant_id)
    os_ = await svc_a.abrir_os(OrdemServicoBenfeitoriaCreate(
        benfeitoria_id=benfeitoria_id, tipo="CORRETIVA", descricao_problema="Isolamento teste",
    ))

    svc_b = ManutencaoBenfeitoriaService(session_b, outro_tenant_id)
    with pytest.raises(Exception):
        await svc_b._get_or_fail(os_.id)
