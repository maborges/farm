"""
Testes de Integração para Mark-to-Market de Hedge V2.
EXECUTION-HEDGE-04A
"""
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from core.cadastros.commodities.models import Commodity, CotacaoCommodity
from financeiro.hedge.models import ContratoFuturo, HedgePositionSnapshot
from financeiro.hedge.snapshot_service import HedgeSnapshotService
from core.models.tenant_audit_log import TenantAuditLog



@pytest.fixture
async def tenant_mtm(session):
    from core.models.tenant import Tenant
    t = Tenant(nome="Tenant MTM Teste")
    session.add(t)
    await session.flush()
    return t

@pytest.fixture
async def tenant_isolado(session):
    from core.models.tenant import Tenant
    t = Tenant(nome="Tenant Isolado MTM")
    session.add(t)
    await session.flush()
    return t


@pytest.fixture
async def commodity_mtm(session, tenant_mtm):
    codigo = f"SOJA_MTM_{uuid.uuid4().hex[:6].upper()}"
    c = Commodity(
        tenant_id=tenant_mtm.id,
        nome="Soja MTM",
        codigo=codigo,
        tipo="AGRICOLA",
        unidade_padrao="sc",
        possui_cotacao=True,
    )
    session.add(c)
    await session.flush()
    return c


@pytest.fixture
async def cotacoes(session, commodity_mtm):
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    
    c1 = CotacaoCommodity(commodity_id=commodity_mtm.id, data=ontem, preco=100.0, fonte="B3")
    c2 = CotacaoCommodity(commodity_id=commodity_mtm.id, data=hoje, preco=120.0, fonte="B3")
    
    session.add_all([c1, c2])
    await session.flush()
    return {"ontem": c1, "hoje": c2}


@pytest.fixture
async def contrato_venda(session, tenant_mtm, commodity_mtm):
    c = ContratoFuturo(
        tenant_id=tenant_mtm.id,
        commodity_id=commodity_mtm.id,
        commodity="SOJA",
        tipo_posicao="VENDA",
        quantidade=1000.0, # 1000 sc
        preco_contratado=110.0,
        status="ABERTO",
        unidade="sc"
    )
    session.add(c)
    await session.flush()
    return c


@pytest.fixture
async def contrato_compra(session, tenant_mtm, commodity_mtm):
    c = ContratoFuturo(
        tenant_id=tenant_mtm.id,
        commodity_id=commodity_mtm.id,
        commodity="SOJA",
        tipo_posicao="COMPRA",
        quantidade=1000.0,
        preco_contratado=110.0,
        status="ABERTO",
        unidade="sc"
    )
    session.add(c)
    await session.flush()
    return c


