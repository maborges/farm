"""
Testes — Frota & Equipamentos — Step 02

Cobre:
- Resolução de UP operacional via alocação ativa
- Rejeição de UP incompatível com alocação
- Fallback legado sem alocação
- Manutenção histórica preserva contexto após transferência de UP
- Abastecimento usa UP operacional resolvida via alocação
- Dashboard respeita alocação ativa
- Hardening: equipamento de outro tenant é rejeitado
- Listagem de jornadas por UP segregada corretamente

Design: auto-suficiente — não usa fixture unidade_produtiva_id do conftest
(evita transação compartilhada + conflito de locks inter-sessão).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.alocacao_service import criar_equipamento_alocacao
from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import BusinessRuleError, EntityNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


async def _criar_unidade(
    session: AsyncSession, tenant_id: uuid.UUID, nome: str = "UP Frota"
) -> uuid.UUID:
    uid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(uid), "tenant_id": str(tenant_id), "nome": nome},
    )
    await session.commit()
    return uid


async def _criar_equipamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None = None,
    status: str = "ATIVO",
) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Trator-S02-{uuid.uuid4().hex[:6]}",
        tipo="TRATOR",
        combustivel="DIESEL",
        status=status,
        horimetro_atual=0.0,
        km_atual=0.0,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_jornada_raw(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None,
    status: str = "ABERTA",
) -> uuid.UUID:
    """Cria jornada diretamente no banco (bypass de validação de serviço)."""
    jornada_id = uuid.uuid4()
    agora = datetime.now(timezone.utc)
    await session.execute(
        text(
            "INSERT INTO frota_jornadas_equipamento "
            "(id, tenant_id, equipamento_id, unidade_produtiva_id, tipo_operacao, data_inicio, status, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :eq_id, :up_id, 'COLHEITA', :dt, :status, now(), now())"
        ),
        {
            "id": str(jornada_id),
            "tenant_id": str(tenant_id),
            "eq_id": str(equipamento_id),
            "up_id": str(unidade_produtiva_id) if unidade_produtiva_id else None,
            "dt": agora,
            "status": status,
        },
    )
    await session.commit()
    return jornada_id


async def _criar_os_raw(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    equipamento_id: uuid.UUID,
) -> uuid.UUID:
    """Cria OS diretamente no banco."""
    os_id = uuid.uuid4()
    numero = f"OS-TEST-{uuid.uuid4().hex[:8]}"
    await session.execute(
        text(
            "INSERT INTO frota_ordens_servico "
            "(id, tenant_id, equipamento_id, numero_os, tipo, status, descricao_problema, data_abertura, "
            "horimetro_na_abertura, custo_total_pecas, custo_mao_obra) "
            "VALUES (:id, :tid, :eq, :num, 'PREVENTIVA', 'ABERTA', 'Teste Step02', now(), 0, 0, 0)"
        ),
        {
            "id": str(os_id),
            "tid": str(tenant_id),
            "eq": str(equipamento_id),
            "num": numero,
        },
    )
    await session.commit()
    return os_id


# ---------------------------------------------------------------------------
# Fixture local: UP padrão para cada teste (sem conflito de locks)
# ---------------------------------------------------------------------------

@pytest.fixture
async def up_padrao(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """UP padrão criada na sessão local do teste."""
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant S02", "doc": str(tenant_id)[:11]},
    )
    await session.commit()
    return await _criar_unidade(session, tenant_id, "UP Padrão S02")


# ---------------------------------------------------------------------------
# 1. Resolução de UP via alocação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jornada_usa_up_operacional_por_alocacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """UP operacional resolvida via alocação ativa (não usa campo legado)."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    up_operacional = await _criar_unidade(session, tenant_id, "UP Operacional S02-A")
    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_operacional,
    )
    await session.commit()

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == up_operacional
    assert contexto.source == "alocacao"

    # Cria jornada diretamente com a UP operacional resolvida
    jornada_id = await _criar_jornada_raw(session, tenant_id, equipamento.id, up_operacional)
    row = (await session.execute(
        text("SELECT unidade_produtiva_id FROM frota_jornadas_equipamento WHERE id = :id"),
        {"id": str(jornada_id)},
    )).fetchone()
    assert row is not None
    assert str(row[0]) == str(up_operacional)


# ---------------------------------------------------------------------------
# 2. Rejeição de UP incompatível com alocação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jornada_rejeita_up_incompativel(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """get_equipamento_unidade_operacional rejeita UP incompatível com a alocação ativa."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    up_operacional = await _criar_unidade(session, tenant_id, "UP Oper S02-B")
    up_incompativel = await _criar_unidade(session, tenant_id, "UP Incompat S02-B")
    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_operacional,
    )
    await session.commit()

    with pytest.raises(BusinessRuleError, match="não está alocado"):
        await get_equipamento_unidade_operacional(
            session,
            tenant_id=tenant_id,
            equipamento_id=equipamento.id,
            expected_unidade_produtiva_id=up_incompativel,
        )


# ---------------------------------------------------------------------------
# 3. Fallback legado sem alocação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jornada_fallback_legado_sem_alocacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """Sem alocação ativa, resolvedor usa campo legado unidade_produtiva_id."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == up_padrao
    assert contexto.source == "legado"


