import { apiFetchServer } from "@/lib/api-server";
import { cookies } from "next/headers";
import { ReceituariosClient } from "./ReceituariosClient";
import type { ReceituarioAgronomico } from "@farm/zod-schemas";

export default async function ReceituariosPage() {
    const cookieStore = await cookies();
    const activeFazendaId = cookieStore.get("unidade_produtiva_id")?.value;

    let initialReceituarios: ReceituarioAgronomico[] = [];
    try {
        initialReceituarios = await apiFetchServer<ReceituarioAgronomico[]>("/agricola/receituarios");
    } catch (e) {
        // Ignora erro no servidor — Client refaz o fetch.
    }

    return (
        <ReceituariosClient
            initialReceituarios={initialReceituarios}
            initialActiveFazendaId={activeFazendaId}
        />
    );
}
