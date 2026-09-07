import { apiFetchServer } from "@/lib/api-server";
import { DevolucaoDetalheClient } from "./DevolucaoDetalheClient";
import type { DevolucaoEmbalagem } from "@farm/zod-schemas";

export default async function DevolucaoDetalhePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;

    let devolucao: DevolucaoEmbalagem | null = null;
    try {
        devolucao = await apiFetchServer<DevolucaoEmbalagem>(`/agricola/logistica-reversa-embalagens/${id}`);
    } catch (e) {
        // Ignora erro no servidor — Client refaz o fetch e trata o estado de erro.
    }

    return <DevolucaoDetalheClient id={id} initialDevolucao={devolucao} />;
}
