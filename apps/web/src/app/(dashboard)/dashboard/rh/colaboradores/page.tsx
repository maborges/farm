import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { ColaboradoresClient, Colaborador } from "./ColaboradoresClient";

export default async function ColaboradoresPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    let initialColaboradores: Colaborador[] = [];
    try {
        initialColaboradores = await apiFetchServer<Colaborador[]>(`/rh/colaboradores${qs}`);
    } catch (e) {
        // Ignora erro no servidor
    }

    return (
        <ColaboradoresClient 
            initialColaboradores={initialColaboradores}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
