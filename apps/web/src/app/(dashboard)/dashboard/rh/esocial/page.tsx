import { apiFetchServer } from "@/lib/api-server";
import { EsocialClient, EsocialEvento } from "./EsocialClient";

export default async function RhEsocialPage() {
    const eventos = await apiFetchServer<EsocialEvento[]>("/rh/esocial/eventos");
    return <EsocialClient initialData={eventos} />;
}
