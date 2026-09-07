import { apiFetchServer } from "@/lib/api-server";
import { ManutencoesClient, OrdemServico, Maquinario } from "./ManutencoesClient";

export default async function ManutencoesPage() {
    let initialOrdens: OrdemServico[] = [];
    let initialMaquinarios: Maquinario[] = [];

    try {
        const [ordensRes, maqRes] = await Promise.allSettled([
            apiFetchServer<OrdemServico[]>("/oficina/os"),
            apiFetchServer<Maquinario[]>("/frota/")
        ]);

        if (ordensRes.status === "fulfilled") initialOrdens = ordensRes.value;
        if (maqRes.status === "fulfilled") initialMaquinarios = maqRes.value;
    } catch (e) {
        // Ignora e deixa o Client component resolver
    }

    return (
        <ManutencoesClient 
            initialOrdens={initialOrdens}
            initialMaquinarios={initialMaquinarios}
        />
    );
}
