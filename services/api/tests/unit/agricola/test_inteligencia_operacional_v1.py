from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.diagnostico.schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo
from agricola.inteligencia_operacional.service import InteligenciaOperacionalAgricolaV1Service
from agricola.prioridades.schemas import PrioridadeAgricolaResponse
from agricola.recomendacoes.schemas import RecomendacaoAgricolaResponse
from core.exceptions import EntityNotFoundError
from core.services.analytics_request_cache import clear_analytics_request_cache
from agricola.dre.schemas import DREWarning


@pytest.fixture(autouse=True)
def _limpar_cache_analytics():
    clear_analytics_request_cache()
    yield
    clear_analytics_request_cache()


def _warning(codigo: str, origem: str, severidade: str = "INCONSISTENCIA_MODERADA") -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade=severidade,
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid4())],
        meta={"codigo": codigo},
    )


def _diagnostico_item(*, codigo: str, scope: str, entidade_id: UUID, label: str, severidade: str, sugestao: str | None) -> DiagnosticoAgricolaItem:
    return DiagnosticoAgricolaItem(
        scope=scope,  # type: ignore[arg-type]
        id=str(entidade_id),
        label=label,
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade=severidade,  # type: ignore[arg-type]
        mensagem=f"Mensagem oficial {codigo}",
        categoria="ECONOMICO" if "OPERACIONAL" in codigo or "CUSTO" in codigo or "RESULTADO" in codigo else "OPERACIONAL",
        valor_observado=-12.0 if "NEGATIVO" in codigo else 12.0,
        valor_referencia=0.0,
        sugestao=sugestao,
        warnings_relevantes=[codigo],
    )


def _recomendacao_item(*, codigo: str, scope: str, entidade_id: UUID, label: str, severidade: str, acao_sugerida: str) -> SimpleNamespace:
    return SimpleNamespace(
        scope=scope,
        id=str(entidade_id),
        label=label,
        tipo="REVISAO_RECONCILIACAO_ECONOMICA" if "RESULTADO" in codigo else "REVISAO_JORNADA",
        severidade=severidade,
        origem_diagnostica_codigo=codigo,
        origem_diagnostica_titulo=codigo.replace("_", " ").title(),
        contexto_operacional=f"Contexto operacional {codigo}",
        contexto_economico=f"Contexto econômico {codigo}",
        explicacao_objetiva=f"Explicação objetiva {codigo}",
        acao_sugerida=acao_sugerida,
        entidade_tipo="PRODUCTION_UNIT" if scope == "PRODUCTION_UNIT" else "JOURNEY",
        entidade_id=str(entidade_id),
        entidade_label=label,
        status="NOVA",
        warnings_relevantes=[codigo],
    )


def _prioridade_item(*, codigo: str, scope: str, entidade_id: UUID, label: str, severidade: str, score: int, acao_sugerida: str) -> SimpleNamespace:
    return SimpleNamespace(
        scope=scope,
        id=str(entidade_id),
        label=label,
        tipo=codigo,
        severidade=severidade,
        score_prioridade=score,
        origem="DIAGNOSTICO",
        origem_codigo=codigo,
        origem_titulo=codigo.replace("_", " ").title(),
        impacto_estimado=float(score),
        contexto_operacional=f"Contexto operacional {codigo}",
        contexto_economico=f"Contexto econômico {codigo}",
        acao_sugerida=acao_sugerida,
        entidade_tipo="PRODUCTION_UNIT" if scope == "PRODUCTION_UNIT" else "SAFRA",
        entidade_id=str(entidade_id),
        entidade_label=label,
        status="NOVA",
        warnings_relevantes=[codigo],
        recorrencia=2,
        fontes_relacionadas=[],
    )


def _diagnostico_response(*, diagnosticos: list[DiagnosticoAgricolaItem], warnings: list[DREWarning] | None = None) -> DiagnosticoAgricolaResponse:
    return DiagnosticoAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=uuid4(),
        diagnosticos=diagnosticos,
        ranking=diagnosticos,
        resumo=DiagnosticoAgricolaResumo(total=len(diagnosticos)),
        warnings=warnings or [],
        sujeito_reconciliacao=bool(warnings),
        observacao_reconciliacao="diagnóstico sujeito à reconciliação." if warnings else None,
    )


