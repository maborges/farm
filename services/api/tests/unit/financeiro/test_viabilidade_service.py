import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from financeiro.routers import viabilidade as viabilidade_router
from financeiro.schemas.viabilidade_schema import (
    ComparativoViabilidadeInput,
    PrecoEquilibrioTmaInput,
    ProjetoInvestimentoInput,
    TmaCalculoInput,
)
from financeiro.services.viabilidade_service import ViabilidadeFinanceiraService


def test_calcular_tma_ponderada_capital_proprio_e_plano_safra():
    svc = ViabilidadeFinanceiraService()
    resultado = svc.calcular_tma(
        TmaCalculoInput(
            percentual_capital_proprio=40.0,
            custo_oportunidade_proprio_aa=12.0,
            percentual_financiamento=60.0,
            taxa_financiamento_aa=8.0,
            premio_risco_agro_aa=2.5,
        )
    )

    # Custo ponderado = 0.4 * 12 + 0.6 * 8 = 4.8 + 4.8 = 9.6%
    # TMA = 9.6 + 2.5 = 12.1%
    assert resultado.custo_ponderado_capital_aa == 9.6
    assert resultado.premio_risco_agro_aa == 2.5
    assert resultado.tma_calculada_aa == 12.1
    assert "9.60%" in resultado.detalhamento


def test_projeto_viavel_vpl_positivo_tir_maior_que_tma_e_payback_descontado_maior_que_simples():
    svc = ViabilidadeFinanceiraService()
    projeto = ProjetoInvestimentoInput(
        id="pivo-01",
        nome="Pivô Central 100 ha",
        categoria="IRRIGACAO",
        investimento_inicial=1_000_000.0,
        tma_aa=12.0,
        prazo_maximo_aceitavel_anos=4.0,
        fluxos_caixa_anuais=[380_000.0, 400_000.0, 420_000.0, 440_000.0, 460_000.0],
        valor_residual_final=150_000.0,
    )

    out = svc.analisar_projeto(projeto)

    assert out.vpl > 0
    assert out.tir_aa is not None and out.tir_aa > 12.0
    assert out.margem_seguranca_tir_pp is not None and out.margem_seguranca_tir_pp > 0
    assert out.payback_simples_anos is not None
    assert out.payback_descontado_anos is not None
    assert out.payback_descontado_anos > out.payback_simples_anos
    assert out.payback_descontado_anos <= 4.0
    assert out.indice_lucratividade > 1.0
    assert out.fluxo_nao_convencional is False
    assert out.decisao_vpl == "ACEITAR"
    assert out.decisao_tir == "ACEITAR"
    assert out.decisao_payback == "ACEITAR"
    assert out.veredito_final == "VIAVEL"
    assert len(out.evolucao_anual) == 6  # Ano 0..5


def test_projeto_inviavel_vpl_negativo_rejeita():
    svc = ViabilidadeFinanceiraService()
    projeto = ProjetoInvestimentoInput(
        id="maq-ruim",
        nome="Colheitadeira Subutilizada",
        categoria="MAQUINARIO",
        investimento_inicial=1_500_000.0,
        tma_aa=14.0,
        prazo_maximo_aceitavel_anos=5.0,
        fluxos_caixa_anuais=[250_000.0, 260_000.0, 260_000.0, 250_000.0, 250_000.0],
        valor_residual_final=100_000.0,
    )

    out = svc.analisar_projeto(projeto)

    assert out.vpl < 0
    assert out.tir_aa is not None and out.tir_aa < 14.0
    assert out.margem_seguranca_tir_pp is not None and out.margem_seguranca_tir_pp < 0
    assert out.decisao_vpl == "REJEITAR"
    assert out.decisao_tir == "REJEITAR"
    assert out.veredito_final == "INVIAVEL"


