import { apiFetchServer } from "@/lib/api-server";
import { MtMClient } from "./MtMClient";
import { HedgePositionSnapshot } from "../types";
import type { SafraOption } from "../contratos/commodity-resolution";

type ContratoOption = {
    id: string;
    commodity: string;
    mes_vencimento: string | null;
    tipo_posicao: string;
};

type PageSearchParams = {
    safra_id?: string | string[];
};

function firstParam(value: string | string[] | undefined): string {
    return Array.isArray(value) ? value[0] : value || "";
}

export default async function MtMPage({ searchParams }: { searchParams?: PageSearchParams }) {
    let snapshots: HedgePositionSnapshot[] = [];
    let safras: SafraOption[] = [];
    let contratos: ContratoOption[] = [];

    const safraId = firstParam(searchParams?.safra_id);
    const safraParam = safraId ? `&safra_id=${safraId}` : "";

    try {
        const [snapshotsRes, safrasRes, contratosRes] = await Promise.allSettled([
            apiFetchServer<HedgePositionSnapshot[]>(`/financeiro/hedge/snapshots?limit=100${safraParam}`),
            apiFetchServer<SafraOption[]>("/safras"),
            apiFetchServer<ContratoOption[]>("/financeiro/hedge/contratos")
        ]);

        if (snapshotsRes.status === "fulfilled") snapshots = snapshotsRes.value;
        if (safrasRes.status === "fulfilled") safras = safrasRes.value;
        if (contratosRes.status === "fulfilled") contratos = contratosRes.value;
    } catch (e) {
        // Ignora erro inicial
    }

    return (
        <MtMClient 
            initialSnapshots={snapshots}
            safras={safras}
            contratos={contratos}
            initialSafraId={safraId}
        />
    );
}