@pytest.mark.asyncio
async def test_gerar_snapshot_criado_uso_cotacao_dia(session, tenant_mtm, cotacoes, contrato_venda):
    """Verifica se o snapshot é gerado usando a cotação do dia (D-0)."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    # 1. snapshot criado
    # 3. uso de cotacao do dia
    stmt = select(HedgePositionSnapshot).where(
        HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id,
        HedgePositionSnapshot.data_referencia == hoje
    )
    snap = (await session.execute(stmt)).scalar_one_or_none()
    
    assert snap is not None
    assert float(snap.preco_mercado) == 120.0 # Cotação de hoje


@pytest.mark.asyncio
async def test_calculo_venda(session, tenant_mtm, cotacoes, contrato_venda):
    """
    Verifica a fórmula VENDA: (preco_contratado - preco_mercado) * quantidade
    (110.0 - 120.0) * 1000 = -10.0 * 1000 = -10000.0
    """
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id)
    snap = (await session.execute(stmt)).scalar_one()
    
    assert float(snap.mtm_valor) == -10000.0


@pytest.mark.asyncio
async def test_calculo_compra(session, tenant_mtm, cotacoes, contrato_compra):
    """
    Verifica a fórmula COMPRA: (preco_mercado - preco_contratado) * quantidade
    (120.0 - 110.0) * 1000 = 10.0 * 1000 = 10000.0
    """
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_compra.id)
    snap = (await session.execute(stmt)).scalar_one()
    
    assert float(snap.mtm_valor) == 10000.0


@pytest.mark.asyncio
async def test_fallback_d1(session, tenant_mtm, cotacoes, contrato_venda):
    """Verifica se usa cotação de ontem caso hoje não tenha (fallback D-1)."""
    svc = HedgeSnapshotService(session)
    # Exclui a cotação de hoje para forçar o fallback
    await session.delete(cotacoes["hoje"])
    await session.flush()
    
    hoje = date.today()
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id)
    snap = (await session.execute(stmt)).scalar_one()
    
    # 4. fallback D-1
    assert float(snap.preco_mercado) == 100.0 # Cotação de ontem


@pytest.mark.asyncio
async def test_ausencia_de_cotacao_nao_gera_snapshot(session, tenant_mtm, cotacoes, contrato_venda):
    """Se não há cotação em nenhuma data anterior, pula o snapshot e loga."""
    svc = HedgeSnapshotService(session)
    
    # Exclui ambas cotações
    await session.delete(cotacoes["hoje"])
    await session.delete(cotacoes["ontem"])
    await session.flush()
    
    hoje = date.today()
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id)
    snap = (await session.execute(stmt)).scalar_one_or_none()
    
    # 5. ausência de cotacao não gera snapshot
    assert snap is None

    # E deve gerar um log de auditoria MTM_SKIPPED
    stmt_audit = select(TenantAuditLog).where(
        TenantAuditLog.tenant_id == tenant_mtm.id,
        TenantAuditLog.action == "MTM_SKIPPED"
    )
    audit = (await session.execute(stmt_audit)).scalar_one_or_none()
    assert audit is not None


@pytest.mark.asyncio
async def test_upsert_atualizacao(session, tenant_mtm, cotacoes, contrato_venda):
    """Verifica se rodar novamente no mesmo dia atualiza o snapshot e cria auditoria UPDATED."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    # Roda a primeira vez (cria)
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    # Altera cotação e roda segunda vez (atualiza/upsert)
    cotacoes["hoje"].preco = 130.0
    await session.flush()
    
    # 2. snapshot atualizado (UPSERT)
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id)
    snaps = (await session.execute(stmt)).scalars().all()
    
    # 9. idempotência (só deve ter 1 registro para a data)
    assert len(snaps) == 1
    assert float(snaps[0].preco_mercado) == 130.0
    
    # 10. auditoria criada (CREATED e UPDATED)
    stmt_audit = select(TenantAuditLog.action).where(
        TenantAuditLog.tenant_id == tenant_mtm.id,
        TenantAuditLog.resource == "hedge_position_snapshots_v2"
    )
    audits = (await session.execute(stmt_audit)).scalars().all()
    assert "SNAPSHOT_CREATED" in audits
    assert "SNAPSHOT_UPDATED" in audits


@pytest.mark.asyncio
async def test_isolamento_tenant(session, tenant_mtm, tenant_isolado, cotacoes, contrato_venda):
    """Verifica se um tenant processado não enxerga/altera os dados de outro."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    # Roda para o tenant isolado
    count = await svc.processar_tenant(tenant_isolado.id, hoje)
    
    # 6. isolamento tenant
    # Tenant isolado não tem contrato, deve dar 0 snapshots
    assert count == 0
    
    # Verifica se gerou pro tenant principal? Não deveria.
    stmt = select(HedgePositionSnapshot).where(HedgePositionSnapshot.contrato_futuro_id == contrato_venda.id)
    snap = (await session.execute(stmt)).scalar_one_or_none()
    assert snap is None


@pytest.mark.asyncio
async def test_listar_snapshots_filtros_e_paginacao(session, tenant_mtm, cotacoes, contrato_venda, contrato_compra):
    """Verifica se o listar_snapshots aplica corretamente filtros de tenant e paginação."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    # 1. Filtro apenas por tenant
    snaps = await svc.listar_snapshots(tenant_id=tenant_mtm.id)
    assert len(snaps) == 2
    
    # 2. Filtro por contrato_futuro_id
    snaps_venda = await svc.listar_snapshots(tenant_id=tenant_mtm.id, contrato_futuro_id=contrato_venda.id)
    assert len(snaps_venda) == 1
    assert snaps_venda[0].contrato_futuro_id == contrato_venda.id
    
    # 3. Paginação limit/offset
    snaps_paginados = await svc.listar_snapshots(tenant_id=tenant_mtm.id, limit=1, offset=1)
    assert len(snaps_paginados) == 1
    
    # 4. Filtro por data
    snaps_data = await svc.listar_snapshots(tenant_id=tenant_mtm.id, data_inicio=hoje, data_fim=hoje)
    assert len(snaps_data) == 2
    
    snaps_vazio = await svc.listar_snapshots(tenant_id=tenant_mtm.id, data_inicio=hoje + timedelta(days=1))
    assert len(snaps_vazio) == 0


