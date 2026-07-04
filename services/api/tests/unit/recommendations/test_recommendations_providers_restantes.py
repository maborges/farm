from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from recommendations import RecommendationEngine
from recommendations.providers import (
    CampoRecommendationProvider,
    EstoqueRecommendationProvider,
    ESGRecommendationProvider,
    FrotaRecommendationProvider,
    PecuariaRecommendationProvider,
    WizardRecommendationProvider,
    DEFAULT_RECOMMENDATION_PROVIDERS,
)
from recommendations.registry import RecommendationProviderRegistry
from recommendations.schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from recommendations.enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType


def _context(domain: RecommendationDomain, tenant_id, unidade_produtiva_id=None) -> OperationalContext:
    return OperationalContext(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        domain=domain,
        scope_type="TESTE",
        scope_id="scope-1",
        generated_at=datetime.now(timezone.utc),
    )


def _signal(tenant_id) -> RecommendationSignal:
    return RecommendationSignal(
        signal_id=uuid4(),
        tenant_id=tenant_id,
        domain=RecommendationDomain.OPERATIONS,
        source_type=RecommendationSourceType.SYSTEM,
        key="signal",
        occurred_at=datetime.now(timezone.utc),
    )


def _fake_candidate(tenant_id, domain: RecommendationDomain, provider_name: str, rule_code: str) -> RecommendationCandidate:
    return RecommendationCandidate(
        tenant_id=tenant_id,
        domain=domain,
        priority=RecommendationPriority.HIGH,
        source_type=RecommendationSourceType.SYSTEM,
        action_type=RecommendationActionType.OPEN_ROUTE,
        provider_name=provider_name,
        rule_code=rule_code,
        scope_type="TESTE",
        scope_id="scope-1",
        title="Teste",
        summary="Resumo",
        rationale="Racional",
        dedupe_key=f"{provider_name}:{rule_code}:dedupe",
        action_target="/dashboard/teste",
    )


@pytest.mark.asyncio
async def test_registry_includes_new_providers() -> None:
    registry = RecommendationProviderRegistry()
    registry.register_many(DEFAULT_RECOMMENDATION_PROVIDERS)

    assert registry.get_provider("pecuaria") is PecuariaRecommendationProvider
    assert registry.get_provider("estoque") is EstoqueRecommendationProvider
    assert registry.get_provider("frota") is FrotaRecommendationProvider
    assert registry.get_provider("esg") is ESGRecommendationProvider
    assert registry.get_provider("wizard") is WizardRecommendationProvider
    assert registry.get_provider("campo") is CampoRecommendationProvider

    assert {provider.provider_name for provider in registry.find_by_domain("LIVESTOCK")} >= {"pecuaria"}
    assert {provider.provider_name for provider in registry.find_by_domain("OPERATIONS")} >= {"estoque", "frota"}
    assert {provider.provider_name for provider in registry.find_by_domain("SYSTEM")} >= {"esg", "wizard"}
    assert {provider.provider_name for provider in registry.find_by_domain("FIELD")} >= {"campo"}


@pytest.mark.asyncio
async def test_pecuaria_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = PecuariaRecommendationProvider(session=SimpleNamespace())

    lote = SimpleNamespace(id=uuid4(), identificacao="Lote A", area_id=None)
    indicadores = SimpleNamespace(ultima_pesagem=date.today() - timedelta(days=60), quantidade_animais=35)
    sanitario = SimpleNamespace(custo_sanitario_total=1200.0, custo_sanitario_por_animal=65.0, ultima_vacinacao=date.today() - timedelta(days=90))

    monkeypatch.setattr(provider, "_listar_lotes", AsyncMock(return_value=[lote]))
    monkeypatch.setattr(provider, "_resumo_lote", AsyncMock(return_value=indicadores))
    monkeypatch.setattr(provider, "_resumo_sanitario", AsyncMock(return_value=sanitario))
    monkeypatch.setattr(provider, "_ultima_movimentacao", AsyncMock(return_value=date.today() - timedelta(days=90)))
    monkeypatch.setattr(provider, "_tarefas_vacinacao_atrasadas", AsyncMock(return_value=[]))

    result = await provider.evaluate(_context(RecommendationDomain.LIVESTOCK, tenant_id), [_signal(tenant_id)])

    assert result
    assert any(item.provider_name == "pecuaria" for item in result)
    assert any(item.rule_code == "PEC_LOTE_SEM_PESAGEM_RECENTE" for item in result)
    assert all(item.action_target for item in result)