def test_projeto_vpl_positivo_mas_payback_acima_do_limite_alerta_liquidez():
    svc = ViabilidadeFinanceiraService()
    projeto = ProjetoInvestimentoInput(
        id="silo-lento",
        nome="Silo Expansão Longo Prazo",
        categoria="ARMAZENAGEM",
        investimento_inicial=1_000_000.0,
        tma_aa=10.0,
        prazo_maximo_aceitavel_anos=3.0,
        fluxos_caixa_anuais=[220_000.0, 240_000.0, 260_000.0, 350_000.0, 450_000.0, 500_000.0],
        valor_residual_final=0.0,
    )

    out = svc.analisar_projeto(projeto)

    assert out.vpl > 0
    assert out.payback_descontado_anos is not None and out.payback_descontado_anos > 3.0
    assert out.decisao_vpl == "ACEITAR"
    assert out.decisao_payback == "REJEITAR"
    assert out.veredito_final == "ATENCAO_LIQUIDEZ"


def test_fluxo_nao_convencional_detecta_multiplas_trocas_de_sinal_e_calcula_tirm():
    svc = ViabilidadeFinanceiraService()
    projeto = ProjetoInvestimentoInput(
        id="pivo-reforma",
        nome="Pivô com Reforma Pesada no Ano 3",
        categoria="IRRIGACAO",
        investimento_inicial=500_000.0,
        tma_aa=12.0,
        prazo_maximo_aceitavel_anos=5.0,
        fluxos_caixa_anuais=[280_000.0, 290_000.0, -350_000.0, 320_000.0, 350_000.0],
        valor_residual_final=80_000.0,
    )

    out = svc.analisar_projeto(projeto)

    assert out.fluxo_nao_convencional is True
    assert out.tirm_aa is not None
    assert out.decisao_tir == "INCONCLUSIVO"


def test_comparar_projetos_mutuamente_excludentes_prioriza_maior_vpl():
    svc = ViabilidadeFinanceiraService()
    # Projeto A: investimento menor, TIR percentual altíssima, mas gera menos riqueza em R$ (VPL menor)
    projeto_menor_escala = ProjetoInvestimentoInput(
        id="proj-a",
        nome="Projeto Pequeno (Alta TIR)",
        categoria="MAQUINARIO",
        investimento_inicial=100_000.0,
        tma_aa=12.0,
        prazo_maximo_aceitavel_anos=5.0,
        fluxos_caixa_anuais=[90_000.0, 90_000.0, 90_000.0],
        valor_residual_final=0.0,
    )
    # Projeto B: investimento maior, TIR menor que A, mas VPL absoluto muito maior
    projeto_maior_riqueza = ProjetoInvestimentoInput(
        id="proj-b",
        nome="Projeto Grande (Maior VPL)",
        categoria="ARMAZENAGEM",
        investimento_inicial=1_000_000.0,
        tma_aa=12.0,
        prazo_maximo_aceitavel_anos=5.0,
        fluxos_caixa_anuais=[550_000.0, 550_000.0, 550_000.0],
        valor_residual_final=0.0,
    )

    comparativo = svc.comparar_projetos(
        ComparativoViabilidadeInput(projetos=[projeto_menor_escala, projeto_maior_riqueza])
    )

    res_a = next(r for r in comparativo.resultados if r.id == "proj-a")
    res_b = next(r for r in comparativo.resultados if r.id == "proj-b")
    assert res_a.tir_aa is not None and res_b.tir_aa is not None
    assert res_a.tir_aa > res_b.tir_aa
    assert res_b.vpl > res_a.vpl
    assert comparativo.projeto_recomendado_id == "proj-b"