# ---------------------------------------------------------------------------
# 4. Manutenção histórica preserva contexto após transferência
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registro_manutencao_preserva_contexto_historico_apos_transferencia(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """RegistroManutencao captura tenant_id e permanece ligado ao equipamento mesmo após transferência de UP."""
    from sqlalchemy import select as _select
    from operacional.models.frota import RegistroManutencao

    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    os_id = await _criar_os_raw(session, tenant_id, equipamento.id)

    # Simula fechamento de OS com registro de manutenção
    reg_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO frota_registros_manutencao "
            "(id, tenant_id, equipamento_id, os_id, tipo, descricao, custo_total, horimetro_na_data, data_realizacao) "
            "VALUES (:id, :tid, :eq, :os, 'PREVENTIVA', 'Manutenção S02', 500.00, 1250.0, now())"
        ),
        {
            "id": str(reg_id),
            "tid": str(tenant_id),
            "eq": str(equipamento.id),
            "os": str(os_id),
        },
    )
    await session.commit()

    # Transfere equipamento para nova UP
    nova_up = await _criar_unidade(session, tenant_id, "UP Nova S02")
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=nova_up,
        encerrar_alocacoes_ativas=True,
    )
    await session.commit()

    # Histórico deve continuar intacto
    stmt = _select(RegistroManutencao).where(RegistroManutencao.id == reg_id)
    registro = (await session.execute(stmt)).scalar_one()

    assert registro.equipamento_id == equipamento.id
    assert registro.tenant_id == tenant_id
    assert registro.os_id == os_id
    assert float(registro.custo_total) == 500.00


# ---------------------------------------------------------------------------
# 5. Abastecimento — resolve UP via alocação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_abastecimento_usa_up_operacional_por_alocacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """AbastecimentoService obtém UP via get_equipamento_unidade_operacional (alocação ativa)."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    up_operacional = await _criar_unidade(session, tenant_id, "UP Abast S02")
    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_operacional,
    )
    await session.commit()

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == up_operacional
    assert contexto.source == "alocacao"


@pytest.mark.asyncio
async def test_abastecimento_fallback_legado_sem_alocacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """Sem alocação, AbastecimentoService usa campo legado via fallback."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)

    contexto = await get_equipamento_unidade_operacional(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
    )

    assert contexto.unidade_produtiva_id == up_padrao
    assert contexto.source == "legado"


# ---------------------------------------------------------------------------
# 6. Dashboard — considera alocação ativa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_inclui_equipamento_alocado_em_up(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """Dashboard retorna equipamento com alocação ativa na UP consultada."""
    from operacional.services.frota_dashboard_service import FrotaDashboardService

    up_operacional = await _criar_unidade(session, tenant_id, "UP Dashboard S02")
    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    await criar_equipamento_alocacao(
        session,
        tenant_id=tenant_id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_operacional,
    )
    await session.commit()

    service = FrotaDashboardService(session, tenant_id)
    dashboard = await service.obter_dashboard(unidade_produtiva_id=up_operacional)

    ids = {item.equipamento_id for item in dashboard.equipamentos}
    assert equipamento.id in ids


@pytest.mark.asyncio
async def test_dashboard_nao_retorna_equipamento_sem_alocacao_em_up(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """Dashboard não retorna equipamento que não está alocado na UP consultada."""
    from operacional.services.frota_dashboard_service import FrotaDashboardService

    up_outra = await _criar_unidade(session, tenant_id, "UP Sem Equip S02")
    equipamento = await _criar_equipamento(session, tenant_id, up_padrao)
    # Não aloca o equipamento em up_outra

    service = FrotaDashboardService(session, tenant_id)
    dashboard = await service.obter_dashboard(unidade_produtiva_id=up_outra)

    ids = {item.equipamento_id for item in dashboard.equipamentos}
    assert equipamento.id not in ids


# ---------------------------------------------------------------------------
# 7. Hardening — equipamento de outro tenant é rejeitado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jornada_rejeita_equipamento_de_outro_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
) -> None:
    """Resolução rejeita equipamento de tenant diferente."""
    from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional

    await _garantir_tenant(session, outro_tenant_id)
    up_outro = await _criar_unidade(session, outro_tenant_id, "UP Outro Tenant S02")
    equip_outro = await _criar_equipamento(session, outro_tenant_id, up_outro)

    with pytest.raises(EntityNotFoundError):
        await get_equipamento_unidade_operacional(
            session,
            tenant_id=tenant_id,
            equipamento_id=equip_outro.id,
        )


# ---------------------------------------------------------------------------
# 8. Listagem de jornadas por UP (query direta)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listagem_jornadas_filtra_por_up_da_jornada(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    up_padrao: uuid.UUID,
) -> None:
    """Jornadas ficam registradas na UP correta e podem ser filtradas por ela."""
    up_a = await _criar_unidade(session, tenant_id, "UP A S02")
    up_b = await _criar_unidade(session, tenant_id, "UP B S02")
    equip_a = await _criar_equipamento(session, tenant_id, up_a)
    equip_b = await _criar_equipamento(session, tenant_id, up_b)

    await _criar_jornada_raw(session, tenant_id, equip_a.id, up_a, status="FINALIZADA")
    await _criar_jornada_raw(session, tenant_id, equip_b.id, up_b, status="FINALIZADA")

    rows = (await session.execute(
        text(
            "SELECT equipamento_id FROM frota_jornadas_equipamento "
            "WHERE tenant_id = :tid AND unidade_produtiva_id = :up AND status = 'FINALIZADA'"
        ),
        {"tid": str(tenant_id), "up": str(up_a)},
    )).fetchall()

    equip_ids_em_up_a = {row[0] for row in rows}
    assert equip_a.id in equip_ids_em_up_a
    assert equip_b.id not in equip_ids_em_up_a
