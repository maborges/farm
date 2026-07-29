from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.climatico.models import RegistroClima
from agricola.caderno.models import CadernoCampoEntrada
from agricola.cultivos.models import Cultivo
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from core.cadastros.propriedades.models import AreaRural
from agricola.safras.models import Safra, SafraTalhao
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.receita import Receita
from recommendations import register_default_recommendation_providers
from recommendations.engine import RecommendationEngine
from recommendations.enums import RecommendationPriority
from recommendations.models import RecommendationResult
from recommendations.providers import (
    AgriculturaRecommendationProvider,
    ClimaRecommendationProvider,
    FinanceiroRecommendationProvider,
)
from recommendations.registry import RecommendationProviderRegistry
from recommendations.schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
pytestmark = pytest.mark.integration


async def _ensure_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tenants (
                id, nome, documento, ativo, storage_usado_mb, storage_limite_mb,
                idioma_padrao, created_at, updated_at
            )
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(tenant_id),
            "nome": f"Tenant {tenant_id.hex[:8]}",
            "documento": tenant_id.hex[:11],
        },
    )
    await session.commit()


async def _ensure_unidade_produtiva(session, tenant_id: uuid.UUID, *, nome: str = "Fazenda Teste") -> uuid.UUID:
    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :nome, true, now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id), "nome": nome},
    )
    await session.commit()
    return unidade_produtiva_id


async def _seed_safra(session, tenant_id: uuid.UUID, *, ano_safra: str = "2025/26", custo_previsto_ha: float | None = None) -> uuid.UUID:
    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra=ano_safra,
        status="PLANEJADA",
        observacoes="Safra de teste",
    )
    if custo_previsto_ha is not None:
        setattr(safra, "custo_previsto_ha", custo_previsto_ha)
    session.add(safra)
    await session.commit()
    return safra.id


async def _seed_safra_talhao(
    session,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    area_ha: float = 10.0,
) -> uuid.UUID:
    talhao_id = uuid.uuid4()
    area = AreaRural(
        id=talhao_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        parent_id=None,
        tipo="TALHAO",
        nome="Talhão Teste",
        area_hectares=area_ha,
        ativo=True,
    )
    session.add(area)
    await session.flush()
    session.add(
        SafraTalhao(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            area_id=talhao_id,
            area_ha=area_ha,
            principal=True,
        )
    )
    await session.commit()
    return talhao_id


