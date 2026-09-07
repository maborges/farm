import { apiFetchServer } from "@/lib/api-server";
import { PessoasClient, Pessoa } from "./PessoasClient";

export default async function PessoasPage() {
    let initialPessoas: Pessoa[] = [];

    try {
        initialPessoas = await apiFetchServer<Pessoa[]>("/cadastros/pessoas");
    } catch (e) {
        // Ignora e deixa o Client component resolver
    }

    return <PessoasClient initialPessoas={initialPessoas} />;
}
