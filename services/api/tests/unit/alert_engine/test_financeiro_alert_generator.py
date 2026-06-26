# ruff: noqa: UP017
from __future__ import annotations

import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import alert_engine.generators.financeiro_generator as financeiro_module
from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRunner,
    FinanceiroAlertGenerator,
    alert_generator_registry,
)
from alert_engine.scheduler import run_scheduled_alerts


def _generator(tenant_id: uuid.UUID) -> FinanceiroAlertGenerator:
    return FinanceiroAlertGenerator(AsyncMock(), tenant_id)


def _store() -> SimpleNamespace:
    store = SimpleNamespace(seen=set(), calls=[])

    async def persist(*args: object, **kwargs: object) -> int:
        store.calls.append(kwargs)
        if kwargs["dedupe_key"] in store.seen:
            return 0
        store.seen.add(kwargs["dedupe_key"])
        return 1

    store.persist = persist
    return store


@pytest.mark.asyncio
async def test_generator_executes_via_canonical_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    context = AlertGeneratorContext(tenant_id=tenant_id, metadata={})

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencidos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_desvios_orcamento",
        AsyncMock(return_value=[]),
    )

    result = await AlertGeneratorRunner().execute(generator, context)

    assert result.generator_name == "financeiro"
    assert result.metadata["rule_counters"] == {
        "vencimentos_proximos": 0,
        "lancamentos_vencidos": 0,
        "fluxo_caixa_critico": 0,
        "orcamento_excedido": 0,
    }


@pytest.mark.asyncio
async def test_vencimento_proximo_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    titulo = SimpleNamespace(
        titulo_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        descricao="Conta de insumo",
        status="A_PAGAR",
        data_vencimento=date.today() + timedelta(days=3),
        valor=1250.0,
        tipo="DESPESA",
    )
    store = _store()

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[titulo]),
    )
    monkeypatch.setattr(generator, "_listar_vencidos", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 1
    assert result.metadata["rule_counters"]["vencimentos_proximos"] == 1
    assert store.calls[0]["source_type"] == "FINANCEIRO_VENCIMENTO_PROXIMO"


@pytest.mark.asyncio
async def test_lancamento_vencido_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    titulo = SimpleNamespace(
        titulo_id=uuid.uuid4(),
        unidade_produtiva_id=None,
        descricao="Conta de venda",
        status="A_RECEBER",
        data_vencimento=date.today() - timedelta(days=2),
        valor=820.0,
        tipo="RECEITA",
    )
    store = _store()

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencidos",
        AsyncMock(return_value=[titulo]),
    )
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["lancamentos_vencidos"] == 1
    assert store.calls[0]["source_type"] == "FINANCEIRO_VENCIDO"


@pytest.mark.asyncio
async def test_fluxo_caixa_critico_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    store = _store()

    class FakeRelatorioService:
        def __init__(self, session, tenant_id) -> None:
            self.session = session
            self.tenant_id = tenant_id

        async def fluxo_caixa(self, data_inicio, data_fim, unidade_produtiva_id):
            return SimpleNamespace(
                totais=SimpleNamespace(total_saldo_previsto=-1500.0),
                periodos=[],
            )

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(financeiro_module, "RelatorioService", FakeRelatorioService)
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_listar_vencidos", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["fluxo_caixa_critico"] == 1
    assert store.calls[0]["source_type"] == "FINANCEIRO_FLUXO_CAIXA_CRITICO"


