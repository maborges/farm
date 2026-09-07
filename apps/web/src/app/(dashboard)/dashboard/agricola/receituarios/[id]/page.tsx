import { apiFetchServer } from "@/lib/api-server";
import { ReceituarioDetalheClient } from "./ReceituarioDetalheClient";
import type { ReceituarioAgronomico } from "@farm/zod-schemas";

export default async function ReceituarioDetalhePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;

    let receituario: ReceituarioAgronomico | null = null;
    try {
        receituario = await apiFetchServer<ReceituarioAgronomico>(`/agricola/receituarios/${id}`);
    } catch (e) {
        // Ignora erro no servidor — Client refaz o fetch e trata o estado de erro.
    }

    return <ReceituarioDetalheClient id={id} initialReceituario={receituario} />;
}
