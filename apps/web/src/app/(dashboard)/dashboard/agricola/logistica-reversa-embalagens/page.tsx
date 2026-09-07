import { apiFetchServer } from "@/lib/api-server";
import { LogisticaReversaClient } from "./LogisticaReversaClient";
import type { DevolucaoEmbalagem } from "@farm/zod-schemas";

export default async function LogisticaReversaPage() {
    let initialDevolucoes: DevolucaoEmbalagem[] = [];
    try {
        initialDevolucoes = await apiFetchServer<DevolucaoEmbalagem[]>("/agricola/logistica-reversa-embalagens");
    } catch (e) {
        // Ignora erro no servidor — Client refaz o fetch.
    }

    return <LogisticaReversaClient initialDevolucoes={initialDevolucoes} />;
}