@pytest.mark.asyncio
async def test_orcamento_excedido_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    safra_id = uuid.uuid4()
    store = _store()

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_listar_vencidos", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        financeiro_module.CenarioFinanceiroService,
        "analisar_desvio",
        AsyncMock(
            return_value={
                "cenario_escolhido": "Base",
                "resultado_real": 800.0,
                "resultado_planejado": 1000.0,
                "desvio": -200.0,
                "desvio_percentual": -20.0,
            }
        ),
    )
    monkeypatch.setattr(
        generator.session,
        "execute",
        AsyncMock(return_value=FakeResult([(safra_id,)])),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["orcamento_excedido"] == 1
    assert store.calls[0]["source_type"] == "FINANCEIRO_ORCAMENTO_EXCEDIDO"


@pytest.mark.asyncio
async def test_execucao_repetida_preserva_idempotencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    titulo = SimpleNamespace(
        titulo_id=uuid.uuid4(),
        unidade_produtiva_id=None,
        descricao="Conta duplicada",
        status="A_PAGAR",
        data_vencimento=date.today() + timedelta(days=2),
        valor=300.0,
        tipo="DESPESA",
    )
    store = _store()

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[titulo]),
    )
    monkeypatch.setattr(generator, "_listar_vencidos", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    context = AlertGeneratorContext(tenant_id=tenant_id)
    first = await generator.run(context)
    second = await generator.run(context)

    assert first.created == 1
    assert second.created == 0
    assert second.updated == 1
    assert len(store.calls) == 2


@pytest.mark.asyncio
async def test_filtro_tenant_id(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    titulo = SimpleNamespace(
        titulo_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        descricao="Conta tenant",
        status="A_PAGAR",
        data_vencimento=date.today() + timedelta(days=1),
        valor=100.0,
        tipo="DESPESA",
    )

    async def list_vencimentos(arg_tenant_id: uuid.UUID, arg_unit_id: uuid.UUID | None, days: int):
        assert arg_tenant_id == tenant_id
        assert arg_unit_id == unit_id
        assert days == 7
        return [titulo]

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_vencimentos_proximos", list_vencimentos)
    monkeypatch.setattr(generator, "_listar_vencidos", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_persistir_alerta", _store().persist)

    result = await generator.run(
        AlertGeneratorContext(tenant_id=tenant_id, unidade_produtiva_id=unit_id)
    )

    assert result.created == 1


@pytest.mark.asyncio
async def test_filtro_unidade_produtiva_id(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)

    async def list_vencidos(arg_tenant_id: uuid.UUID, arg_unit_id: uuid.UUID | None):
        assert arg_tenant_id == tenant_id
        assert arg_unit_id == unit_id
        return []

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_listar_vencidos", list_vencidos)
    monkeypatch.setattr(
        generator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_desvios_orcamento", AsyncMock(return_value=[]))

    result = await generator.run(
        AlertGeneratorContext(tenant_id=tenant_id, unidade_produtiva_id=unit_id)
    )

    assert result.created == 0


def test_registry_integration() -> None:
    assert alert_generator_registry.get_generator("financeiro") is FinanceiroAlertGenerator
    assert FinanceiroAlertGenerator in alert_generator_registry.find_scheduled_generators()


@pytest.mark.asyncio
async def test_scheduler_executes_financeiro_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    titulo = SimpleNamespace(
        titulo_id=uuid.uuid4(),
        unidade_produtiva_id=None,
        descricao="Conta scheduler",
        status="A_PAGAR",
        data_vencimento=date.today() + timedelta(days=1),
        valor=50.0,
        tipo="DESPESA",
    )
    store = _store()

    monkeypatch.setattr(
        financeiro_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        FinanceiroAlertGenerator,
        "_listar_vencimentos_proximos",
        AsyncMock(return_value=[titulo]),
    )
    monkeypatch.setattr(
        FinanceiroAlertGenerator,
        "_listar_vencidos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        FinanceiroAlertGenerator,
        "_avaliar_fluxo_caixa_critico",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        FinanceiroAlertGenerator,
        "_listar_desvios_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(FinanceiroAlertGenerator, "_persistir_alerta", store.persist)

    result = await run_scheduled_alerts(
        generator.session,
        tenant_id=tenant_id,
        domains=["FINANCE"],
    )

    assert result.generators_executed >= 1
    assert result.alerts_created >= 1
    assert result.errors == 0
