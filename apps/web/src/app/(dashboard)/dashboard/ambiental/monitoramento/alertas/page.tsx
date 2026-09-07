import { apiFetchServer } from "@/lib/api-server";
import { AlertasClient, Alerta } from "./AlertasClient";

export default async function AlertasDesmatamentoPage() {
    // A página carrega inicialmente os alertas abertos, para ser rápido no SSR
    const alertasAbertos = await apiFetchServer<Alerta[]>("/ambiental/alertas?status=NOVO&status=EM_ANALISE");
    return <AlertasClient initialData={alertasAbertos} />;
}
