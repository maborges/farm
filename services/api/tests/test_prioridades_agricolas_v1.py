from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agricola.benchmark.schemas import BenchmarkAgricolaDestaques, BenchmarkAgricolaItem, BenchmarkAgricolaResponse
from agricola.diagnostico.schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.eficiencia.schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem
from agricola.prioridades.schemas import PrioridadeAgricolaResponse
from agricola.prioridades.service import PrioridadesAgricolasV1Service
from agricola.recomendacoes.schemas import RecomendacaoAgricolaItem, RecomendacaoAgricolaResponse, RecomendacaoAgricolaResumo
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse


def _warning(codigo: str, origem: str, severidade: str = "INCONSISTENCIA_MODERADA") -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade=severidade,
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid.uuid4())],
        meta={"codigo": codigo},
    )


def _dre_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> DREAgricolaResponse:
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        cultura="SOJA",
        receita_bruta=120000.0,
        deducoes=8000.0,
        receita_liquida=112000.0,
        custos_diretos=40000.0,
        custos_operacionais=15000.0,
        margem_bruta=72000.0,
        despesas_operacionais=12000.0,
        resultado_operacional=45000.0,
        kpis=DREAgricolaKpis(
            area_total_ha=100.0,
            receita_liquida=112000.0,
            custo_operacional_total=67000.0,
            margem_bruta=72000.0,
            resultado_operacional=45000.0,
            margem_pct=33.9,
            custo_por_hectare=670.0,
            receita_por_hectare=1120.0,
            resultado_por_hectare=450.0,
            sujeito_reconciliacao=True,
            observacao_reconciliacao="prioridades sujeitas à reconciliação.",
            warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO", "CUSTO_HECTARE_ACIMA_MEDIA"],
        ),
        receita=DREAgricolaSection(),
        custos_diretos_detalhe=DREAgricolaSection(),
        custos_operacionais_detalhe=DREAgricolaSection(),
        despesas_operacionais_detalhe=DREAgricolaSection(),
        warnings=[
            _warning("RESULTADO_OPERACIONAL_NEGATIVO", "dre_v1", "RISCO_ECONOMICO"),
            _warning("CUSTO_HECTARE_ACIMA_MEDIA", "dre_v1", "INCONSISTENCIA_MODERADA"),
        ],
        reconciliacao=DREReconcilacaoMeta(),
    )


def _rentabilidade_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, pu_id: uuid.UUID) -> RentabilidadeAgricolaResponse:
    safra = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=100.0,
        resultado_operacional=45000.0,
        margem_pct=33.9,
        receita_liquida_por_hectare=1120.0,
        resultado_por_hectare=450.0,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="rentabilidade sujeita à reconciliação.",
        warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO"],
    )
    unit = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_id,
        label="Talhão A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        resultado_operacional=10000.0,
        margem_pct=20.0,
        receita_liquida_por_hectare=900.0,
        resultado_por_hectare=300.0,
        warnings_relevantes=["PRODUCTION_UNIT_BAIXA_EFICIENCIA"],
        posicao=1,
    )
    return RentabilidadeAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[unit],
        ranking=[unit],
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "rentabilidade_v1", "RISCO_ECONOMICO")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="rentabilidade sujeita à reconciliação.",
    )