def _recomendacao_response(*, recomendacoes: list[SimpleNamespace], warnings: list[DREWarning] | None = None) -> RecomendacaoAgricolaResponse:
    return RecomendacaoAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=uuid4(),
        recomendacoes=recomendacoes,  # type: ignore[arg-type]
        warnings=warnings or [],
        sujeito_reconciliacao=bool(warnings),
        observacao_reconciliacao="recomendações sujeitas à reconciliação." if warnings else None,
    )


def _prioridade_response(*, prioridades: list[SimpleNamespace], warnings: list[DREWarning] | None = None) -> PrioridadeAgricolaResponse:
    return PrioridadeAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=uuid4(),
        prioridades=prioridades,  # type: ignore[arg-type]
        warnings=warnings or [],
        sujeito_reconciliacao=bool(warnings),
        observacao_reconciliacao="prioridades sujeitas à reconciliação." if warnings else None,
    )


@pytest.mark.asyncio
async def test_plano_operacional_deduplica_fontes_e_mantem_rastreabilidade():
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    jornada_id = uuid4()

    diag_neg = _diagnostico_item(
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        scope="PRODUCTION_UNIT",
        entidade_id=production_unit_id,
        label="Talhão A",
        severidade="RISCO_ECONOMICO",
        sugestao="Revisar custos alocados e reconciliação.",
    )
    diag_jornada = _diagnostico_item(
        codigo="JORNADA_BAIXA_PRODUTIVIDADE",
        scope="JOURNEY",
        entidade_id=jornada_id,
        label="Jornada 01",
        severidade="ATENCAO",
        sugestao="Rever desenho da jornada e disponibilidade.",
    )
    rec_neg = _recomendacao_item(
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        scope="PRODUCTION_UNIT",
        entidade_id=production_unit_id,
        label="Talhão A",
        severidade="RISCO_ECONOMICO",
        acao_sugerida="Auditar custos alocados e confirmar receita oficial.",
    )
    pri_neg = _prioridade_item(
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        scope="PRODUCTION_UNIT",
        entidade_id=production_unit_id,
        label="Talhão A",
        severidade="PRIORIDADE_CRITICA",
        score=100,
        acao_sugerida="Tratar imediatamente e validar reconciliação.",
    )

    diagnostico_response = _diagnostico_response(
        diagnosticos=[diag_neg, diag_jornada],
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "diagnostico_v1", "RISCO_ECONOMICO")],
    )
    recomendacao_response = _recomendacao_response(
        recomendacoes=[rec_neg],
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "recomendacoes_v1", "RISCO_ECONOMICO")],
    )
    prioridade_response = _prioridade_response(
        prioridades=[pri_neg],
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "prioridades_v1", "RISCO_ECONOMICO")],
    )

    with (
        patch("agricola.inteligencia_operacional.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar", new=AsyncMock(return_value=diagnostico_response)),
        patch("agricola.inteligencia_operacional.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar", new=AsyncMock(return_value=recomendacao_response)),
        patch("agricola.inteligencia_operacional.service.PrioridadesAgricolasV1Service.gerar", new=AsyncMock(return_value=prioridade_response)),
    ):
        service = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
        resposta = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert resposta.resumo.total == 2
    assert resposta.resumo.prioridade_critica == 1
    assert resposta.resumo.atencao == 1
    assert resposta.resumo.risco_economico == 0
    assert len(resposta.planos) == 2

    prioridade_critica = next(item for item in resposta.planos if item.severidade == "PRIORIDADE_CRITICA")
    assert prioridade_critica.origem_primaria.origem_analitica == "PRIORIDADE"
    assert {fonte.origem_analitica for fonte in prioridade_critica.fontes_analiticas} == {"PRIORIDADE", "DIAGNOSTICO", "RECOMENDACAO"}
    assert prioridade_critica.prazo_sugerido == "Imediato"
    assert prioridade_critica.acoes_sugeridas

    jornada = next(item for item in resposta.planos if item.titulo == diag_jornada.titulo)
    assert jornada.origem_primaria.origem_analitica == "DIAGNOSTICO"
    assert jornada.prazo_sugerido == "Até 15 dias"
    assert jornada.fontes_analiticas[0].origem_analitica == "DIAGNOSTICO"
    assert resposta.sujeito_reconciliacao is True


