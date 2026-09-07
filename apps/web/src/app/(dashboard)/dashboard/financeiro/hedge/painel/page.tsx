import { apiFetchServer } from "@/lib/api-server";
import { PainelClient } from "./PainelClient";
import { HedgeExposicao, HedgePosicao } from "../types";
import type { SafraOption } from "../contratos/commodity-resolution";

type PageSearchParams = {
    safra_id?: string | string[];
};

function firstParam(value: string | string[] | undefined): string {
    return Array.isArray(value) ? value[0] : value || "";
}

export default async function PainelPage({ searchParams }: { searchParams?: PageSearchParams }) {
    let exposicao: HedgeExposicao | null = null;
    let posicao: HedgePosicao | null = null;
    let safras: SafraOption[] = [];

    const safraId = firstParam(searchParams?.safra_id);
    const qs = safraId ? `?safra_id=${safraId}` : "";

    try {
        const [exposicaoRes, posicaoRes, safrasRes] = await Promise.allSettled([
            apiFetchServer<HedgeExposicao>(`/financeiro/hedge/exposicao${qs}`),
            apiFetchServer<HedgePosicao>(`/financeiro/hedge/posicao${qs}`),
            apiFetchServer<SafraOption[]>("/safras")
        ]);

        if (exposicaoRes.status === "fulfilled") exposicao = exposicaoRes.value;
        if (posicaoRes.status === "fulfilled") posicao = posicaoRes.value;
        if (safrasRes.status === "fulfilled") safras = safrasRes.value;
    } catch (e) {
        // Ignora e deixa o Client component resolver
    }

    return (
        <PainelClient 
            initialExposicao={exposicao}
            initialPosicao={posicao}
            safras={safras}
            initialSafraId={safraId}
        />
    );
}