@pytest.mark.asyncio
async def test_reprocessar_snapshots_bloqueios(session, tenant_mtm):
    """Testa bloqueios da função de reprocessamento."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    # 1. Bloqueia data_fim < data_inicio
    with pytest.raises(ValueError, match="não pode ser menor que data_inicio"):
        await svc.reprocessar_snapshots(
            tenant_id=tenant_mtm.id,
            user_id=uuid.uuid4(),
            data_inicio=hoje,
            data_fim=hoje - timedelta(days=1),
            motivo="Reprocessamento de teste"
        )
        
    # 2. Bloqueia janela maior que 31 dias
    with pytest.raises(ValueError, match="intervalo máximo permitido"):
        await svc.reprocessar_snapshots(
            tenant_id=tenant_mtm.id,
            user_id=uuid.uuid4(),
            data_inicio=hoje - timedelta(days=32),
            data_fim=hoje,
            motivo="Reprocessamento longo"
        )
        
    # 3. Bloqueia motivo vazio ou muito curto
    with pytest.raises(ValueError, match="Motivo válido é obrigatório"):
        await svc.reprocessar_snapshots(
            tenant_id=tenant_mtm.id,
            user_id=uuid.uuid4(),
            data_inicio=hoje - timedelta(days=5),
            data_fim=hoje,
            motivo="curto"
        )


@pytest.mark.asyncio
async def test_reprocessar_snapshots_sucesso(session, tenant_mtm, cotacoes, contrato_venda):
    """Testa reprocessamento de snapshots com sucesso e registro de auditoria."""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    user_id = uuid.uuid4()
    
    # Cria primeiro os snapshots originais
    await svc.processar_tenant(tenant_mtm.id, hoje)
    
    # Executa o reprocessamento para hoje
    resultado = await svc.reprocessar_snapshots(
        tenant_id=tenant_mtm.id,
        user_id=user_id,
        data_inicio=hoje,
        data_fim=hoje,
        contrato_futuro_id=contrato_venda.id,
        motivo="Teste de reprocessamento"
    )
    
    # Como já existia de hoje, deve ter sido "atualizado"
    assert resultado["periodo_dias"] == 1
    assert resultado["processados"] == 1
    assert resultado["atualizados"] == 1
    assert resultado["criados"] == 0
    assert resultado["erros"] == 0

@pytest.mark.asyncio
async def test_processar_alertas_mtm(session, tenant_mtm, cotacoes, contrato_venda):
    """Testa a geração de alertas do MTM (Vencimento, Missing, PnL)"""
    svc = HedgeSnapshotService(session)
    hoje = date.today()
    
    # Forçar PnL Crítico
    cotacao_hj = cotacoes["hoje"]
    cotacao_hj.preco = 150.0  # Venda a 110, mercado 150 = Prejuízo grande
    session.add(cotacao_hj)
    await session.flush()
    
    await svc.gerar_snapshot_contrato(contrato_venda, hoje)
    
    alertas_count = await svc.processar_alertas_tenant(tenant_mtm.id, hoje)
    assert alertas_count >= 1
    
    from notificacoes.models import Notificacao
    stmt = select(Notificacao).where(Notificacao.tenant_id == tenant_mtm.id)
    notifs = (await session.execute(stmt)).scalars().all()
    
    tipos = [n.tipo for n in notifs]
    assert "HEDGE_CRITICAL_PNL" in tipos
