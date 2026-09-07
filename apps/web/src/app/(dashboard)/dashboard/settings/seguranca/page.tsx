import { apiFetchServer } from "@/lib/api-server";
import { SegurancaClient, SegurancaConfig } from "./SegurancaClient";

export default async function SegurancaPage() {
    let initialConfig: SegurancaConfig | null = null;
    try {
        initialConfig = await apiFetchServer<SegurancaConfig>("/config/seguranca");
    } catch (e) {
        // Silencia e deixa o Client tratar o erro/loader
    }

    return <SegurancaClient initialConfig={initialConfig} />;
}