@pytest.mark.asyncio
async def test_estoque_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = EstoqueRecommendationProvider(session=SimpleNamespace())

    saldo = SimpleNamespace(
        id=uuid4(),
        produto_id=uuid4(),
        produto_nome="Insumo X",
        deposito_id=uuid4(),
        deposito_nome="Depósito 1",
        quantidade_atual=5.0,
        quantidade_reservada=0.0,
        quantidade_disponivel=5.0,
        estoque_minimo=10.0,
        abaixo_minimo=True,
    )
    lote = SimpleNamespace(id=uuid4(), produto_id=saldo.produto_id, numero_lote="L1", data_validade=date.today() + timedelta(days=10), quantidade_atual=5.0)

    monkeypatch.setattr(provider, "_listar_saldos", AsyncMock(return_value=[saldo]))
    monkeypatch.setattr(provider, "_listar_lotes_vencendo", AsyncMock(return_value=[lote]))
    monkeypatch.setattr(provider, "_listar_requisicoes_pendentes", AsyncMock(return_value=[]))
    monkeypatch.setattr(provider, "_consumo_recente_por_produto", AsyncMock(return_value={saldo.produto_id: 20.0}))

    result = await provider.evaluate(_context(RecommendationDomain.OPERATIONS, tenant_id), [_signal(tenant_id)])

    assert any(item.provider_name == "estoque" for item in result)
    assert any(item.rule_code == "EST_SALDO_ABAIXO_MINIMO" for item in result)


@pytest.mark.asyncio
async def test_frota_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = FrotaRecommendationProvider(session=SimpleNamespace())

    dashboard_item = SimpleNamespace(
        equipamento_id=uuid4(),
        nome="Trator 1",
        manutencao_status="VENCIDA",
        custo_total=1500.0,
        os_abertas=1,
        dias_sem_abastecimento=45,
        jornada_aberta=False,
        risco_total=4,
        riscos=["MANUTENCAO_VENCIDA"],
    )
    dashboard = SimpleNamespace(equipamentos=[dashboard_item])
    monkeypatch.setattr(provider, "_obter_dashboard", AsyncMock(return_value=dashboard))

    result = await provider.evaluate(_context(RecommendationDomain.OPERATIONS, tenant_id), [_signal(tenant_id)])

    assert any(item.provider_name == "frota" for item in result)
    assert any(item.rule_code == "FROTA_MANUTENCAO_VENCIDA" for item in result)


@pytest.mark.asyncio
async def test_esg_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = ESGRecommendationProvider(session=SimpleNamespace())

    programa = SimpleNamespace(
        id=uuid4(),
        nome="Certificação X",
        data_fim=date.today() - timedelta(days=2),
        status_programa="ATIVO",
    )
    checklist = SimpleNamespace(
        id=uuid4(),
        nome="Checklist X",
        programa_certificacao_id=programa.id,
        status_checklist="RASCUNHO",
        percentual_conformidade=55.0,
    )
    nc = SimpleNamespace(
        id=uuid4(),
        programa_id=programa.id,
        titulo="NC X",
        status="ABERTA",
        severidade="CRITICA",
        prazo_correcao=datetime.now(timezone.utc) - timedelta(days=1),
    )
    plano = SimpleNamespace(
        id=uuid4(),
        programa_id=programa.id,
        titulo="Plano X",
        status="PENDENTE",
        prazo=datetime.now(timezone.utc) - timedelta(days=1),
    )

    monkeypatch.setattr(provider, "_listar_programas", AsyncMock(return_value=[programa]))
    monkeypatch.setattr(provider, "_listar_checklists", AsyncMock(return_value=[checklist]))
    monkeypatch.setattr(provider, "_listar_nao_conformidades", AsyncMock(return_value=[nc]))
    monkeypatch.setattr(provider, "_listar_planos_acao", AsyncMock(return_value=[plano]))

    result = await provider.evaluate(_context(RecommendationDomain.SYSTEM, tenant_id), [_signal(tenant_id)])

    assert any(item.provider_name == "esg" for item in result)
    assert any(item.rule_code == "ESG_CERTIFICACAO_VENCIDA" for item in result)


