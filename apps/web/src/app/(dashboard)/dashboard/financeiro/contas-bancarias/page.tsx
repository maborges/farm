import { apiFetchServer } from "@/lib/api-server";
import { ContasBancariasClient, ContaBancaria } from "./ContasBancariasClient";

export default async function ContasBancariasPage() {
    let initialContas: ContaBancaria[] = [];
    try {
        initialContas = await apiFetchServer<ContaBancaria[]>("/financeiro/integracao/contas-bancarias");
    } catch (e) {
        // Ignora erro no servidor e deixa o client resolver
    }

    return <ContasBancariasClient initialContas={initialContas} />;
}
