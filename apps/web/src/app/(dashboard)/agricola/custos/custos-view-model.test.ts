import { expect, test } from "@playwright/test";

import {
    resolveFonteResumoCustos,
    resolveSafraSelecionadaId,
    sortBreakdownCustos,
    type CustoBreakdown,
    type ResumoCustos,
    type SafraKPI,
} from "./custos-view-model";

const SAFRAS_FIXTURE: SafraKPI[] = [
    {
        safra_id: "safra-1",
        cultura: "Soja",
        ano_safra: "2025/2026",
        area_ha: 500,
        custo_previsto_ha: 4200,
        custo_realizado_ha: 3900,
    },
    {
        safra_id: "safra-2",
        cultura: "Milho",
        ano_safra: "2026",
        area_ha: 300,
        custo_previsto_ha: 3100,
        custo_realizado_ha: 2950,
    },
];

function criarResumo(overrides: Partial<ResumoCustos> = {}): ResumoCustos {
    return {
        safra_id: "safra-1",
        area_total_ha: 500,
        custo_total_realizado: 1950000,
        custo_realizado_por_ha: 3900,
        orcamento_previsto_total: 2100000,
        desvio_orcamento_pct: -7.14,
        fonte_orcamento_previsto: "ORCAMENTO_SAFRA",
        usou_fallback_orcamento: false,
        fonte_apuracao: "COST_ALLOCATION",
        usou_fallback_operacional: false,
        breakdown: [],
        ...overrides,
    };
}

test.describe("custos-view-model", () => {
    test("resolveFonteResumoCustos retorna null para undefined ou null sem lançar erro", () => {
        expect(resolveFonteResumoCustos(undefined)).toBeNull();
        expect(resolveFonteResumoCustos(null)).toBeNull();
    });

    test("resolveFonteResumoCustos retorna badge success para COST_ALLOCATION oficial", () => {
        const resumo = criarResumo({
            fonte_apuracao: "COST_ALLOCATION",
            usou_fallback_operacional: false,
        });

        expect(resolveFonteResumoCustos(resumo)).toEqual({
            variant: "success",
            label: "Apropriação econômica oficial",
            showFallbackHint: false,
        });
    });

    test("resolveFonteResumoCustos retorna badge warning para fallback operacional", () => {
        const resumo = criarResumo({
            fonte_apuracao: "OPERACIONAL_FALLBACK",
            usou_fallback_operacional: true,
        });

        expect(resolveFonteResumoCustos(resumo)).toEqual({
            variant: "warning",
            label: "Fallback operacional",
            showFallbackHint: true,
        });
    });

    test("sortBreakdownCustos ordena por valor_total decrescente sem mutar o array original", () => {
        const original: CustoBreakdown[] = [
            { categoria: "Sementes", valor_total: 10000, valor_por_ha: 100, percentual: 20 },
            { categoria: "Fertilizantes", valor_total: 35000, valor_por_ha: 350, percentual: 70 },
            { categoria: "Defensivos", valor_total: 5000, valor_por_ha: 50, percentual: 10 },
        ];
        const snapshot = [...original];

        const ordenado = sortBreakdownCustos(original);

        expect(ordenado.map((item) => item.categoria)).toEqual([
            "Fertilizantes",
            "Sementes",
            "Defensivos",
        ]);
        expect(original).toEqual(snapshot);
        expect(sortBreakdownCustos(undefined)).toEqual([]);
        expect(sortBreakdownCustos(null)).toEqual([]);
    });

    test("resolveSafraSelecionadaId trata lista vazia, 'all', id inexistente e seleção explícita", () => {
        expect(resolveSafraSelecionadaId([], "all")).toBeNull();
        expect(resolveSafraSelecionadaId([], "safra-1")).toBeNull();
        expect(resolveSafraSelecionadaId(SAFRAS_FIXTURE, "all")).toBe("safra-1");
        expect(resolveSafraSelecionadaId(SAFRAS_FIXTURE, "safra-inexistente")).toBe("safra-1");
        expect(resolveSafraSelecionadaId(SAFRAS_FIXTURE, "safra-2")).toBe("safra-2");
    });
});
