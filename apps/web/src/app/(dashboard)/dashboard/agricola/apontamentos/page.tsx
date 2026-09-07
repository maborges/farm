import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { ApontamentosClient, Operacao, TipoOperacao } from "./ApontamentosClient";

export default async function ApontamentosPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;

    let initialOrdens: Operacao[] = [];
    let initialTipos: TipoOperacao[] = [];

    try {
        const [ordensRes, tiposRes] = await Promise.allSettled([
            activeFazendaId ? apiFetchServer<Operacao[]>(`/operacoes?unidade_produtiva_id=${activeFazendaId}`) : Promise.resolve([]),
            apiFetchServer<TipoOperacao[]>("/operacoes/tipos")
        ]);

        if (ordensRes.status === "fulfilled") {
            initialOrdens = ordensRes.value;
        }
        if (tiposRes.status === "fulfilled") {
            initialTipos = tiposRes.value;
        }
    } catch (e) {
        // Silencia erro e deixa o client tentar
    }

    return (
        <ApontamentosClient 
            initialOrdens={initialOrdens}
            initialTipos={initialTipos}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
