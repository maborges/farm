import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.alocacao_service import (
    criar_equipamento_alocacao,
    get_equipamento_unidade_operacional,
)
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.equipamentos.service import EquipamentoService
from core.exceptions import BusinessRuleError, EntityNotFoundError


async def _criar_unidade(session: AsyncSession, tenant_id: uuid.UUID, nome: str = "UP Frota") -> uuid.UUID:
    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(unidade_id), "tenant_id": str(tenant_id), "nome": nome},
    )
    await session.commit()
    return unidade_id


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _criar_equipamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Trator {uuid.uuid4().hex[:6]}",
        tipo="TRATOR",
        combustivel="DIESEL",
        status="ATIVO",
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


@pytest.mark.asyncio
async def test_equipamento_sem_alocacao_usa_fallback_legado(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == unidade_produtiva_id
    assert contexto.source == "legado"
    assert contexto.alocacao_id is None


@pytest.mark.asyncio
async def test_equipamento_com_alocacao_ativa_prefere_alocacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    outra_up = await _criar_unidade(session, tenant_id, "UP Operacional")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)
    alocacao = await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=outra_up,
    )
    await session.commit()

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == outra_up
    assert contexto.source == "alocacao"
    assert contexto.alocacao_id == alocacao.id


@pytest.mark.asyncio
async def test_transferencia_encerra_alocacao_anterior_e_resolve_nova_up(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    nova_up = await _criar_unidade(session, tenant_id, "UP Destino")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)
    inicio = datetime.now(timezone.utc) - timedelta(days=2)
    alocacao_antiga = await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=inicio,
    )
    transferencia = datetime.now(timezone.utc)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=nova_up,
        data_inicio=transferencia,
        encerrar_alocacoes_ativas=True,
    )
    await session.commit()
    await session.refresh(alocacao_antiga)

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        momento=transferencia + timedelta(seconds=1),
    )

    assert alocacao_antiga.status == "ENCERRADA"
    assert alocacao_antiga.data_fim == transferencia
    assert contexto.unidade_produtiva_id == nova_up


@pytest.mark.asyncio
async def test_multiplas_alocacoes_ativas_prioriza_principal(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    up_secundaria = await _criar_unidade(session, tenant_id, "UP Secundaria")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_secundaria,
        principal=False,
    )
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=unidade_produtiva_id,
        principal=True,
    )
    await session.commit()

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == unidade_produtiva_id


@pytest.mark.asyncio
async def test_alocacao_rejeita_up_de_outro_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    await _garantir_tenant(session, outro_tenant_id)
    up_outro_tenant = await _criar_unidade(session, outro_tenant_id, "UP Outro Tenant")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)

    with pytest.raises(BusinessRuleError, match="Unidade produtiva"):
        await criar_equipamento_alocacao(
            session,
            tenant_id=tenant_id,
            equipamento_id=equipamento.id,
            unidade_produtiva_id=up_outro_tenant,
        )


@pytest.mark.asyncio
async def test_resolucao_rejeita_equipamento_de_outro_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
):
    await _garantir_tenant(session, outro_tenant_id)
    up_outro_tenant = await _criar_unidade(session, outro_tenant_id, "UP Outro Tenant")
    equipamento = await _criar_equipamento(session, outro_tenant_id, up_outro_tenant)

    with pytest.raises(EntityNotFoundError):
        await get_equipamento_unidade_operacional(
            session,
            tenant_id=tenant_id,
            equipamento_id=equipamento.id,
        )


@pytest.mark.asyncio
async def test_resolucao_rejeita_contexto_up_invalido(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    outra_up = await _criar_unidade(session, tenant_id, "UP Esperada")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)

    with pytest.raises(BusinessRuleError, match="unidade produtiva esperada"):
        await get_equipamento_unidade_operacional(
            session,
            tenant_id=tenant_id,
            equipamento_id=equipamento.id,
            expected_unidade_produtiva_id=outra_up,
        )


@pytest.mark.asyncio
async def test_listagem_por_up_inclui_equipamento_alocado_sem_quebrar_legado(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    up_operacional = await _criar_unidade(session, tenant_id, "UP Operacional")
    equipamento = await _criar_equipamento(session, tenant_id, unidade_produtiva_id)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_operacional,
    )
    await session.commit()

    service = EquipamentoService(session, tenant_id)
    equipamentos_legado = await service.listar(unidade_produtiva_id=unidade_produtiva_id)
    equipamentos_alocados = await service.listar(unidade_produtiva_id=up_operacional)

    assert equipamento.id in {item.id for item in equipamentos_legado}
    assert equipamento.id in {item.id for item in equipamentos_alocados}
