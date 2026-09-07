import { cookies } from "next/headers";
import { apiFetchServer } from "@/lib/api-server";
import { CustosClient, CentroCustoResponse } from "./CustosClient";

function defaultRange() {
    const now = new Date();
    const inicio = new Date(now.getFullYear(), now.getMonth(), 1);
    const fim = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return {
        data_inicio: inicio.toISOString().split("T")[0],
        data_fim: fim.toISOString().split("T")[0],
    };
}

export default async function CustosPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
    const { data_inicio, data_fim } = defaultRange();
    const qs = new URLSearchParams({ data_inicio, data_fim });
    if (activeFazendaId) qs.set("unidade_produtiva_id", activeFazendaId);

    let initialCustos: CentroCustoResponse | null = null;
    try {
        initialCustos = await apiFetchServer<CentroCustoResponse>(`/financeiro/custos/centro-custos?${qs.toString()}`);
    } catch {
        // deixa o client carregar caso o RSC falhe
    }

    return (
        <CustosClient
            initialCustos={initialCustos}
            initialDataInicio={data_inicio}
            initialDataFim={data_fim}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
