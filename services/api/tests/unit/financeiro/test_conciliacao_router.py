from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.tenant import Tenant
from financeiro.models.conciliacao import ContaBancaria, LancamentoBancario
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.receita import Receita
from financeiro.routers import conciliacao as conciliacao_router


@pytest.fixture
async def fin_session():
    """Cria sessão SQLite em memória com tabelas financeiras mínimas."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [
        Tenant.__table__,
        PlanoConta.__table__,
        ContaBancaria.__table__,
        Despesa.__table__,
        Receita.__table__,
        LancamentoBancario.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_fluxo_completo_conciliacao_real_persistencia(fin_session):
    """Valida listagem pendente, conciliação manual, aprovação em lote, resumo e desfazimento."""
    tenant_a = Tenant(id=uuid.uuid4(), nome="Tenant A", ativo=True)
    tenant_b = Tenant(id=uuid.uuid4(), nome="Tenant B", ativo=True)
    fin_session.add_all([tenant_a, tenant_b])

    conta_a = ContaBancaria(
        id=uuid.uuid4(), tenant_id=tenant_a.id, nome="BB Principal", banco="001"
    )
    conta_b = ContaBancaria(
        id=uuid.uuid4(), tenant_id=tenant_b.id, nome="Sicoob B", banco="756"
    )
    fin_session.add_all([conta_a, conta_b])

    hoje = datetime.now(timezone.utc).date()
    up_id = uuid.uuid4()
    pc_id = uuid.uuid4()
    desp_a = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        unidade_produtiva_id=up_id,
        plano_conta_id=pc_id,
        descricao="Compra Adubo",
        valor_total=Decimal("1500.00"),
        data_emissao=hoje,
        data_vencimento=hoje,
        status="A_PAGAR",
        ativo=True,
    )
    rec_a = Receita(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        unidade_produtiva_id=up_id,
        plano_conta_id=pc_id,
        descricao="Venda Soja",
        valor_total=Decimal("3200.00"),
        data_emissao=hoje,
        data_vencimento=hoje,
        status="A_RECEBER",
        ativo=True,
    )
    desp_b = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        unidade_produtiva_id=uuid.uuid4(),
        plano_conta_id=uuid.uuid4(),
        descricao="Despesa Outro Tenant",
        valor_total=Decimal("500.00"),
        data_emissao=hoje,
        data_vencimento=hoje,
        status="A_PAGAR",
        ativo=True,
    )
    fin_session.add_all([desp_a, rec_a, desp_b])

    lanc_debito = LancamentoBancario(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        conta_id=conta_a.id,
        data=hoje,
        valor=-1500.00,
        descricao="TED Adubo",
        tipo="DEBIT",
        status_conciliacao="NAO_CONCILIADO",
    )
    lanc_credito = LancamentoBancario(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        conta_id=conta_a.id,
        data=hoje,
        valor=3200.00,
        descricao="PIX Soja",
        tipo="CREDIT",
        status_conciliacao="NAO_CONCILIADO",
    )
    lanc_outro_tenant = LancamentoBancario(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        conta_id=conta_b.id,
        data=hoje,
        valor=-500.00,
        descricao="Outro Tenant",
        tipo="DEBIT",
        status_conciliacao="NAO_CONCILIADO",
    )
    fin_session.add_all([lanc_debito, lanc_credito, lanc_outro_tenant])
    await fin_session.commit()

    # 1. Pendentes filtrados por tenant A
    pend_tx = await conciliacao_router.listar_transacoes_pendentes(
        tenant=tenant_a, session=fin_session
    )
    assert pend_tx["total"] == 2

    pend_lanc = await conciliacao_router.listar_lancamentos_pendentes(
        tenant=tenant_a, session=fin_session
    )
    assert pend_lanc["total"] == 2

    # 2. Bloqueio cross-tenant na conciliação manual
    with pytest.raises(HTTPException) as exc_info:
        await conciliacao_router.conciliar_manual(
            transacao_extrato_id=str(lanc_debito.id),
            lancamento_sistema_id=str(desp_b.id),
            tenant=tenant_a,
            session=fin_session,
        )
    assert exc_info.value.status_code == 404

    # 3. Conciliação manual persistida
    res_manual = await conciliacao_router.conciliar_manual(
        transacao_extrato_id=str(lanc_debito.id),
        lancamento_sistema_id=str(desp_a.id),
        tipo_lancamento="DESPESA",
        tenant=tenant_a,
        session=fin_session,
    )
    assert res_manual["sucesso"] is True
    assert res_manual["conciliacao"]["despesa_id"] == str(desp_a.id)

    # 4. Aprovação em lote persistida
    res_lote = await conciliacao_router.aprovar_conciliacao(
        sugestoes=[
            {
                "transacao_extrato_id": str(lanc_credito.id),
                "lancamento_sistema_id": str(rec_a.id),
                "tipo": "RECEITA",
            }
        ],
        tenant=tenant_a,
        session=fin_session,
    )
    assert res_lote["total_aprovadas"] == 1

    # 5. Resumo reflete dados reais (2 conciliadas, R$ 4700.00, 100%)
    resumo = await conciliacao_router.get_resumo_conciliacao(
        periodo="mes", tenant=tenant_a, session=fin_session
    )
    assert resumo["total_transacoes"] == 2
    assert resumo["total_conciliadas"] == 2
    assert resumo["total_pendentes"] == 0
    assert resumo["percentual_conciliado"] == 100.0
    assert resumo["valor_total_conciliado"] == 4700.0

    # 6. Desfazer conciliação reverte estado no banco
    res_undo = await conciliacao_router.desfazer_conciliacao(
        conciliacao_id=str(lanc_debito.id), tenant=tenant_a, session=fin_session
    )
    assert res_undo["sucesso"] is True

    pend_tx_apos = await conciliacao_router.listar_transacoes_pendentes(
        tenant=tenant_a, session=fin_session
    )
    assert pend_tx_apos["total"] == 1