@pytest.mark.asyncio
async def test_wizard_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = WizardRecommendationProvider(session=SimpleNamespace())

    implantacao = SimpleNamespace(
        id=uuid4(),
        unidade_produtiva_id=None,
        status="BLOCKED",
        etapa_atual="DIAGNOSTICO",
        percentual_progresso=25,
        checklist_minimo_percentual=80,
        bloqueio_critico_aberto=True,
    )

    monkeypatch.setattr(provider, "_listar_implantacoes", AsyncMock(return_value=[implantacao]))
    monkeypatch.setattr(provider, "_contar_checklist_pendentes", AsyncMock(return_value=3))
    monkeypatch.setattr(provider, "_contar_pendencias_criticas", AsyncMock(return_value=1))

    result = await provider.evaluate(_context(RecommendationDomain.SYSTEM, tenant_id), [_signal(tenant_id)])

    assert any(item.provider_name == "wizard" for item in result)
    assert any(item.rule_code == "WIZARD_UNIDADE_PRODUTIVA_AUSENTE" for item in result)


@pytest.mark.asyncio
async def test_campo_provider_emits_candidate_without_persistence(monkeypatch) -> None:
    tenant_id = uuid4()
    provider = CampoRecommendationProvider(session=SimpleNamespace())

    device = SimpleNamespace(
        id=uuid4(),
        nome="Dispositivo 1",
        last_sync_at=datetime.now(timezone.utc) - timedelta(days=10),
        last_seen_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    tarefa = SimpleNamespace(
        id=uuid4(),
        titulo="Coleta 1",
        type="PESAGEM",
        module="pecuaria",
        status_execucao="PENDENTE",
        data_programada=date.today() - timedelta(days=1),
        dados={"sync_pecuaria": {"status": "ERROR", "erros": ["falha"]}},
    )
    tombstone = SimpleNamespace(id=uuid4(), entity_type="tarefas", deleted_at=datetime.now(timezone.utc) - timedelta(hours=1))

    monkeypatch.setattr(provider, "_listar_dispositivos", AsyncMock(return_value=[device]))
    monkeypatch.setattr(provider, "_listar_tarefas", AsyncMock(return_value=[tarefa]))
    monkeypatch.setattr(provider, "_listar_sync_falhas", AsyncMock(return_value=[tarefa]))
    monkeypatch.setattr(provider, "_listar_tombstones", AsyncMock(return_value=[tombstone]))

    result = await provider.evaluate(_context(RecommendationDomain.FIELD, tenant_id), [_signal(tenant_id)])

    assert any(item.provider_name == "campo" for item in result)
    assert any(item.rule_code == "CAMPO_SYNC_DESATUALIZADO" for item in result)
    assert any(item.rule_code == "CAMPO_TAREFA_ATRASADA" for item in result)


@pytest.mark.asyncio
async def test_engine_deduplicates_duplicate_candidates_from_new_provider(monkeypatch) -> None:
    tenant_id = uuid4()
    registry = RecommendationProviderRegistry()
    registry.register(PecuariaRecommendationProvider)
    session = SimpleNamespace()
    engine = RecommendationEngine(session, tenant_id, registry=registry)

    async def fake_evaluate(self, context, signals):
        candidate = _fake_candidate(tenant_id, RecommendationDomain.LIVESTOCK, "pecuaria", "PEC_DUPLICADA")
        return [candidate, candidate]

    from recommendations.providers.pecuaria_provider import PecuariaRecommendationProvider as ProviderClass

    monkeypatch.setattr(ProviderClass, "evaluate", fake_evaluate)
    persisted = SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=None,
        domain="LIVESTOCK",
        status="CREATED",
        priority="HIGH",
        source_type="SYSTEM",
        action_type="OPEN_ROUTE",
        provider_name="pecuaria",
        rule_code="PEC_DUPLICADA",
        scope_type="TESTE",
        scope_id="scope-1",
        title="Teste",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="pecuaria:PEC_DUPLICADA:dedupe",
        source_signal_ids=[],
        confidence=None,
        action_label=None,
        action_target="/dashboard/teste",
        context={},
        expires_at=None,
        viewed_at=None,
        accepted_at=None,
        dismissed_at=None,
        postponed_until=None,
        executed_at=None,
        expired_at=None,
        superseded_at=None,
        superseded_by_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    engine.lifecycle._find_active_recommendation = AsyncMock(side_effect=[None, persisted])
    engine.lifecycle.create_or_update_recommendation = AsyncMock(side_effect=[persisted, persisted])
    context = _context(RecommendationDomain.LIVESTOCK, tenant_id)
    result = await engine.generate(context, [])

    assert result.providers_executed == 1
    assert result.recommendations_created == 1
    assert result.recommendations_updated == 1
    assert len(result.items) == 2