@pytest.mark.asyncio
async def test_plano_operacional_reaproveita_mesmo_contexto_na_mesma_request():
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()

    diagnostico_response = _diagnostico_response(
        diagnosticos=[
            _diagnostico_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=production_unit_id,
                label="Talhão A",
                severidade="RISCO_ECONOMICO",
                sugestao="Revisar custos alocados e reconciliação.",
            )
        ],
    )
    recomendacao_response = _recomendacao_response(recomendacoes=[])
    prioridade_response = _prioridade_response(
        prioridades=[
            _prioridade_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=production_unit_id,
                label="Talhão A",
                severidade="PRIORIDADE_CRITICA",
                score=100,
                acao_sugerida="Tratar imediatamente e validar reconciliação.",
            )
        ],
    )

    with (
        patch("agricola.inteligencia_operacional.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar", new=AsyncMock(return_value=diagnostico_response)) as diagnostico_mock,
        patch("agricola.inteligencia_operacional.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar", new=AsyncMock(return_value=recomendacao_response)) as recomendacoes_mock,
        patch("agricola.inteligencia_operacional.service.PrioridadesAgricolasV1Service.gerar", new=AsyncMock(return_value=prioridade_response)) as prioridades_mock,
    ):
        service = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
        resposta_1 = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )
        resposta_2 = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert resposta_1.model_dump() == resposta_2.model_dump()
    assert diagnostico_mock.await_count == 1
    assert recomendacoes_mock.await_count == 1
    assert prioridades_mock.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "altered_kwargs",
    [
        {"safra_id": uuid4()},
        {"unidade_produtiva_id": uuid4()},
        {"production_unit_id": uuid4()},
        {"data_inicio": date(2026, 2, 1)},
        {"data_fim": date(2026, 2, 28)},
    ],
)
async def test_plano_operacional_cache_isola_safra_pu_e_periodo(altered_kwargs):
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    base_safra_id = uuid4()
    base_unidade_produtiva_id = uuid4()
    base_production_unit_id = uuid4()
    base_args = {
        "safra_id": base_safra_id,
        "unidade_produtiva_id": base_unidade_produtiva_id,
        "production_unit_id": base_production_unit_id,
        "data_inicio": date(2026, 1, 1),
        "data_fim": date(2026, 1, 31),
    }

    diagnostico_response = _diagnostico_response(
        diagnosticos=[
            _diagnostico_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=base_production_unit_id,
                label="Talhão A",
                severidade="RISCO_ECONOMICO",
                sugestao="Revisar custos alocados e reconciliação.",
            )
        ],
    )
    recomendacao_response = _recomendacao_response(recomendacoes=[])
    prioridade_response = _prioridade_response(
        prioridades=[
            _prioridade_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=base_production_unit_id,
                label="Talhão A",
                severidade="PRIORIDADE_CRITICA",
                score=100,
                acao_sugerida="Tratar imediatamente e validar reconciliação.",
            )
        ],
    )

    with (
        patch("agricola.inteligencia_operacional.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar", new=AsyncMock(return_value=diagnostico_response)) as diagnostico_mock,
        patch("agricola.inteligencia_operacional.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar", new=AsyncMock(return_value=recomendacao_response)) as recomendacoes_mock,
        patch("agricola.inteligencia_operacional.service.PrioridadesAgricolasV1Service.gerar", new=AsyncMock(return_value=prioridade_response)) as prioridades_mock,
    ):
        service = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
        await service.gerar(**base_args)
        await service.gerar(**{**base_args, **altered_kwargs})

    assert diagnostico_mock.await_count == 2
    assert recomendacoes_mock.await_count == 2
    assert prioridades_mock.await_count == 2