def _eficiencia_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, pu_id: uuid.UUID, equipment_id: uuid.UUID) -> EficienciaOperacionalAgricolaResponse:
    safra = EficienciaOperacionalItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=100.0,
        hectares_totais=90.0,
        horas_totais=100.0,
        quantidade_operacoes=10,
        quantidade_jornadas=5,
        quantidade_apontamentos=10,
        custo_operacional_total=67000.0,
        custo_operacional_por_hectare=670.0,
        custo_operacional_por_operacao=6700.0,
        horas_por_hectare=1.0,
        hectares_por_jornada=18.0,
        resultado_operacional=45000.0,
        resultado_por_hectare=450.0,
        margem_pct=33.9,
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
    )
    production_unit = EficienciaOperacionalItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_id),
        label="Talhão A",
        safra_id=safra_id,
        production_unit_id=pu_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        hectares_totais=25.0,
        horas_totais=40.0,
        quantidade_operacoes=4,
        quantidade_jornadas=2,
        quantidade_apontamentos=4,
        custo_operacional_total=15000.0,
        custo_operacional_por_hectare=600.0,
        custo_operacional_por_operacao=3750.0,
        horas_por_hectare=1.6,
        hectares_por_jornada=12.5,
        resultado_operacional=10000.0,
        resultado_por_hectare=300.0,
        margem_pct=20.0,
        warnings_relevantes=["PRODUCTION_UNIT_BAIXA_EFICIENCIA"],
        posicao=1,
    )
    equipamento = EficienciaOperacionalItem(
        scope="EQUIPMENT",
        id=str(equipment_id),
        label="Trator A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        equipamento_id=equipment_id,
        area_total_ha=30.0,
        hectares_totais=25.0,
        horas_totais=40.0,
        quantidade_operacoes=2,
        quantidade_jornadas=2,
        quantidade_apontamentos=2,
        custo_operacional_total=12000.0,
        custo_operacional_por_hectare=400.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=["EQUIPAMENTO_CUSTO_ELEVADO"],
    )
    operacao = EficienciaOperacionalItem(
        scope="OPERATION",
        id="operacao-a",
        label="Pulverização",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        operacao_id=uuid.uuid4(),
        area_total_ha=30.0,
        hectares_totais=25.0,
        horas_totais=10.0,
        quantidade_operacoes=1,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
        custo_operacional_total=3000.0,
        custo_operacional_por_hectare=100.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=[],
    )
    return EficienciaOperacionalAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[production_unit],
        equipamentos=[equipamento],
        operacoes=[operacao],
        ranking=[production_unit],
        warnings=[_warning("PRODUCTION_UNIT_BAIXA_EFICIENCIA", "eficiencia_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="eficiência sujeita à reconciliação.",
    )


def _benchmark_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, pu_id: uuid.UUID) -> BenchmarkAgricolaResponse:
    safra = BenchmarkAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=100.0,
        resultado_operacional=45000.0,
        margem_pct=33.9,
        receita_liquida_por_hectare=1120.0,
        resultado_por_hectare=450.0,
        custo_operacional_total=67000.0,
        custo_operacional_por_hectare=670.0,
        horas_por_hectare=1.0,
        hectares_por_jornada=18.0,
        warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO"],
    )
    unit = BenchmarkAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_id,
        label="Talhão A",
        safra_id=safra_id,
        production_unit_id=pu_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        resultado_operacional=10000.0,
        margem_pct=20.0,
        receita_liquida_por_hectare=900.0,
        resultado_por_hectare=300.0,
        custo_operacional_total=15000.0,
        custo_operacional_por_hectare=600.0,
        custo_operacional_por_operacao=3750.0,
        horas_por_hectare=1.6,
        hectares_por_jornada=12.5,
        warnings_relevantes=[],
        posicao=1,
        destaque="MELHOR",
    )
    return BenchmarkAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        safra=safra,
        production_units=[unit],
        ranking=[unit],
        destaques=BenchmarkAgricolaDestaques(melhor=unit, referencia=unit, ponto_atencao=unit),
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "benchmark_v1", "RISCO_ECONOMICO")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="benchmark sujeito à reconciliação.",
    )


def _diagnostico_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, pu_id: uuid.UUID, equipment_id: uuid.UUID) -> DiagnosticoAgricolaResponse:
    item_resultado = DiagnosticoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        titulo="Resultado operacional negativo",
        severidade="RISCO_ECONOMICO",
        mensagem="Resultado operacional negativo na safra.",
        categoria="ECONOMICO",
        valor_observado=45000.0,
        valor_referencia=0.0,
        sugestao="Revisar a margem e a reconciliação econômica.",
        warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO"],
        posicao=1,
    )
    item_equipment = DiagnosticoAgricolaItem(
        scope="EQUIPMENT",
        id=str(equipment_id),
        label="Trator A",
        codigo="EQUIPAMENTO_CUSTO_ELEVADO",
        titulo="Equipamento com custo elevado",
        severidade="RISCO_OPERACIONAL",
        mensagem="Custo operacional elevado do equipamento.",
        categoria="OPERACIONAL",
        valor_observado=400.0,
        valor_referencia=250.0,
        sugestao="Inspecionar o equipamento.",
        warnings_relevantes=["EQUIPAMENTO_CUSTO_ELEVADO"],
        posicao=2,
    )
    item_pu = DiagnosticoAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_id),
        label="Talhão A",
        codigo="PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        titulo="ProductionUnit com baixa eficiência",
        severidade="ATENCAO",
        mensagem="ProductionUnit abaixo da média operacional.",
        categoria="OPERACIONAL",
        valor_observado=300.0,
        valor_referencia=500.0,
        sugestao="Revisar a ProductionUnit e o uso de recursos.",
        warnings_relevantes=["PRODUCTION_UNIT_BAIXA_EFICIENCIA"],
        posicao=3,
    )
    return DiagnosticoAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=pu_id,
        unidade_produtiva_id=unidade_produtiva_id,
        diagnosticos=[item_resultado, item_equipment, item_pu],
        ranking=[item_resultado, item_equipment, item_pu],
        resumo=DiagnosticoAgricolaResumo(total=3, info=0, atencao=1, risco_operacional=1, risco_economico=1),
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "diagnostico_v1", "RISCO_ECONOMICO")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnósticos sujeitos à reconciliação.",
    )


