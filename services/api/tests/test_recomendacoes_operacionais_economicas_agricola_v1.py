from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from agricola.diagnostico.schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo
from agricola.dre.schemas import DREWarning
from agricola.recomendacoes.service import RecomendacoesOperacionaisEconomicasAgricolaV1Service
from agricola.recomendacoes.schemas import RecomendacaoAgricolaResponse


def _warning(codigo: str, origem: str) -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade="INCONSISTENCIA_MODERADA",
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid.uuid4())],
        meta={"codigo": codigo},
    )


def _diagnostico_response(*, tenant_id: uuid.UUID, safra_id: uuid.UUID) -> DiagnosticoAgricolaResponse:
    equipamento_id = uuid.uuid4()
    production_unit_id = uuid.uuid4()
    jornada_id = "jornada-a"

    risco_economico = DiagnosticoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        titulo="Resultado operacional negativo",
        severidade="RISCO_ECONOMICO",
        mensagem="Resultado operacional negativo e sujeito à reconciliação.",
        categoria="ECONOMICO",
        valor_observado=-5000.0,
        valor_referencia=0.0,
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
        posicao=1,
    )
    risco_operacional = DiagnosticoAgricolaItem(
        scope="EQUIPMENT",
        id=str(equipamento_id),
        label="Trator A",
        codigo="EQUIPAMENTO_CUSTO_ELEVADO",
        titulo="Equipamento com custo elevado",
        severidade="RISCO_OPERACIONAL",
        mensagem="Custo operacional elevado por hectare no equipamento.",
        categoria="OPERACIONAL",
        valor_observado=800.0,
        valor_referencia=300.0,
        warnings_relevantes=["EQUIPAMENTO_CUSTO_ELEVADO"],
        posicao=2,
    )
    production_unit = DiagnosticoAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=str(production_unit_id),
        label="Talhão A",
        codigo="PRODUCTION_UNIT_BAIXA_EFICIENCIA",
        titulo="ProductionUnit com baixa eficiência",
        severidade="ATENCAO",
        mensagem="ProductionUnit abaixo da média operacional do recorte.",
        categoria="OPERACIONAL",
        valor_observado=450.0,
        valor_referencia=700.0,
        warnings_relevantes=["PRODUCTION_UNIT_BAIXA_EFICIENCIA"],
        posicao=3,
    )
    atencao = DiagnosticoAgricolaItem(
        scope="JOURNEY",
        id=jornada_id,
        label="Jornada A",
        codigo="JORNADA_BAIXA_PRODUTIVIDADE",
        titulo="Jornada com baixa produtividade",
        severidade="ATENCAO",
        mensagem="Jornada improdutiva no recorte selecionado.",
        categoria="OPERACIONAL",
        valor_observado=6.0,
        valor_referencia=9.0,
        warnings_relevantes=["JORNADA_BAIXA_PRODUTIVIDADE"],
        posicao=4,
    )
    info = DiagnosticoAgricolaItem(
        scope="TENANT",
        id=str(tenant_id),
        label="Tenant consolidado",
        codigo="RECORRENCIA_WARNING_ECONOMICO",
        titulo="Recorrência de warning econômico",
        severidade="INFO",
        mensagem="Warnings econômicos recorrentes identificados no tenant.",
        categoria="RECORRENCIA",
        warnings_relevantes=["MOVIMENTO_COM_CUSTO_SEM_ALLOCATION"],
        posicao=5,
    )

    return DiagnosticoAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        diagnosticos=[risco_economico, risco_operacional, production_unit, atencao, info],
        ranking=[risco_economico, risco_operacional, production_unit, atencao, info],
        resumo=DiagnosticoAgricolaResumo(total=5, info=1, atencao=2, risco_operacional=1, risco_economico=1),
        warnings=[_warning("CUSTO_HECTARE_ACIMA_MEDIA", "diagnostico_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnósticos sujeitos à reconciliação.",
    )


@pytest.mark.asyncio
async def test_recomendacoes_v1_service_mapeia_rankeia_e_propaga_warnings():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = AsyncMock()
    captured: dict[str, object] = {}

    class FakeDiagnosticoService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id
            captured["session_type"] = type(session).__name__

        async def gerar(self, **kwargs):
            captured["kwargs"] = kwargs
            return _diagnostico_response(tenant_id=tenant_id, safra_id=safra_id)

    with (
        patch("agricola.recomendacoes.service.DiagnosticoOperacionalEconomicoAgricolaV1Service", FakeDiagnosticoService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        svc = RecomendacoesOperacionaisEconomicasAgricolaV1Service(session, tenant_id)
        response = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=uuid.uuid4(),
            production_unit_id=uuid.uuid4(),
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
        )

    assert isinstance(response, RecomendacaoAgricolaResponse)
    assert captured["tenant_id"] == tenant_id
    assert response.tenant_id == tenant_id
    assert response.safra_id == safra_id
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "recomendações sujeitas à reconciliação."
    assert response.resumo.total == 5
    assert response.resumo.nova == 5
    assert response.resumo.risco_economico == 1
    assert response.resumo.risco_operacional == 1
    assert response.resumo.atencao == 2
    assert response.resumo.info == 1
    assert response.resumo.por_tipo == {
        "ANALISE_PRODUCTION_UNIT": 1,
        "INSPECAO_EQUIPAMENTO": 1,
        "INVESTIGACAO_MARGEM_NEGATIVA": 1,
        "REVISAO_JORNADA": 1,
        "REVISAO_RECONCILIACAO_ECONOMICA": 1,
    }
    assert [item.tipo for item in response.recomendacoes] == [
        "INVESTIGACAO_MARGEM_NEGATIVA",
        "INSPECAO_EQUIPAMENTO",
        "ANALISE_PRODUCTION_UNIT",
        "REVISAO_JORNADA",
        "REVISAO_RECONCILIACAO_ECONOMICA",
    ]
    assert [item.posicao for item in response.recomendacoes] == [1, 2, 3, 4, 5]
    assert response.recomendacoes[0].warnings_relevantes == ["CUSTO_HECTARE_ACIMA_MEDIA"]
    assert response.warnings[0].codigo == "CUSTO_HECTARE_ACIMA_MEDIA"
    assert captured["kwargs"]["safra_id"] == safra_id
    assert captured["kwargs"]["production_unit_id"] is not None
    assert captured["kwargs"]["unidade_produtiva_id"] is not None
    legacy_report.assert_not_called()
    legacy_lancamento.assert_not_called()
