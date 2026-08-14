from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import alert_engine.generators.esg_certificacoes_generator as esg_module
from alert_engine.generators import (
    AlertGeneratorContext,
    AlertGeneratorRunner,
    ESGCertificacoesAlertGenerator,
    alert_generator_registry,
)
from alert_engine.scheduler import AlertSchedulerService
from certificacoes_esg.models import StatusNaoConformidade, StatusPlanoAcao

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.10 compatibility in the test environment.
    UTC = timezone.utc  # noqa: UP017


@asynccontextmanager
async def _fake_nested():
    """SAVEPOINT falso — session mockada não sabe fazer begin_nested() de verdade."""
    yield


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.begin_nested = lambda: _fake_nested()
    return session


def _generator(tenant_id: uuid.UUID) -> ESGCertificacoesAlertGenerator:
    return ESGCertificacoesAlertGenerator(_mock_session(), tenant_id)


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

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )

    result = await AlertGeneratorRunner().execute(generator, context)

    assert result.generator_name == "esg_certificacoes"
    assert result.metadata["rule_counters"] == {
        "certificacao_vencimento_proximo": 0,
        "certificacao_vencida": 0,
        "nao_conformidade_aberta": 0,
        "plano_acao_atrasado": 0,
    }


@pytest.mark.asyncio
async def test_certificacao_vencimento_proximo_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    certificacao = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="GLOBALG.A.P.",
        status="ATIVO",
        data_fim=date.today() + timedelta(days=12),
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[certificacao]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["certificacao_vencimento_proximo"] == 1
    assert store.calls[0]["source_type"] == "ESG_CERTIFICACAO_VENCIMENTO_PROXIMO"


@pytest.mark.asyncio
async def test_certificacao_vencida_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    certificacao = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="Orgânico",
        status="ATIVO",
        data_fim=date.today() - timedelta(days=4),
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[certificacao]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["certificacao_vencida"] == 1
    assert store.calls[0]["source_type"] == "ESG_CERTIFICACAO_VENCIDA"


@pytest.mark.asyncio
async def test_certificacao_fora_da_janela_nao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)

    async def list_certificacoes(
        arg_tenant_id: uuid.UUID,
        arg_unit_id: uuid.UUID | None,
        dias: int,
    ) -> list[SimpleNamespace]:
        assert arg_tenant_id == tenant_id
        assert arg_unit_id is None
        assert dias == 30
        return []

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(generator, "_listar_certificacoes_vencimento_proximo", list_certificacoes)
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 0


@pytest.mark.asyncio
async def test_nao_conformidade_aberta_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    nao_conformidade = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="NC documental",
        status=StatusNaoConformidade.ABERTA,
        detectada_em=datetime.now(UTC) - timedelta(days=3),
        prazo_correcao=None,
        severidade="MAIOR",
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[nao_conformidade]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["nao_conformidade_aberta"] == 1
    assert store.calls[0]["source_type"] == "ESG_NAO_CONFORMIDADE_ABERTA"


@pytest.mark.asyncio
async def test_nao_conformidade_concluida_nao_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 0


@pytest.mark.asyncio
async def test_plano_acao_atrasado_gera_alerta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    plano_acao = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="Correção ESG",
        status=StatusPlanoAcao.PENDENTE,
        prazo=datetime.now(UTC) - timedelta(days=8),
        concluido_em=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[plano_acao]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    result = await generator.run(AlertGeneratorContext(tenant_id=tenant_id))

    assert result.created == 1
    assert result.metadata["rule_counters"]["plano_acao_atrasado"] == 1
    assert store.calls[0]["source_type"] == "ESG_PLANO_ACAO_ATRASADO"


@pytest.mark.asyncio
async def test_execucao_repetida_preserva_idempotencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    generator = _generator(tenant_id)
    certificacao = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="Certificação única",
        status="ATIVO",
        data_fim=date.today() + timedelta(days=5),
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[certificacao]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(generator, "_persistir_alerta", store.persist)

    context = AlertGeneratorContext(tenant_id=tenant_id)
    first = await generator.run(context)
    second = await generator.run(context)

    assert first.created == 1
    assert second.created == 0
    assert second.updated == 1
    assert len(store.calls) == 2


@pytest.mark.asyncio
async def test_isolamento_tenant_e_unidade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)

    async def list_certificacoes(
        arg_tenant_id: uuid.UUID,
        arg_unit_id: uuid.UUID | None,
        dias: int,
    ) -> list[SimpleNamespace]:
        assert arg_tenant_id == tenant_id
        assert arg_unit_id == unit_id
        assert dias == 30
        return []

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(generator, "_listar_certificacoes_vencimento_proximo", list_certificacoes)
    monkeypatch.setattr(
        generator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        generator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )

    result = await generator.run(
        AlertGeneratorContext(tenant_id=tenant_id, unidade_produtiva_id=unit_id),
    )

    assert result.created == 0


@pytest.mark.asyncio
async def test_filtro_unidade_produtiva_aplica_joins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    generator = _generator(tenant_id)
    certificacao = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Certificação modelo",
        status_programa="ATIVO",
        data_fim=date.today() + timedelta(days=10),
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    execute_mock = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: [certificacao]),
        ),
    )
    monkeypatch.setattr(generator.session, "execute", execute_mock)

    rows = await generator._listar_certificacoes_vencimento_proximo(tenant_id, unit_id, 30)
    stmt = execute_mock.call_args.args[0]
    sql = str(stmt)

    assert rows[0].entidade_id == certificacao.id
    assert "cadastros_exploracoes_rurais" in sql
    assert "imoveis_rurais" in sql
    assert "propriedade_imovel" in sql


def test_registry_integration() -> None:
    assert (
        alert_generator_registry.get_generator("esg_certificacoes")
        is ESGCertificacoesAlertGenerator
    )
    assert ESGCertificacoesAlertGenerator in alert_generator_registry.find_scheduled_generators()


@pytest.mark.asyncio
async def test_scheduler_executes_esg_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    certificacao = SimpleNamespace(
        entidade_id=uuid.uuid4(),
        nome="Certificação scheduler",
        status="ATIVO",
        data_fim=date.today() + timedelta(days=7),
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
    )
    store = _store()

    monkeypatch.setattr(esg_module, "set_rls_context", AsyncMock(return_value=None))
    monkeypatch.setattr(
        ESGCertificacoesAlertGenerator,
        "_listar_certificacoes_vencimento_proximo",
        AsyncMock(return_value=[certificacao]),
    )
    monkeypatch.setattr(
        ESGCertificacoesAlertGenerator,
        "_listar_certificacoes_vencidas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        ESGCertificacoesAlertGenerator,
        "_listar_nao_conformidades_abertas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        ESGCertificacoesAlertGenerator,
        "_listar_planos_acao_atrasados",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(ESGCertificacoesAlertGenerator, "_persistir_alerta", store.persist)

    registry = alert_generator_registry.__class__()
    registry.register(ESGCertificacoesAlertGenerator)
    service = AlertSchedulerService(_mock_session(), registry=registry)

    result = await service.run_scheduled_alerts(tenant_id=tenant_id, domains=["SYSTEM"])

    assert result.generators_executed == 1
    assert result.alerts_created == 1
    assert result.errors == 0