@pytest.mark.asyncio
async def test_plano_operacional_cache_isola_tenant():
    session = AsyncMock(spec=AsyncSession)
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    tenant_a = uuid4()
    tenant_b = uuid4()

    diagnostico_response = _diagnostico_response(
        diagnosticos=[
            _diagnostico_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=production_unit_id,
                label="Talhão A",
                severidade="RISCO_ECONOMICO",
                sugestao="Revisar custos alocados e reconciliação.",
            )
        ],
    )
    recomendacao_response = _recomendacao_response(recomendacoes=[])
    prioridade_response = _prioridade_response(
        prioridades=[
            _prioridade_item(
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                scope="PRODUCTION_UNIT",
                entidade_id=production_unit_id,
                label="Talhão A",
                severidade="PRIORIDADE_CRITICA",
                score=100,
                acao_sugerida="Tratar imediatamente e validar reconciliação.",
            )
        ],
    )

    with (
        patch("agricola.inteligencia_operacional.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar", new=AsyncMock(return_value=diagnostico_response)) as diagnostico_mock,
        patch("agricola.inteligencia_operacional.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar", new=AsyncMock(return_value=recomendacao_response)) as recomendacoes_mock,
        patch("agricola.inteligencia_operacional.service.PrioridadesAgricolasV1Service.gerar", new=AsyncMock(return_value=prioridade_response)) as prioridades_mock,
    ):
        service_a = InteligenciaOperacionalAgricolaV1Service(session, tenant_a)
        service_b = InteligenciaOperacionalAgricolaV1Service(session, tenant_b)
        await service_a.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )
        await service_b.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert diagnostico_mock.await_count == 2
    assert recomendacoes_mock.await_count == 2
    assert prioridades_mock.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "altered_kwargs",
    [
        {"safra_id": uuid4()},
        {"unidade_produtiva_id": uuid4()},
        {"production_unit_id": uuid4()},
        {"data_inicio": date(2026, 2, 1)},
        {"data_fim": date(2026, 2, 28)},
    ],
)
async def test_obter_plano_por_id_respeita_safra_pu_e_periodo(altered_kwargs):
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid4()
    base_safra_id = uuid4()
    base_unidade_produtiva_id = uuid4()
    base_production_unit_id = uuid4()
    base_args = {
        "safra_id": base_safra_id,
        "unidade_produtiva_id": base_unidade_produtiva_id,
        "production_unit_id": base_production_unit_id,
        "data_inicio": date(2026, 1, 1),
        "data_fim": date(2026, 1, 31),
    }

    def _suffix(kwargs: dict) -> str:
        return ":".join(
            [
                str(kwargs["safra_id"]),
                str(kwargs.get("unidade_produtiva_id")),
                str(kwargs.get("production_unit_id")),
                str(kwargs.get("data_inicio")),
                str(kwargs.get("data_fim")),
            ]
        )

    def _make_response(kwargs: dict):
        suffix = _suffix(kwargs)
        entity_id = uuid5(NAMESPACE_URL, f"agrosaas:inteligencia-operacional:test:{suffix}")
        diagnostico_item = _diagnostico_item(
            codigo="RESULTADO_OPERACIONAL_NEGATIVO",
            scope="PRODUCTION_UNIT",
            entidade_id=entity_id,
            label=f"UP {suffix[:8]}",
            severidade="RISCO_ECONOMICO",
            sugestao="Revisar custos alocados e reconciliação.",
        )
        recomendacao_item = _recomendacao_item(
            codigo="RESULTADO_OPERACIONAL_NEGATIVO",
            scope="PRODUCTION_UNIT",
            entidade_id=entity_id,
            label=f"UP {suffix[:8]}",
            severidade="RISCO_ECONOMICO",
            acao_sugerida="Auditar custos alocados e confirmar receita oficial.",
        )
        prioridade_item = _prioridade_item(
            codigo="RESULTADO_OPERACIONAL_NEGATIVO",
            scope="PRODUCTION_UNIT",
            entidade_id=entity_id,
            label=f"UP {suffix[:8]}",
            severidade="PRIORIDADE_CRITICA",
            score=100,
            acao_sugerida="Tratar imediatamente e validar reconciliação.",
        )
        return (
            _diagnostico_response(diagnosticos=[diagnostico_item]),
            _recomendacao_response(recomendacoes=[recomendacao_item]),
            _prioridade_response(prioridades=[prioridade_item]),
        )

    async def diagnostico_side_effect(**kwargs):
        return _make_response(kwargs)[0]

    async def recomendacoes_side_effect(**kwargs):
        return _make_response(kwargs)[1]

    async def prioridades_side_effect(**kwargs):
        return _make_response(kwargs)[2]

    with (
        patch("agricola.inteligencia_operacional.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar", new=AsyncMock(side_effect=diagnostico_side_effect)),
        patch("agricola.inteligencia_operacional.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar", new=AsyncMock(side_effect=recomendacoes_side_effect)),
        patch("agricola.inteligencia_operacional.service.PrioridadesAgricolasV1Service.gerar", new=AsyncMock(side_effect=prioridades_side_effect)),
    ):
        service = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
        base_response = await service.gerar(**base_args)
        plano_id = base_response.planos[0].id

        with pytest.raises(EntityNotFoundError):
            await service.obter_plano_por_id(plano_id=plano_id, **{**base_args, **altered_kwargs})
