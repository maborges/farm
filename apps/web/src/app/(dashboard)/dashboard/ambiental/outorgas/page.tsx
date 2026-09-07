import { apiFetchServer } from "@/lib/api-server";
import { OutorgasClient, Outorga } from "./OutorgasClient";

export default async function OutorgasPage() {
    // Busca no servidor antes de enviar HTML ao cliente
    const outorgas = await apiFetchServer<Outorga[]>("/ambiental/outorgas");
    return <OutorgasClient initialData={outorgas} />;
}
