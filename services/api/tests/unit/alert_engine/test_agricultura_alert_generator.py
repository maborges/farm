# ruff: noqa: UP017
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import alert_engine.generators.agricultura_generator as agricultura_module
from alert_engine.generators import (
    AgriculturaAlertGenerator,
    AlertGeneratorContext,
    AlertGeneratorRunner,
    alert_generator_registry,
)
from alert_engine.generators.agricultura_generator import _OperacaoContext, _SafraContext, _TalhaoContext
from alert_engine.generators.clima_generator import ClimaAlertGenerator
from alert_engine.scheduler import run_scheduled_alerts

UTC = timezone.utc


def _generator(tenant_id: uuid.UUID) -> AgriculturaAlertGenerator:
    return AgriculturaAlertGenerator(AsyncMock(), tenant_id)


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
async def test_generator_executes_via_canonical_context(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    context = AlertGeneratorContext(tenant_id=tenant_id, metadata={})

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_safras_ativas", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_listar_operacoes_atrasadas", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_listar_talhoes_ativos", AsyncMock(return_value=[]))
    monkeypatch.setattr(generator, "_listar_safras_com_orcamento", AsyncMock(return_value=[]))

    result = await AlertGeneratorRunner().execute(generator, context)

    assert result.generator_name == "agricultura"
    assert result.metadata["rule_counters"] == {
        "safras_sem_movimentacao": 0,
        "operacoes_atrasadas": 0,
        "talhoes_sem_atualizacao": 0,
        "custos_acima_previstos": 0,
    }


@pytest.mark.asyncio
async def test_safra_sem_movimentacao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    safra = SimpleNamespace(
        safra_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        ano_safra="2025/2026",
        cultura="SOJA",
        status="PLANTIO",
        created_at=datetime.now(UTC) - timedelta(days=40),
    )
    store = _store()

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[safra]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_ultima_movimentacao_safra",
        AsyncMock(return_value=date.today() - timedelta(days=40)),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 1
    assert result.metadata["rule_counters"]["safras_sem_movimentacao"] == 1
    assert store.calls[0]["source_type"] == "AGRICULTURA_SAFRA_SEM_MOVIMENTACAO"


@pytest.mark.asyncio
async def test_safra_encerrada_nao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 0
    assert result.metadata["rule_counters"]["safras_sem_movimentacao"] == 0


@pytest.mark.asyncio
async def test_operacao_atrasada_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    operacao = SimpleNamespace(
        operacao_id=uuid.uuid4(),
        safra_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        talhao_id=uuid.uuid4(),
        tipo="PULVERIZACAO",
        status="PLANEJADA",
        data_prevista=date.today() - timedelta(days=1),
        descricao="Operacao agricola",
    )
    store = _store()

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[operacao]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 1
    assert result.metadata["rule_counters"]["operacoes_atrasadas"] == 1
    assert store.calls[0]["source_type"] == "AGRICULTURA_OPERACAO_ATRASADA"


@pytest.mark.asyncio
async def test_operacao_concluida_ou_cancelada_nao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 0
    assert result.metadata["rule_counters"]["operacoes_atrasadas"] == 0


@pytest.mark.asyncio
async def test_talhao_sem_atualizacao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    talhao = SimpleNamespace(
        safra_id=uuid.uuid4(),
        talhao_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        talhao_nome="Talhao 1",
        ano_safra="2025/2026",
        cultura="SOJA",
        safra_status="PLANTIO",
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    store = _store()

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[talhao]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_ultima_movimentacao_talhao",
        AsyncMock(return_value=date.today() - timedelta(days=60)),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 1
    assert result.metadata["rule_counters"]["talhoes_sem_atualizacao"] == 1
    assert store.calls[0]["source_type"] == "AGRICULTURA_TALHAO_SEM_ATUALIZACAO"


@pytest.mark.asyncio
async def test_custo_acima_previsto_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    safra_id = uuid.uuid4()
    store = _store()

    class FakeCustosService:
        def __init__(self, session, tenant_id) -> None:
            self.session = session
            self.tenant_id = tenant_id

        async def get_resumo_safra(self, safra_id: uuid.UUID) -> SimpleNamespace:
            return SimpleNamespace(
                orcamento_previsto_total=100.0,
                custo_total_realizado=200.0,
                desvio_orcamento_pct=100.0,
            )

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[safra_id]),
    )
    monkeypatch.setattr(agricultura_module, "CustosService", FakeCustosService)
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            metadata={"limite_desvio_percentual": 10.0},
        )
    )

    assert result.created == 1
    assert result.metadata["rule_counters"]["custos_acima_previstos"] == 1
    assert store.calls[0]["source_type"] == "AGRICULTURA_CUSTO_ACIMA_PREVISTO"


