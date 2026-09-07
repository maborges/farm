import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { PontoClient, Diaria, Colaborador } from "./PontoClient";

export default async function PontoPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    let initialDiarias: Diaria[] = [];
    let initialColaboradores: Colaborador[] = [];

    try {
        const [diariasRes, colabRes] = await Promise.allSettled([
            apiFetchServer<Diaria[]>(`/rh/diarias${qs}`),
            apiFetchServer<Colaborador[]>(`/rh/colaboradores${qs}`)
        ]);

        if (diariasRes.status === "fulfilled") initialDiarias = diariasRes.value;
        if (colabRes.status === "fulfilled") initialColaboradores = colabRes.value;
    } catch (e) {
        // Silenciar e deixar query client tratar erro
    }

    return (
        <PontoClient 
            initialDiarias={initialDiarias}
            initialColaboradores={initialColaboradores}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
