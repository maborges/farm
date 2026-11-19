export interface CustoBreakdown {
    categoria: string;
    valor_total: number;
    valor_por_ha: number;
    percentual: number;
}

export interface ResumoCustos {
    safra_id: string;
    area_total_ha: number;
    custo_total_realizado: number;
    custo_realizado_por_ha: number;
    orcamento_previsto_total: number | null;
    desvio_orcamento_pct: number | null;
    fonte_orcamento_previsto: string;
    usou_fallback_orcamento: boolean;
    fonte_apuracao: string;
    usou_fallback_operacional: boolean;
    breakdown: CustoBreakdown[];
}

export interface SafraKPI {
    safra_id: string;
    cultura: string;
    ano_safra: string;
    area_ha: number;
    custo_previsto_ha: number | null;
    custo_realizado_ha: number | null;
}

export interface CampanhasResponse {
    safras: SafraKPI[];
}

export interface FonteResumoCustosBadge {
    variant: "success" | "warning";
    label: string;
    showFallbackHint: boolean;
}

/**
 * Resolve o identificador efetivo da safra a consultar, evitando queries
 * inválidas quando não há safras ou o item selecionado não está mais na lista.
 */
export function resolveSafraSelecionadaId(
    safras: readonly SafraKPI[],
    selectedSafraId: string,
): string | null {
    if (!safras || safras.length === 0) {
        return null;
    }
    if (selectedSafraId !== "all") {
        const encontrada = safras.find((item) => item.safra_id === selectedSafraId);
        if (encontrada) {
            return encontrada.safra_id;
        }
    }
    return safras[0].safra_id;
}

/**
 * Deriva o selo e a mensagem da fonte de apuração somente quando o resumo
 * da safra está carregado e definido.
 */
export function resolveFonteResumoCustos(
    relatorio: ResumoCustos | null | undefined,
): FonteResumoCustosBadge | null {
    if (!relatorio) {
        return null;
    }
    const isOficial =
        relatorio.fonte_apuracao === "COST_ALLOCATION" && !relatorio.usou_fallback_operacional;
    return {
        variant: isOficial ? "success" : "warning",
        label: relatorio.usou_fallback_operacional
            ? "Fallback operacional"
            : "Apropriação econômica oficial",
        showFallbackHint: Boolean(relatorio.usou_fallback_operacional),
    };
}

/**
 * Retorna uma cópia ordenada por maior custo total sem mutar o array em cache.
 */
export function sortBreakdownCustos(
    breakdown: readonly CustoBreakdown[] | null | undefined,
): CustoBreakdown[] {
    if (!breakdown || breakdown.length === 0) {
        return [];
    }
    return [...breakdown].sort((a, b) => b.valor_total - a.valor_total);
}
