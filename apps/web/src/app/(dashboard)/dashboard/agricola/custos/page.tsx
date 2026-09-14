import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { CustosClient, Safra, ResumosCustos } from "./CustosClient";

export default async function CustosPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    let safras: Safra[] = [];
    let initialCustos: ResumosCustos | null = null;

    try {
        safras = await apiFetchServer<Safra[]>(`/safras/${qs}`);
        if (safras && safras.length > 0) {
            initialCustos = await apiFetchServer<ResumosCustos>(`/custos/safra/${safras[0].id}`);
        }
    } catch (e) {
        // Silencia erro e deixa o client tentar / lidar com loading state
    }

    return (
        <CustosClient 
            initialSafras={safras}
            initialCustos={initialCustos}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
