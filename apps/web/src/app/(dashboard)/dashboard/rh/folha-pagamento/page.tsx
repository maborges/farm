import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { FolhaPagamentoClient, DashboardRH, Diaria, Empreitada, Colaborador } from "./FolhaPagamentoClient";

export default async function FolhaPagamentoPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const [dashRes, diariasRes, empreitadasRes, colaboradoresRes] = await Promise.allSettled([
        apiFetchServer<DashboardRH>("/rh/dashboard"),
        apiFetchServer<Diaria[]>(`/rh/diarias${qs}`),
        apiFetchServer<Empreitada[]>(`/rh/empreitadas${qs}`),
        apiFetchServer<Colaborador[]>(`/rh/colaboradores${qs}`)
    ]);

    const fallbackDash: DashboardRH = {
        total_colaboradores_ativos: 0, total_diaristas: 0, total_empreiteiros: 0,
        gasto_diarias_mes: 0, gasto_empreitadas_mes: 0
    };

    return (
        <FolhaPagamentoClient 
            initialDash={dashRes.status === "fulfilled" ? dashRes.value : fallbackDash}
            initialDiarias={diariasRes.status === "fulfilled" ? diariasRes.value : []}
            initialEmpreitadas={empreitadasRes.status === "fulfilled" ? empreitadasRes.value : []}
            initialColaboradores={colaboradoresRes.status === "fulfilled" ? colaboradoresRes.value : []}
        />
    );
}