def _recomendacoes_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID, unidade_produtiva_id: uuid.UUID, pu_id: uuid.UUID, equipment_id: uuid.UUID) -> RecomendacaoAgricolaResponse:
    rec_resultado = RecomendacaoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        tipo="INVESTIGACAO_MARGEM_NEGATIVA",
        severidade="RISCO_ECONOMICO",
        origem_diagnostica_codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        origem_diagnostica_titulo="Resultado operacional negativo",
        contexto_operacional="Resultado operacional negativo na safra.",
        contexto_economico="Prioridade econômica consolidada.",
        explicacao_objetiva="Investigar a margem negativa.",
        acao_sugerida="Revisar margem, receita e custo.",
        entidade_tipo="SAFRA",
        entidade_id=str(safra_id),
        entidade_label="SAFRA • SOJA",
        warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO"],
        posicao=1,
    )
    rec_equipment = RecomendacaoAgricolaItem(
        scope="EQUIPMENT",
        id=str(equipment_id),
        label="Trator A",
        tipo="INSPECAO_EQUIPAMENTO",
        severidade="RISCO_OPERACIONAL",
        origem_diagnostica_codigo="EQUIPAMENTO_CUSTO_ELEVADO",
        origem_diagnostica_titulo="Equipamento com custo elevado",
        contexto_operacional="Custo operacional elevado do equipamento.",
        contexto_economico="Recomendação operacional governada.",
        explicacao_objetiva="Inspecionar equipamento.",
        acao_sugerida="Agendar inspeção e validar consumo.",
        entidade_tipo="EQUIPMENT",
        entidade_id=str(equipment_id),
        entidade_label="Trator A",
        warnings_relevantes=["EQUIPAMENTO_CUSTO_ELEVADO"],
        posicao=2,
    )
    rec_pu = RecomendacaoAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_id),
        label="Talhão A",
        tipo="ANALISE_PRODUCTION_UNIT",
        severidade="ATENCAO",
        origem_diagnostica_codigo="PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        origem_diagnostica_titulo="ProductionUnit com baixa eficiência",
        contexto_operacional="ProductionUnit abaixo da média operacional.",
        contexto_economico="Eficiência operacional abaixo do benchmark.",
        explicacao_objetiva="Analisar a ProductionUnit abaixo da média.",
        acao_sugerida="Revisar custo, resultado e produtividade.",
        entidade_tipo="PRODUCTION_UNIT",
        entidade_id=str(pu_id),
        entidade_label="Talhão A",
        warnings_relevantes=["PRODUCTION_UNIT_BAIXA_EFICIENCIA"],
        posicao=3,
    )
    return RecomendacaoAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        recomendacoes=[rec_resultado, rec_equipment, rec_pu],
        resumo=RecomendacaoAgricolaResumo(total=3, nova=3, por_tipo={
            "ANALISE_PRODUCTION_UNIT": 1,
            "INSPECAO_EQUIPAMENTO": 1,
            "INVESTIGACAO_MARGEM_NEGATIVA": 1,
        }),
        warnings=[_warning("RESULTADO_OPERACIONAL_NEGATIVO", "recomendacoes_v1", "RISCO_ECONOMICO")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="recomendações sujeitas à reconciliação.",
    )