async def _seed_clima(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    session.add(
        RegistroClima(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_registro=date.today(),
            precipitacao_mm=15.0,
            temp_max_c=39.0,
            temp_min_c=18.0,
            temp_media_c=28.0,
            umidade_rel_pct=30.0,
            evapotranspiracao_mm=5.0,
            vento_kmh=32.0,
            gdu_calculado=18.0,
            fonte="ESTACAO_LOCAL",
        )
    )
    await session.commit()


async def _seed_operacoes(session, tenant_id: uuid.UUID, safra_id: uuid.UUID, talhao_id: uuid.UUID) -> None:
    session.add(
        OperacaoAgricola(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultivo_id=None,
            production_unit_id=None,
            talhao_id=talhao_id,
            tipo="PULVERIZACAO",
            descricao="Pulverização teste",
            data_prevista=date.today() - timedelta(days=15),
            data_realizada=date.today() - timedelta(days=11),
            custo_total=1200.0,
            custo_por_ha=120.0,
            status="REALIZADA",
            fotos=[],
        )
    )
    session.add(
        CadernoCampoEntrada(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OPERACAO",
            tipo_evento="OPERACAO",
            descricao="Registro antigo",
            data_registro=date.today() - timedelta(days=10),
            usuario_id=ADMIN_USER_ID,
            origem_evento="MANUAL",
            origem_id=str(uuid.uuid4()),
            origem_tecnica="MANUAL",
            payload_operacional={},
            status_evento="CONSOLIDADO",
        )
    )
    session.add(
        ItemOrcamentoSafra(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultivo_id=None,
            production_unit_id=None,
            categoria="DEFENSIVO",
            descricao="Defensivo teste",
            quantidade=10.0,
            unidade="L",
            custo_unitario=100.0,
            custo_total=400.0,
        )
    )
    session.add(
        ItemOrcamentoSafra(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultivo_id=None,
            production_unit_id=None,
            categoria="SERVICO",
            descricao="Serviço teste",
            quantidade=20.0,
            unidade="h",
            custo_unitario=120.0,
            custo_total=500.0,
        )
    )
    await session.commit()


async def _seed_custo_oficial_safra(
    session,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    talhao_id: uuid.UUID,
    *,
    amount: float,
    allocation_tenant_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Seed the canonical economic chain used by the agricultural provider."""
    cultivo = Cultivo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultura="MILHO",
        status="ATIVO",
    )
    session.add(cultivo)
    await session.flush()
    production_unit = ProductionUnit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        cultivo_id=cultivo.id,
        area_id=talhao_id,
        area_ha=10.0,
        status="ATIVA",
    )
    session.add(production_unit)
    await session.flush()
    session.add(
        CostAllocation(
            id=uuid.uuid4(),
            tenant_id=allocation_tenant_id or tenant_id,
            production_unit_id=production_unit.id,
            source="MANUAL",
            source_id=uuid.uuid4(),
            cost_category="INSUMO",
            amount=amount,
            allocation_date=date.today(),
            allocation_method="DIRECT",
            allocation_basis=10.0,
        )
    )
    await session.commit()
    return production_unit.id


async def _seed_financeiro(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, safra_id: uuid.UUID) -> None:
    despesa_pc = PlanoConta(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="3.01.01",
        nome="Custos operacionais",
        tipo="DESPESA",
    )
    receita_pc = PlanoConta(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="4.01.01",
        nome="Receita agrícola",
        tipo="RECEITA",
    )
    session.add_all([despesa_pc, receita_pc])
    await session.flush()
    session.add_all(
        [
            Despesa(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                plano_conta_id=despesa_pc.id,
                descricao="Compra de insumo",
                valor_total=5000.0,
                data_emissao=date.today() - timedelta(days=10),
                data_vencimento=date.today() - timedelta(days=2),
                status="ATRASADO",
                fornecedor="Fornecedor X",
                ativo=True,
            ),
            Despesa(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                plano_conta_id=despesa_pc.id,
                descricao="Serviço pago",
                valor_total=4200.0,
                valor_pago=4200.0,
                data_emissao=date.today() - timedelta(days=6),
                data_vencimento=date.today() - timedelta(days=1),
                data_pagamento=date.today(),
                status="PAGO",
                fornecedor="Fornecedor Y",
                ativo=True,
            ),
            Despesa(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                plano_conta_id=despesa_pc.id,
                descricao="Serviço a pagar",
                valor_total=800.0,
                data_emissao=date.today(),
                data_vencimento=date.today() + timedelta(days=4),
                status="A_PAGAR",
                fornecedor="Fornecedor Z",
                ativo=True,
            ),
            Receita(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                plano_conta_id=receita_pc.id,
                descricao="Venda futura",
                valor_total=1500.0,
                data_emissao=date.today() - timedelta(days=3),
                data_vencimento=date.today() - timedelta(days=1),
                status="RECEBIDO",
                valor_recebido=1500.0,
                data_recebimento=date.today(),
                cliente="Cliente Z",
                ativo=True,
            ),
            LancamentoFinanceiro(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                safra_id=safra_id,
                descricao="Receita teste",
                valor=1500.0,
                data=date.today() - timedelta(days=1),
                tipo="RECEITA",
                categoria="OPERACOES",
            ),
            LancamentoFinanceiro(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                safra_id=safra_id,
                descricao="Custo teste",
                valor=3200.0,
                data=date.today() - timedelta(days=1),
                tipo="CUSTO",
                categoria="OPERACOES",
            ),
            ItemOrcamentoSafra(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                safra_id=safra_id,
                cultivo_id=None,
                production_unit_id=None,
                categoria="SERVICO",
                descricao="Budget teste",
                quantidade=1.0,
                unidade="un",
                custo_unitario=1000.0,
                custo_total=1000.0,
            ),
        ]
    )
    await session.commit()


def _context(tenant_id: uuid.UUID, *, domain: str, scope_id: str, unidade_produtiva_id: uuid.UUID | None = None) -> OperationalContext:
    return OperationalContext(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        domain=domain,
        scope_type="SAFRA",
        scope_id=scope_id,
        generated_at=datetime.now(timezone.utc),
        payload={"safra_id": scope_id},
    )


@pytest.mark.asyncio
async def test_clima_provider_generates_candidates_without_alert_engine(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    await _seed_clima(session, tenant_id, unidade_produtiva_id)
    provider = ClimaRecommendationProvider(session)

    candidates = await provider.evaluate(
        OperationalContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain="AGRICULTURE",
            scope_type="SAFRA",
            scope_id="safra-1",
            generated_at=datetime.now(timezone.utc),
        ),
        [],
    )

    assert candidates
    assert all(isinstance(item, RecommendationCandidate) for item in candidates)
    assert all(not isinstance(item, RecommendationResult) for item in candidates)
    assert any(item.rule_code == "CLIMA_JANELA_PULVERIZACAO_DESFAVORAVEL" for item in candidates)


@pytest.mark.asyncio
async def test_agricultura_provider_generates_candidates_from_context(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    safra_id = await _seed_safra(session, tenant_id)
    talhao_id = await _seed_safra_talhao(session, tenant_id, safra_id, unidade_produtiva_id)
    await _seed_operacoes(session, tenant_id, safra_id, talhao_id)
    await _seed_custo_oficial_safra(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        amount=1200.0,
    )
    provider = AgriculturaRecommendationProvider(session)
    allocations_before = int(
        (await session.execute(
            select(func.count(CostAllocation.id)).where(CostAllocation.tenant_id == tenant_id)
        )).scalar_one()
    )

    candidates = await provider.evaluate(
        _context(tenant_id, domain="AGRICULTURE", scope_id=str(safra_id), unidade_produtiva_id=unidade_produtiva_id),
        [RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain="AGRICULTURE",
            source_type="SIGNAL",
            key="agri-signal",
            occurred_at=datetime.now(timezone.utc),
        )],
    )

    assert candidates
    assert all(isinstance(item, RecommendationCandidate) for item in candidates)
    assert any(item.rule_code == "AGRI_SAFRA_SEM_MOVIMENTACAO_RECENTE" for item in candidates)
    assert any(item.rule_code == "AGRI_OPERACAO_ATRASADA" for item in candidates)
    custo_candidate = next(item for item in candidates if item.rule_code == "AGRI_CUSTO_ACIMA_PREVISTO")
    assert custo_candidate.priority == RecommendationPriority.URGENT
    assert custo_candidate.context["source"] == "ORCAMENTO_SAFRA"
    assert custo_candidate.context["custo_realizado_total"] == 1200.0
    assert custo_candidate.context["orcamento_previsto_total"] == 900.0
    assert custo_candidate.context["desvio_orcamento_pct"] > 10
    assert custo_candidate.dedupe_key == (
        f"agricultura:{tenant_id}:{unidade_produtiva_id}:{safra_id}:AGRI_CUSTO_ACIMA_PREVISTO"
    )
    allocations_after = int(
        (await session.execute(
            select(func.count(CostAllocation.id)).where(CostAllocation.tenant_id == tenant_id)
        )).scalar_one()
    )
    assert allocations_after == allocations_before


@pytest.mark.asyncio
async def test_agricultura_provider_does_not_generate_cost_rule_without_official_allocation(
    session,
    tenant_id: uuid.UUID,
) -> None:
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    safra_id = await _seed_safra(session, tenant_id)
    talhao_id = await _seed_safra_talhao(session, tenant_id, safra_id, unidade_produtiva_id)
    await _seed_operacoes(session, tenant_id, safra_id, talhao_id)

    candidates = await AgriculturaRecommendationProvider(session).evaluate(
        _context(
            tenant_id,
            domain="AGRICULTURE",
            scope_id=str(safra_id),
            unidade_produtiva_id=unidade_produtiva_id,
        ),
        [],
    )

    assert all(item.rule_code != "AGRI_CUSTO_ACIMA_PREVISTO" for item in candidates)


@pytest.mark.asyncio
async def test_agricultura_provider_ignores_cost_allocation_from_another_tenant(
    session,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
) -> None:
    await _ensure_tenant(session, outro_tenant_id)
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    safra_id = await _seed_safra(session, tenant_id)
    talhao_id = await _seed_safra_talhao(session, tenant_id, safra_id, unidade_produtiva_id)
    await _seed_operacoes(session, tenant_id, safra_id, talhao_id)
    await _seed_custo_oficial_safra(
        session,
        tenant_id,
        safra_id,
        talhao_id,
        amount=1200.0,
        allocation_tenant_id=outro_tenant_id,
    )

    candidates = await AgriculturaRecommendationProvider(session).evaluate(
        _context(
            tenant_id,
            domain="AGRICULTURE",
            scope_id=str(safra_id),
            unidade_produtiva_id=unidade_produtiva_id,
        ),
        [],
    )

    assert all(item.rule_code != "AGRI_CUSTO_ACIMA_PREVISTO" for item in candidates)


@pytest.mark.asyncio
async def test_financeiro_provider_generates_candidates_without_mutating_data(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    safra_id = await _seed_safra(session, tenant_id)
    await _seed_financeiro(session, tenant_id, unidade_produtiva_id, safra_id)
    provider = FinanceiroRecommendationProvider(session)

    before = {
        "despesas": int((await session.execute(select(func.count(Despesa.id)).where(Despesa.tenant_id == tenant_id))).scalar_one()),
        "receitas": int((await session.execute(select(func.count(Receita.id)).where(Receita.tenant_id == tenant_id))).scalar_one()),
        "lancamentos": int((await session.execute(select(func.count(LancamentoFinanceiro.id)).where(LancamentoFinanceiro.tenant_id == tenant_id))).scalar_one()),
    }

    candidates = await provider.evaluate(
        _context(tenant_id, domain="FINANCE", scope_id=str(safra_id), unidade_produtiva_id=unidade_produtiva_id),
        [],
    )

    after = {
        "despesas": int((await session.execute(select(func.count(Despesa.id)).where(Despesa.tenant_id == tenant_id))).scalar_one()),
        "receitas": int((await session.execute(select(func.count(Receita.id)).where(Receita.tenant_id == tenant_id))).scalar_one()),
        "lancamentos": int((await session.execute(select(func.count(LancamentoFinanceiro.id)).where(LancamentoFinanceiro.tenant_id == tenant_id))).scalar_one()),
    }

    assert candidates
    assert all(isinstance(item, RecommendationCandidate) for item in candidates)
    assert any(item.rule_code == "FIN_FLUXO_CAIXA_CRITICO" for item in candidates)
    assert any(item.rule_code == "FIN_CONTAS_VENCIDAS" for item in candidates)
    assert before == after


@pytest.mark.asyncio
async def test_engine_processes_real_providers_and_dedupes(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    unidade_produtiva_id = await _ensure_unidade_produtiva(session, tenant_id)
    safra_id = await _seed_safra(session, tenant_id)
    talhao_id = await _seed_safra_talhao(session, tenant_id, safra_id, unidade_produtiva_id)
    await _seed_clima(session, tenant_id, unidade_produtiva_id)
    await _seed_operacoes(session, tenant_id, safra_id, talhao_id)
    await _seed_financeiro(session, tenant_id, unidade_produtiva_id, safra_id)

    registry = RecommendationProviderRegistry()
    register_default_recommendation_providers(registry)
    engine = RecommendationEngine(session, tenant_id, registry=registry)
    context = _context(tenant_id, domain="AGRICULTURE", scope_id=str(safra_id), unidade_produtiva_id=unidade_produtiva_id)
    signals = [
        RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain="AGRICULTURE",
            source_type="SIGNAL",
            key="engine-signal",
            occurred_at=datetime.now(timezone.utc),
        )
    ]

    first = await engine.generate(context, signals)
    count_after_first = int((await session.execute(select(func.count(RecommendationResult.id)).where(RecommendationResult.tenant_id == tenant_id))).scalar_one())
    second = await engine.generate(context, signals)
    count_after_second = int((await session.execute(select(func.count(RecommendationResult.id)).where(RecommendationResult.tenant_id == tenant_id))).scalar_one())

    assert first.providers_executed >= 2
    assert first.recommendations_created >= 2
    assert second.recommendations_created == 0
    assert second.recommendations_updated >= first.recommendations_created
    assert count_after_first == count_after_second


def test_registry_resolves_default_providers_by_domain() -> None:
    registry = RecommendationProviderRegistry()
    register_default_recommendation_providers(registry)

    agriculture = registry.find_by_domain("AGRICULTURE")
    finance = registry.find_by_domain("FINANCE")
    field = registry.find_by_domain("FIELD")

    assert ClimaRecommendationProvider in agriculture
    assert AgriculturaRecommendationProvider in agriculture
    assert FinanceiroRecommendationProvider in finance
    assert ClimaRecommendationProvider in field
