import { apiFetchServer } from "@/lib/api-server";
import { TiposOperacaoClient, TipoOperacao } from "./TiposOperacaoClient";

export default async function BackofficeTiposOperacaoPage() {
    const tipos = await apiFetchServer<TipoOperacao[]>("/operacoes/tipos");
    return <TiposOperacaoClient initialData={tipos} />;
}