def _status_log(resource_id: uuid.UUID, prioridade_id: str, status_novo: str, observacao: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        resource="agricola_prioridade_status",
        resource_id=resource_id,
        payload_after={
            "prioridade_id": prioridade_id,
            "status_anterior": "NOVA",
            "status_novo": status_novo,
            "status": status_novo,
            "observacao": observacao,
            "responsavel_id": str(uuid.uuid4()),
            "responsavel_nome": "Responsável",
        },
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_prioridades_v1_service_consolida_fila_e_scoreia_sem_duplicar():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    pu_id = uuid.uuid4()
    equipment_id = uuid.uuid4()
    session = AsyncMock()
    captured: dict[str, object] = {}

    class FakeDreService:
        def __init__(self, session, tenant_id):
            captured["dre_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["dre_kwargs"] = kwargs
            return _dre_response(tenant_id=tenant_id, safra_id=safra_id, unidade_produtiva_id=unidade_produtiva_id)

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            captured["rent_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["rent_kwargs"] = kwargs
            return _rentabilidade_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeEficienciaService:
        def __init__(self, session, tenant_id):
            captured["eff_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["eff_kwargs"] = kwargs
            return _eficiencia_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeBenchmarkService:
        def __init__(self, session, tenant_id):
            captured["benchmark_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["benchmark_kwargs"] = kwargs
            return _benchmark_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeDiagnosticoService:
        def __init__(self, session, tenant_id):
            captured["diag_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["diag_kwargs"] = kwargs
            return _diagnostico_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeRecomendacoesService:
        def __init__(self, session, tenant_id):
            captured["reco_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["reco_kwargs"] = kwargs
            return _recomendacoes_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    with (
        patch("agricola.prioridades.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.prioridades.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
        patch("agricola.prioridades.service.EficienciaOperacionalAgricolaV1Service", FakeEficienciaService),
        patch("agricola.prioridades.service.BenchmarkAgricolaV1Service", FakeBenchmarkService),
        patch("agricola.prioridades.service.DiagnosticoOperacionalEconomicoAgricolaV1Service", FakeDiagnosticoService),
        patch("agricola.prioridades.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service", FakeRecomendacoesService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        session.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))
        svc = PrioridadesAgricolasV1Service(session, tenant_id)
        response = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=pu_id,
            data_inicio=datetime(2026, 1, 1).date(),
            data_fim=datetime(2026, 1, 31).date(),
        )

    assert isinstance(response, PrioridadeAgricolaResponse)
    assert response.tenant_id == tenant_id
    assert response.safra_id == safra_id
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "prioridades sujeitas à reconciliação."
    assert response.resumo.total == 4
    assert response.resumo.prioridade_critica == 1
    assert response.resumo.risco_operacional >= 1
    assert response.resumo.atencao >= 1
    assert response.prioridades[0].tipo == "RESULTADO_OPERACIONAL_NEGATIVO"
    assert response.prioridades[0].severidade == "PRIORIDADE_CRITICA"
    assert response.prioridades[0].recorrencia == 6
    assert response.prioridades[0].fontes_relacionadas == ["DIAGNOSTICO", "RECOMENDACAO", "WARNING"]
    assert response.prioridades[0].score_prioridade >= response.prioridades[1].score_prioridade
    assert {item.tipo for item in response.prioridades} == {
        "RESULTADO_OPERACIONAL_NEGATIVO",
        "EQUIPAMENTO_CUSTO_ELEVADO",
        "PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        "CUSTO_HECTARE_ACIMA_MEDIA",
    }
    assert captured["dre_tenant_id"] == tenant_id
    assert captured["rent_tenant_id"] == tenant_id
    assert captured["eff_tenant_id"] == tenant_id
    assert captured["benchmark_tenant_id"] == tenant_id
    assert captured["diag_tenant_id"] == tenant_id
    assert captured["reco_tenant_id"] == tenant_id
    assert captured["dre_kwargs"]["safra_id"] == safra_id
    assert captured["rent_kwargs"]["production_unit_id"] == pu_id
    assert captured["eff_kwargs"]["production_unit_id"] == pu_id
    assert captured["benchmark_kwargs"]["production_unit_id"] == pu_id
    assert captured["diag_kwargs"]["production_unit_id"] == pu_id
    assert captured["reco_kwargs"]["production_unit_id"] == pu_id
    legacy_report.assert_not_called()
    legacy_lancamento.assert_not_called()


@pytest.mark.asyncio
async def test_prioridades_v1_service_aplica_status_da_auditoria_e_atualiza_resumo():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    pu_id = uuid.uuid4()
    equipment_id = uuid.uuid4()
    session = AsyncMock()

    class FakeDreService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _dre_response(tenant_id=tenant_id, safra_id=safra_id, unidade_produtiva_id=unidade_produtiva_id)

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _rentabilidade_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeEficienciaService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _eficiencia_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeBenchmarkService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _benchmark_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeDiagnosticoService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _diagnostico_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeRecomendacoesService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _recomendacoes_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    prioridade_id = f"RESULTADO_OPERACIONAL_NEGATIVO:SAFRA:{safra_id}"
    status_resource_id = PrioridadesAgricolasV1Service(session, tenant_id)._status_resource_id(prioridade_id)
    session.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [_status_log(status_resource_id, prioridade_id, "EM_ANALISE", "Observação de campo")])))

    with (
        patch("agricola.prioridades.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.prioridades.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
        patch("agricola.prioridades.service.EficienciaOperacionalAgricolaV1Service", FakeEficienciaService),
        patch("agricola.prioridades.service.BenchmarkAgricolaV1Service", FakeBenchmarkService),
        patch("agricola.prioridades.service.DiagnosticoOperacionalEconomicoAgricolaV1Service", FakeDiagnosticoService),
        patch("agricola.prioridades.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service", FakeRecomendacoesService),
    ):
        response = await PrioridadesAgricolasV1Service(session, tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=pu_id,
        )

    assert response.prioridades[0].status == "EM_ANALISE"
    assert response.resumo.em_analise == 1


@pytest.mark.asyncio
async def test_prioridades_v1_service_registra_status_em_auditoria_e_retorna_historico():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    pu_id = uuid.uuid4()
    equipment_id = uuid.uuid4()
    session = AsyncMock()
    captured: dict[str, object] = {}

    class FakeDreService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _dre_response(tenant_id=tenant_id, safra_id=safra_id, unidade_produtiva_id=unidade_produtiva_id)

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _rentabilidade_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeEficienciaService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _eficiencia_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeBenchmarkService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _benchmark_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
            )

    class FakeDiagnosticoService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _diagnostico_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    class FakeRecomendacoesService:
        def __init__(self, session, tenant_id):
            pass

        async def gerar(self, **kwargs):
            return _recomendacoes_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_id=pu_id,
                equipment_id=equipment_id,
            )

    prioridade_id = f"RESULTADO_OPERACIONAL_NEGATIVO:SAFRA:{safra_id}"
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    session.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))

    historico_response = SimpleNamespace(
        prioridade_id=prioridade_id,
        prioridade_status_id=svc._status_resource_id(prioridade_id),
        status_atual="RESOLVIDA",
        historico=[],
        sujeito_reconciliacao=True,
    )

    with (
        patch("agricola.prioridades.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.prioridades.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
        patch("agricola.prioridades.service.EficienciaOperacionalAgricolaV1Service", FakeEficienciaService),
        patch("agricola.prioridades.service.BenchmarkAgricolaV1Service", FakeBenchmarkService),
        patch("agricola.prioridades.service.DiagnosticoOperacionalEconomicoAgricolaV1Service", FakeDiagnosticoService),
        patch("agricola.prioridades.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service", FakeRecomendacoesService),
        patch("agricola.prioridades.service.write_audit_log", new=AsyncMock()) as audit_mock,
        patch.object(PrioridadesAgricolasV1Service, "obter_status", new=AsyncMock(return_value=historico_response)) as obter_status_mock,
    ):
        response = await svc.atualizar_status(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            status="RESOLVIDA",
            observacao="Concluído em campo",
            user_id=uuid.uuid4(),
            responsavel_nome="Usuário Teste",
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=pu_id,
        )

    assert response.status_atual == "RESOLVIDA"
    assert audit_mock.await_count == 1
    _, kwargs = audit_mock.call_args
    assert kwargs["resource"] == "agricola_prioridade_status"
    assert kwargs["payload_after"]["status_novo"] == "RESOLVIDA"
    assert kwargs["payload_after"]["observacao"] == "Concluído em campo"
    obter_status_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_prioridades_v1_status_resource_id_is_tenant_scoped():
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    session = AsyncMock()
    svc_a = PrioridadesAgricolasV1Service(session, tenant_a)
    svc_b = PrioridadesAgricolasV1Service(session, tenant_b)

    prioridade_id = "RESULTADO_OPERACIONAL_NEGATIVO:SAFRA:00000000-0000-0000-0000-000000000001"

    assert svc_a._status_resource_id(prioridade_id) != svc_b._status_resource_id(prioridade_id)
