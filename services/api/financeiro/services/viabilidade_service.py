from __future__ import annotations

from datetime import date
import math

from financeiro.schemas.relatorio_schema import AnaliseDecisaoReativa, FluxoCaixaPeriodo
from financeiro.schemas.viabilidade_schema import (
    CenarioSensibilidadeCambio,
    ComparativoViabilidadeInput,
    ComparativoViabilidadeOutput,
    FluxoAnoDetalheOutput,
    PrecoEquilibrioTmaInput,
    PrecoEquilibrioTmaOutput,
    ProjetoInvestimentoInput,
    ProjetoViabilidadeOutput,
    TemplateProjetoAgroOutput,
    TmaCalculoInput,
    TmaCalculoOutput,
)

TOLERANCIA_MOEDA = 0.01
TOLERANCIA_TAXA = 0.01


class ViabilidadeFinanceiraService:
    """
    Motor de análise de viabilidade econômica de investimentos agropecuários.

    Implementa TMA ponderada, Payback Simples e Descontado, VPL, TIR, TIRM
    e comparação de projetos mutuamente excludentes.
    """

    @staticmethod
    def _montar_serie_fluxos(projeto: ProjetoInvestimentoInput) -> list[float]:
        """Monta o vetor de fluxos do Ano 0 ao Ano N incluindo valor residual final."""
        fluxos = [-float(projeto.investimento_inicial), *[float(v) for v in projeto.fluxos_caixa_anuais]]
        if projeto.valor_residual_final > 0:
            fluxos[-1] += float(projeto.valor_residual_final)
        return fluxos

    @staticmethod
    def _contar_trocas_sinal(fluxos: list[float]) -> int:
        """Conta quantas vezes o fluxo de caixa muda de sinal (regra de Descartes)."""
        sinais = [1 if v > 0 else -1 for v in fluxos if abs(v) > 1e-9]
        return sum(1 for idx in range(1, len(sinais)) if sinais[idx] != sinais[idx - 1])

    @staticmethod
    def _calcular_vpl_para_taxa(fluxos: list[float], taxa_decimal: float) -> float:
        """Calcula o Valor Presente Líquido para uma taxa decimal anual."""
        return sum(cf / ((1.0 + taxa_decimal) ** ano) for ano, cf in enumerate(fluxos))

    @classmethod
    def _calcular_tir(cls, fluxos: list[float]) -> float | None:
        """Calcula a Taxa Interna de Retorno anual (%) por varredura e bisseção."""
        grid = [-0.95 + step * 0.05 for step in range(1, 220)]
        anterior_r = -0.95
        anterior_vpl = cls._calcular_vpl_para_taxa(fluxos, anterior_r)

        for taxa_r in grid:
            atual_vpl = cls._calcular_vpl_para_taxa(fluxos, taxa_r)
            if abs(atual_vpl) < 1e-7:
                return round(taxa_r * 100.0, 2)
            if anterior_vpl * atual_vpl < 0:
                return round(cls._bissecao_tir(fluxos, anterior_r, taxa_r) * 100.0, 2)
            anterior_r, anterior_vpl = taxa_r, atual_vpl
        return None

    @classmethod
    def _bissecao_tir(cls, fluxos: list[float], low: float, high: float) -> float:
        """Refina a raiz da TIR no intervalo [low, high]."""
        vpl_low = cls._calcular_vpl_para_taxa(fluxos, low)
        for _ in range(80):
            mid = (low + high) / 2.0
            vpl_mid = cls._calcular_vpl_para_taxa(fluxos, mid)
            if abs(vpl_mid) < 1e-9 or (high - low) < 1e-9:
                return mid
            if vpl_low * vpl_mid <= 0:
                high = mid
            else:
                low, vpl_low = mid, vpl_mid
        return (low + high) / 2.0

    @staticmethod
    def _calcular_tirm(fluxos: list[float], tma_decimal: float) -> float | None:
        """Calcula a TIR Modificada (reinvestimento e financiamento à TMA)."""
        horizon = len(fluxos) - 1
        if horizon <= 0:
            return None

        pv_negativos = sum(
            abs(cf) / ((1.0 + tma_decimal) ** ano)
            for ano, cf in enumerate(fluxos)
            if cf < 0
        )
        fv_positivos = sum(
            cf * ((1.0 + tma_decimal) ** (horizon - ano))
            for ano, cf in enumerate(fluxos)
            if cf > 0
        )
        if pv_negativos <= 0 or fv_positivos <= 0:
            return None

        tirm = (math.pow(fv_positivos / pv_negativos, 1.0 / horizon) - 1.0) * 100.0
        return round(tirm, 2)

    @staticmethod
    def _calcular_evolucao_e_paybacks(
        fluxos: list[float],
        tma_decimal: float,
    ) -> tuple[list[FluxoAnoDetalheOutput], float | None, float | None]:
        """Gera a tabela anual e determina Payback Simples e Payback Descontado."""
        evolucao: list[FluxoAnoDetalheOutput] = []
        saldo_simples = 0.0
        saldo_descontado = 0.0
        payback_simples: float | None = None
        payback_descontado: float | None = None

        for ano, fluxo_nominal in enumerate(fluxos):
            fator = (1.0 + tma_decimal) ** ano
            fluxo_descontado = fluxo_nominal / fator
            anterior_simples = saldo_simples
            anterior_descontado = saldo_descontado
            saldo_simples += fluxo_nominal
            saldo_descontado += fluxo_descontado

            if ano > 0 and payback_simples is None and anterior_simples < 0 <= saldo_simples and fluxo_nominal > 0:
                payback_simples = round((ano - 1) + abs(anterior_simples) / fluxo_nominal, 2)
            if ano > 0 and payback_descontado is None and anterior_descontado < 0 <= saldo_descontado and fluxo_descontado > 0:
                payback_descontado = round((ano - 1) + abs(anterior_descontado) / fluxo_descontado, 2)

            evolucao.append(
                FluxoAnoDetalheOutput(
                    ano=ano,
                    fluxo_nominal=round(fluxo_nominal, 2),
                    fator_desconto=round(fator, 4),
                    fluxo_descontado=round(fluxo_descontado, 2),
                    saldo_acumulado_simples=round(saldo_simples, 2),
                    saldo_acumulado_descontado=round(saldo_descontado, 2),
                )
            )
        return evolucao, payback_simples, payback_descontado

    @staticmethod
    def _classificar_decisoes(
        vpl: float,
        tir_aa: float | None,
        contexto: tuple[float, float, float | None, bool],
    ) -> tuple[str, str, str, str]:
        """Classifica ACEITAR/REJEITAR por critério e define o veredito final."""
        tma_aa, prazo_max, payback_desc, fluxo_nao_conv = contexto
        decisao_vpl = "ACEITAR" if vpl > TOLERANCIA_MOEDA else ("REJEITAR" if vpl < -TOLERANCIA_MOEDA else "INDIFERENTE")

        if fluxo_nao_conv or tir_aa is None:
            decisao_tir = "INCONCLUSIVO"
        elif tir_aa > tma_aa + TOLERANCIA_TAXA:
            decisao_tir = "ACEITAR"
        elif tir_aa < tma_aa - TOLERANCIA_TAXA:
            decisao_tir = "REJEITAR"
        else:
            decisao_tir = "INDIFERENTE"

        decisao_payback = "ACEITAR" if (payback_desc is not None and payback_desc <= prazo_max) else "REJEITAR"

        if decisao_vpl == "REJEITAR":
            veredito = "INVIAVEL"
        elif decisao_vpl == "ACEITAR" and decisao_payback == "REJEITAR":
            veredito = "ATENCAO_LIQUIDEZ"
        elif decisao_vpl == "ACEITAR":
            veredito = "VIAVEL"
        else:
            veredito = "ATENCAO_LIQUIDEZ" if decisao_payback == "REJEITAR" else "INVIAVEL"
        return decisao_vpl, decisao_tir, decisao_payback, veredito

    @staticmethod
    def _gerar_resumo_executivo(
        nome: str,
        vpl: float,
        veredito: str,
    ) -> str:
        """Redige explicação objetiva da geração ou destruição de valor."""
        if veredito == "VIAVEL":
            return f"'{nome}' gera R$ {vpl:,.2f} em riqueza acima da TMA e recupera o capital dentro do prazo."
        if veredito == "ATENCAO_LIQUIDEZ":
            return f"'{nome}' gera valor (VPL positivo de R$ {vpl:,.2f}), mas ultrapassa o payback máximo definido."
        return f"'{nome}' destrói R$ {abs(vpl):,.2f} frente ao custo de oportunidade (TMA)."

    def calcular_tma(self, dados: TmaCalculoInput) -> TmaCalculoOutput:
        """
        Calcula a Taxa Mínima de Atratividade (TMA) ponderando capital próprio,
        financiamento rural (Plano Safra) e prêmio de risco do negócio.

        Args:
            dados: Percentuais e custos anuais de capital próprio, financiamento e risco.

        Returns:
            TmaCalculoOutput: TMA composta final e memória resumida.
        """
        soma_pesos = dados.percentual_capital_proprio + dados.percentual_financiamento
        if soma_pesos > 0:
            custo_ponderado = (
                dados.percentual_capital_proprio * dados.custo_oportunidade_proprio_aa
                + dados.percentual_financiamento * dados.taxa_financiamento_aa
            ) / soma_pesos
        else:
            custo_ponderado = 0.0

        tma = custo_ponderado + dados.premio_risco_agro_aa
        detalhamento = (
            f"Custo ponderado de capital ({custo_ponderado:.2f}% a.a.) + "
            f"prêmio de risco ({dados.premio_risco_agro_aa:.2f}% a.a.) = {tma:.2f}% a.a."
        )
        return TmaCalculoOutput(
            tma_calculada_aa=round(tma, 2),
            custo_ponderado_capital_aa=round(custo_ponderado, 2),
            premio_risco_agro_aa=round(dados.premio_risco_agro_aa, 2),
            detalhamento=detalhamento,
        )

    def analisar_projeto(self, projeto: ProjetoInvestimentoInput) -> ProjetoViabilidadeOutput:
        """
        Executa análise completa de viabilidade financeira de um investimento agro.

        Args:
            projeto: Fluxos nominais, investimento inicial, TMA e prazo máximo.

        Returns:
            ProjetoViabilidadeOutput: VPL, TIR, TIRM, Paybacks, decisões e evolução anual.
        """
        fluxos = self._montar_serie_fluxos(projeto)
        tma_decimal = float(projeto.tma_aa) / 100.0
        evolucao, payback_simples, payback_descontado = self._calcular_evolucao_e_paybacks(fluxos, tma_decimal)

        vpl = round(evolucao[-1].saldo_acumulado_descontado, 2)
        fluxo_nao_conv = self._contar_trocas_sinal(fluxos) > 1
        tir_aa = self._calcular_tir(fluxos)
        tirm_aa = self._calcular_tirm(fluxos, tma_decimal)
        margem_tir = round(tir_aa - projeto.tma_aa, 2) if tir_aa is not None else None
        indice_lucratividade = round((vpl + projeto.investimento_inicial) / projeto.investimento_inicial, 3)

        decisao_vpl, decisao_tir, decisao_payback, veredito = self._classificar_decisoes(
            vpl,
            tir_aa,
            (projeto.tma_aa, projeto.prazo_maximo_aceitavel_anos, payback_descontado, fluxo_nao_conv),
        )

        return ProjetoViabilidadeOutput(
            id=projeto.id,
            nome=projeto.nome,
            categoria=projeto.categoria,
            investimento_inicial=round(projeto.investimento_inicial, 2),
            tma_aa=round(projeto.tma_aa, 2),
            prazo_maximo_aceitavel_anos=round(projeto.prazo_maximo_aceitavel_anos, 2),
            vpl=vpl,
            tir_aa=tir_aa,
            tirm_aa=tirm_aa,
            margem_seguranca_tir_pp=margem_tir,
            payback_simples_anos=payback_simples,
            payback_descontado_anos=payback_descontado,
            indice_lucratividade=indice_lucratividade,
            fluxo_nao_convencional=fluxo_nao_conv,
            decisao_vpl=decisao_vpl,  # type: ignore[arg-type]
            decisao_tir=decisao_tir,  # type: ignore[arg-type]
            decisao_payback=decisao_payback,  # type: ignore[arg-type]
            veredito_final=veredito,  # type: ignore[arg-type]
            resumo_executivo=self._gerar_resumo_executivo(projeto.nome, vpl, veredito),
            evolucao_anual=evolucao,
        )

    def comparar_projetos(self, payload: ComparativoViabilidadeInput) -> ComparativoViabilidadeOutput:
        """
        Analisa múltiplos projetos lado a lado e recomenda a opção com maior geração de riqueza (VPL).

        Args:
            payload: Lista de projetos e composição opcional da TMA.

        Returns:
            ComparativoViabilidadeOutput: Resultados individuais, vencedor e justificativa técnica.
        """
        tma_calculada = self.calcular_tma(payload.tma_composicao) if payload.tma_composicao else None
        resultados = [self.analisar_projeto(projeto) for projeto in payload.projetos]
        viaveis = [res for res in resultados if res.vpl > TOLERANCIA_MOEDA]

        if not viaveis:
            return ComparativoViabilidadeOutput(
                tma_calculada=tma_calculada,
                resultados=resultados,
                projeto_recomendado_id=None,
                justificativa_comparativa="Nenhum projeto apresentou VPL positivo acima da TMA informada.",
            )

        melhor = max(viaveis, key=lambda item: item.vpl)
        justificativa = (
            f"Recomendado '{melhor.nome}' pelo maior VPL absoluto (R$ {melhor.vpl:,.2f}), "
            "critério soberano para criação de riqueza entre alternativas de escalas distintas."
        )
        return ComparativoViabilidadeOutput(
            tma_calculada=tma_calculada,
            resultados=resultados,
            projeto_recomendado_id=melhor.id,
            justificativa_comparativa=justificativa,
        )

    @staticmethod
    def _taxa_mensal_equivalente(taxa_anual_percentual: float) -> float:
        """Converte taxa efetiva anual (%) para taxa mensal decimal."""
        taxa = max(0.0, float(taxa_anual_percentual)) / 100.0
        return (1.0 + taxa) ** (1.0 / 12.0) - 1.0

    @classmethod
    def analisar_decisao_reativa_fluxo(
        cls,
        periodos: list[FluxoCaixaPeriodo],
        parametros: tuple[float, float, float],
    ) -> AnaliseDecisaoReativa:
        """
        Diagnostica vales futuros de capital de giro e calcula o custo da decisão reativa
        (juros emergenciais vs. crédito planejado via Plano Safra).

        Args:
            periodos: Lista ordenada de períodos mensais com `saldo_acumulado_projetado`.
            parametros: Tupla `(saldo_inicial, taxa_credito_planejado_aa, taxa_credito_reativo_aa)`.

        Returns:
            AnaliseDecisaoReativa: Diagnóstico de déficit, economia potencial e recomendação.
        """
        saldo_inicial, taxa_planejado_aa, taxa_reativo_aa = parametros
        meses_deficit = [p for p in periodos if p.saldo_acumulado_projetado < 0]

        if not meses_deficit:
            return AnaliseDecisaoReativa(
                possui_vale_caixa=False,
                pior_vale_valor=0.0,
                mes_pior_vale=None,
                primeiro_mes_vale=None,
                meses_em_deficit=0,
                dias_antecedencia_primeiro_vale=None,
                saldo_inicial_considerado=round(saldo_inicial, 2),
                taxa_credito_planejado_aa=round(taxa_planejado_aa, 2),
                taxa_credito_reativo_aa=round(taxa_reativo_aa, 2),
                custo_juros_planejado=0.0,
                custo_juros_reativo=0.0,
                custo_decisao_reativa=0.0,
                nivel_risco="SAUDAVEL",
                recomendacao=(
                    "Fluxo de caixa projetado positivo em todo o horizonte analisado, "
                    "sem necessidade emergencial de capital de giro."
                ),
            )

        r_plan = cls._taxa_mensal_equivalente(taxa_planejado_aa)
        r_reat = cls._taxa_mensal_equivalente(taxa_reativo_aa)
        custo_plan = sum(abs(p.saldo_acumulado_projetado) * r_plan for p in meses_deficit)
        custo_reat = sum(abs(p.saldo_acumulado_projetado) * r_reat for p in meses_deficit)
        custo_reativa = max(0.0, custo_reat - custo_plan)

        primeiro = meses_deficit[0]
        pior = min(meses_deficit, key=lambda item: item.saldo_acumulado_projetado)
        pior_vale = round(abs(pior.saldo_acumulado_projetado), 2)
        dias_antecedencia = (primeiro.periodo - date.today()).days
        nivel_risco = "CRITICO" if dias_antecedencia <= 30 else "ALERTA"

        if dias_antecedencia <= 0:
            recomendacao = (
                f"Déficit imediato detectado em {primeiro.periodo.strftime('%m/%Y')} "
                f"(pior vale de R$ {pior_vale:,.2f} em {pior.periodo.strftime('%m/%Y')}). "
                f"Estruturar linha de crédito planejada evita pagar R$ {custo_reativa:,.2f} a mais em juros reativos."
            )
        else:
            recomendacao = (
                f"Vale de capital de giro previsto em {dias_antecedencia} dias ({primeiro.periodo.strftime('%m/%Y')}), "
                f"atingindo R$ {pior_vale:,.2f} em {pior.periodo.strftime('%m/%Y')}. "
                f"Planejar captação rural preserva R$ {custo_reativa:,.2f} frente ao crédito emergencial."
            )

        return AnaliseDecisaoReativa(
            possui_vale_caixa=True,
            pior_vale_valor=pior_vale,
            mes_pior_vale=pior.periodo,
            primeiro_mes_vale=primeiro.periodo,
            meses_em_deficit=len(meses_deficit),
            dias_antecedencia_primeiro_vale=dias_antecedencia,
            saldo_inicial_considerado=round(saldo_inicial, 2),
            taxa_credito_planejado_aa=round(taxa_planejado_aa, 2),
            taxa_credito_reativo_aa=round(taxa_reativo_aa, 2),
            custo_juros_planejado=round(custo_plan, 2),
            custo_juros_reativo=round(custo_reat, 2),
            custo_decisao_reativa=round(custo_reativa, 2),
            nivel_risco=nivel_risco,
            recomendacao=recomendacao,
        )

    @staticmethod
    def calcular_preco_equilibrio_tma(dados: PrecoEquilibrioTmaInput) -> PrecoEquilibrioTmaOutput:
        """
        Calcula o preço mínimo da saca para empatar contabilmente e para remunerar a TMA
        (VPL = 0), gerando análise de sensibilidade cambial e recomendação de Hedge.

        Args:
            dados: Custo total, produção estimada, TMA anual, ciclo em meses, preço e câmbio.

        Returns:
            PrecoEquilibrioTmaOutput: Equilíbrio contábil vs TMA, VPL atual e cenários de câmbio.
        """
        fator = (1.0 + dados.tma_aa / 100.0) ** (dados.prazo_ciclo_meses / 12.0)
        preco_contabil = dados.custo_total_safra / dados.producao_estimada_sc
        preco_tma = (dados.custo_total_safra * fator) / dados.producao_estimada_sc
        premio_capital = max(0.0, preco_tma - preco_contabil)
        vpl_atual = (dados.producao_estimada_sc * dados.preco_mercado_atual_sc) / fator - dados.custo_total_safra
        margem_tma = dados.preco_mercado_atual_sc - preco_tma

        if dados.preco_mercado_atual_sc >= preco_tma:
            acao = "TRAVAR_MARGEM"
            mensagem = (
                f"Preço atual (R$ {dados.preco_mercado_atual_sc:,.2f}/sc) supera o equilíbrio por TMA "
                f"(R$ {preco_tma:,.2f}/sc). Travar parcela via Hedge garante VPL positivo "
                f"(R$ {vpl_atual:,.2f}; cobertura atual: {dados.percentual_ja_travado:.0f}%)."
            )
        elif dados.preco_mercado_atual_sc >= preco_contabil:
            acao = "ATENCAO_TMA"
            mensagem = (
                f"Preço atual cobre o custo operacional (R$ {preco_contabil:,.2f}/sc), "
                f"mas está R$ {abs(margem_tma):,.2f}/sc abaixo da TMA (VPL = R$ {vpl_atual:,.2f}). "
                "Monitore dólar/prêmio antes de travar grandes volumes."
            )
        else:
            acao = "DEFESA_CAIXA"
            mensagem = (
                f"Alerta: preço atual abaixo do ponto de equilíbrio contábil (R$ {preco_contabil:,.2f}/sc). "
                "Priorize defesa de caixa e proteção contra quedas adicionais."
            )

        cenarios: list[CenarioSensibilidadeCambio] = []
        for rotulo, multiplicador in (("Dólar -10%", 0.9), ("Base", 1.0), ("Dólar +10%", 1.1)):
            cambio_cenario = round(dados.taxa_cambio_base * multiplicador, 2)
            preco_cenario = round(dados.preco_mercado_atual_sc * multiplicador, 2)
            vpl_cenario = round(
                (dados.producao_estimada_sc * preco_cenario) / fator - dados.custo_total_safra,
                2,
            )
            cenarios.append(
                CenarioSensibilidadeCambio(
                    cenario=rotulo,
                    taxa_cambio=cambio_cenario,
                    preco_estimado_sc=preco_cenario,
                    vpl_safra=vpl_cenario,
                    supera_tma=vpl_cenario >= 0.0,
                )
            )

        return PrecoEquilibrioTmaOutput(
            preco_equilibrio_contabil_sc=round(preco_contabil, 2),
            preco_equilibrio_tma_sc=round(preco_tma, 2),
            premio_custo_capital_sc=round(premio_capital, 2),
            fator_capitalizacao_tma=round(fator, 4),
            vpl_safra_atual=round(vpl_atual, 2),
            margem_sobre_tma_sc=round(margem_tma, 2),
            acao_hedge_recomendada=acao,  # type: ignore[arg-type]
            mensagem_recomendacao=mensagem,
            sensibilidade_cambio=cenarios,
        )

    @staticmethod
    def listar_templates_agro() -> list[TemplateProjetoAgroOutput]:
        """
        Retorna cenários clássicos de investimentos rurais para simulação rápida.

        Returns:
            list[TemplateProjetoAgroOutput]: Templates inspirados em decisões reais do agronegócio.
        """
        return [
            TemplateProjetoAgroOutput(
                id="tpl-pivo",
                nome="Novo Pivô Central (100 ha)",
                categoria="IRRIGACAO",
                descricao="Implantação de pivô para ganho de produtividade e 3ª safra irrigada.",
                investimento_inicial=1_150_000.0,
                tma_sugerida_aa=11.5,
                prazo_maximo_aceitavel_anos=4.5,
                fluxos_caixa_anuais=[340_000.0, 380_000.0, 410_000.0, 430_000.0, 450_000.0],
                valor_residual_final=220_000.0,
            ),
            TemplateProjetoAgroOutput(
                id="tpl-silo",
                nome="Expansão de Silo / Armazenagem Própria",
                categoria="ARMAZENAGEM",
                descricao="Redução de fretes na pico de safra e captura de prêmio na entressafra.",
                investimento_inicial=1_800_000.0,
                tma_sugerida_aa=11.5,
                prazo_maximo_aceitavel_anos=5.0,
                fluxos_caixa_anuais=[420_000.0, 480_000.0, 520_000.0, 560_000.0, 600_000.0],
                valor_residual_final=550_000.0,
            ),
            TemplateProjetoAgroOutput(
                id="tpl-maquinario",
                nome="Aquisição de Pulverizador Autopropelido",
                categoria="MAQUINARIO",
                descricao="Redução de perda por atraso operacional e economia em terceirização.",
                investimento_inicial=920_000.0,
                tma_sugerida_aa=12.0,
                prazo_maximo_aceitavel_anos=4.0,
                fluxos_caixa_anuais=[290_000.0, 310_000.0, 310_000.0, 290_000.0, 270_000.0],
                valor_residual_final=320_000.0,
            ),
            TemplateProjetoAgroOutput(
                id="tpl-expansao",
                nome="Expansão / Abertura de Área (200 ha)",
                categoria="EXPANSAO_AREA",
                descricao="Correção de solo, calcário, infraestrutura e formação de lavoura.",
                investimento_inicial=840_000.0,
                tma_sugerida_aa=12.5,
                prazo_maximo_aceitavel_anos=4.0,
                fluxos_caixa_anuais=[180_000.0, 280_000.0, 350_000.0, 390_000.0, 420_000.0],
                valor_residual_final=180_000.0,
            ),
        ]
