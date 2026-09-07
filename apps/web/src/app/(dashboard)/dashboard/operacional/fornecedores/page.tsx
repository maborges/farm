import { apiFetchServer } from "@/lib/api-server";
import { FornecedoresClient, Fornecedor } from "./FornecedoresClient";

export default async function FornecedoresPage() {
    let initialData: Fornecedor[] = [];
    try {
        initialData = await apiFetchServer<Fornecedor[]>("/compras/fornecedores");
    } catch (e) {
        // Ignora e deixa o Client side fazer fallback/mostrar erro
    }

    return <FornecedoresClient initialData={initialData} />;
}