@pytest.mark.asyncio
async def test_execucao_repetida_preserva_idempotencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    safra = SimpleNamespace(
        safra_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        ano_safra="2025/2026",
        cultura="SOJA",
        status="PLANTIO",
        created_at=datetime.now(UTC) - timedelta(days=45),
    )
    store = _store()

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[safra]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_ultima_movimentacao_safra",
        AsyncMock(return_value=date.today() - timedelta(days=45)),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    context = AlertGeneratorContext(tenant_id=tenant_id, unidade_produtiva_id=unit_id)
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
    safra = SimpleNamespace(
        safra_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        ano_safra="2025/2026",
        cultura="SOJA",
        status="PLANTIO",
        created_at=datetime.now(UTC) - timedelta(days=40),
    )

    async def list_safras(arg_tenant_id: uuid.UUID, arg_unit_id: uuid.UUID | None):
        assert arg_tenant_id == tenant_id
        assert arg_unit_id == unit_id
        return [safra]

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generator, "_listar_safras_ativas", list_safras)
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_ultima_movimentacao_safra",
        AsyncMock(return_value=date.today() - timedelta(days=40)),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", _store().persist)

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 1


@pytest.mark.asyncio
async def test_filtro_unidade_produtiva_id(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)

    async def list_talhoes(arg_tenant_id: uuid.UUID, arg_unit_id: uuid.UUID | None):
        assert arg_tenant_id == tenant_id
        assert arg_unit_id == unit_id
        return []

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        generator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_listar_talhoes_ativos", list_talhoes)
    monkeypatch.setattr(
        generator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(
        AlertGeneratorContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unit_id,
        )
    )

    assert result.created == 0


def test_registry_integration() -> None:
    assert alert_generator_registry.get_generator("agricultura") is AgriculturaAlertGenerator
    assert AgriculturaAlertGenerator in alert_generator_registry.find_scheduled_generators()


@pytest.mark.asyncio
async def test_scheduler_executes_agricultura_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    safra = SimpleNamespace(
        safra_id=uuid.uuid4(),
        unidade_produtiva_id=unit_id,
        ano_safra="2025/2026",
        cultura="SOJA",
        status="PLANTIO",
        created_at=datetime.now(UTC) - timedelta(days=40),
    )
    store = _store()

    monkeypatch.setattr(
        agricultura_module,
        "set_rls_context",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_listar_safras_ativas",
        AsyncMock(return_value=[safra]),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_listar_operacoes_atrasadas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_listar_talhoes_ativos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_listar_safras_com_orcamento",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_ultima_movimentacao_safra",
        AsyncMock(return_value=date.today() - timedelta(days=40)),
    )
    monkeypatch.setattr(
        AgriculturaAlertGenerator,
        "_persistir_alerta",
        store.persist,
    )
    monkeypatch.setattr(
        ClimaAlertGenerator,
        "_listar_registros_climaticos",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(agricultura_module, "CustosService", agricultura_module.CustosService)

    result = await run_scheduled_alerts(
        generator.session,
        tenant_id=tenant_id,
        domains=["AGRICULTURE"],
    )

    assert result.generators_executed >= 1
    assert result.alerts_created >= 1
    assert result.errors == 0