def test_router_viabilidade_templates_e_simulacao():
    app = FastAPI()
    app.include_router(viabilidade_router.router)
    app.dependency_overrides[viabilidade_router.get_tenant_id] = lambda: uuid.uuid4()
    app.dependency_overrides[viabilidade_router.MODULE_DEPENDENCY] = lambda: None

    client = TestClient(app)

    templates_res = client.get("/viabilidade/templates")
    assert templates_res.status_code == 200
    templates = templates_res.json()
    assert len(templates) >= 4

    tma_res = client.post(
        "/viabilidade/calcular-tma",
        json={
            "percentual_capital_proprio": 50.0,
            "custo_oportunidade_proprio_aa": 12.0,
            "percentual_financiamento": 50.0,
            "taxa_financiamento_aa": 8.0,
            "premio_risco_agro_aa": 2.0,
        },
    )
    assert tma_res.status_code == 200
    assert tma_res.json()["tma_calculada_aa"] == 12.0

    sim_res = client.post(
        "/viabilidade/simular",
        json={
            "projetos": [
                {
                    "id": templates[0]["id"],
                    "nome": templates[0]["nome"],
                    "categoria": templates[0]["categoria"],
                    "investimento_inicial": templates[0]["investimento_inicial"],
                    "tma_aa": templates[0]["tma_sugerida_aa"],
                    "prazo_maximo_aceitavel_anos": templates[0]["prazo_maximo_aceitavel_anos"],
                    "fluxos_caixa_anuais": templates[0]["fluxos_caixa_anuais"],
                    "valor_residual_final": templates[0]["valor_residual_final"],
                }
            ]
        },
    )
    assert sim_res.status_code == 200
    body = sim_res.json()
    assert body["projeto_recomendado_id"] == templates[0]["id"]
    assert body["resultados"][0]["vpl"] > 0

    eq_res = client.post(
        "/viabilidade/preco-equilibrio-tma",
        json={
            "custo_total_safra": 1_000_000.0,
            "producao_estimada_sc": 10_000.0,
            "tma_aa": 12.0,
            "prazo_ciclo_meses": 12.0,
            "preco_mercado_atual_sc": 120.0,
            "taxa_cambio_base": 5.8,
            "percentual_ja_travado": 25.0,
        },
    )
    assert eq_res.status_code == 200
    eq_body = eq_res.json()
    assert eq_body["preco_equilibrio_contabil_sc"] == 100.0
    assert eq_body["preco_equilibrio_tma_sc"] == 112.0
    assert eq_body["acao_hedge_recomendada"] == "TRAVAR_MARGEM"
    assert len(eq_body["sensibilidade_cambio"]) == 3


def test_preco_equilibrio_tma_cenarios_hedge_e_sensibilidade_cambio():
    svc = ViabilidadeFinanceiraService()

    # 1. Preço supera equilíbrio TMA (R$ 112/sc) -> TRAVAR_MARGEM e VPL >= 0
    travar = svc.calcular_preco_equilibrio_tma(
        PrecoEquilibrioTmaInput(
            custo_total_safra=1_000_000.0,
            producao_estimada_sc=10_000.0,
            tma_aa=12.0,
            prazo_ciclo_meses=12.0,
            preco_mercado_atual_sc=125.0,
            taxa_cambio_base=5.8,
        )
    )
    assert travar.preco_equilibrio_contabil_sc == 100.0
    assert travar.preco_equilibrio_tma_sc == 112.0
    assert travar.vpl_safra_atual > 0
    assert travar.acao_hedge_recomendada == "TRAVAR_MARGEM"
    assert [c.cenario for c in travar.sensibilidade_cambio] == ["Dólar -10%", "Base", "Dólar +10%"]

    # 2. Preço cobre contábil (>= 100), mas fica abaixo da TMA (< 112) -> ATENCAO_TMA e VPL < 0
    atencao = svc.calcular_preco_equilibrio_tma(
        PrecoEquilibrioTmaInput(
            custo_total_safra=1_000_000.0,
            producao_estimada_sc=10_000.0,
            tma_aa=12.0,
            prazo_ciclo_meses=12.0,
            preco_mercado_atual_sc=105.0,
            taxa_cambio_base=5.8,
        )
    )
    assert atencao.vpl_safra_atual < 0
    assert atencao.acao_hedge_recomendada == "ATENCAO_TMA"

    # 3. Preço abaixo até do equilíbrio contábil (< 100) -> DEFESA_CAIXA
    defesa = svc.calcular_preco_equilibrio_tma(
        PrecoEquilibrioTmaInput(
            custo_total_safra=1_000_000.0,
            producao_estimada_sc=10_000.0,
            tma_aa=12.0,
            prazo_ciclo_meses=12.0,
            preco_mercado_atual_sc=92.0,
            taxa_cambio_base=5.8,
        )
    )
    assert defesa.vpl_safra_atual < 0
    assert defesa.acao_hedge_recomendada == "DEFESA_CAIXA"
