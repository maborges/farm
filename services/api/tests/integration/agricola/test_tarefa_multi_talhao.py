from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError
from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.schemas import TarefaCreate
from agricola.tarefas.service import TarefaService
from tests.test_operational_workflow_governance_step03 import (
    _criar_area,
    _criar_safra,
    _criar_unidade_produtiva,
    _garantir_tenant,
)


def _dados_base(**overrides) -> dict:
    base = dict(
        origem="MANUAL",
        tipo="OUTRO",
        descricao="Aplicação de defensivo em várias áreas",
    )
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_criar_multi_talhao_gera_uma_tarefa_por_talhao_com_grupo_geracao_compartilhado(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_a = await _criar_area(session, tenant_id, unidade_id)
    talhao_b = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)

    svc = TarefaService(session, tenant_id)
    dados = TarefaCreate(talhoes_ids=[talhao_a, talhao_b], **_dados_base())
    tarefas = await svc.criar_multi_talhao(safra.id, dados)
    await session.commit()

    assert len(tarefas) == 2
    talhoes_gerados = {t.talhao_id for t in tarefas}
    assert talhoes_gerados == {talhao_a, talhao_b}

    grupos = {t.grupo_geracao_id for t in tarefas}
    assert len(grupos) == 1
    assert None not in grupos

    persistidas = (
        (await session.execute(select(SafraTarefa).where(SafraTarefa.grupo_geracao_id.in_(grupos))))
        .scalars()
        .all()
    )
    assert len(persistidas) == 2


@pytest.mark.asyncio
async def test_criar_simples_sem_talhao_falha(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)

    svc = TarefaService(session, tenant_id)
    dados = TarefaCreate(**_dados_base())

    with pytest.raises(BusinessRuleError):
        await svc.criar(safra.id, dados)


@pytest.mark.asyncio
async def test_criar_multi_talhao_sem_lista_falha(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    safra = await _criar_safra(session, tenant_id)

    svc = TarefaService(session, tenant_id)
    dados = TarefaCreate(**_dados_base())

    with pytest.raises(BusinessRuleError):
        await svc.criar_multi_talhao(safra.id, dados)


@pytest.mark.asyncio
async def test_criar_multi_talhao_com_talhao_id_e_talhoes_ids_falha(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    talhao_a = await _criar_area(session, tenant_id, unidade_id)
    safra = await _criar_safra(session, tenant_id)

    svc = TarefaService(session, tenant_id)
    dados = TarefaCreate(talhao_id=talhao_a, talhoes_ids=[talhao_a], **_dados_base())

    with pytest.raises(BusinessRuleError):
        await svc.criar_multi_talhao(safra.id, dados)
