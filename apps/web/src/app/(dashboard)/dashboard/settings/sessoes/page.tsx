import { apiFetchServer } from "@/lib/api-server";
import { SessoesClient, Sessao } from "./SessoesClient";

export default async function SessoesPage() {
    let sessoes: Sessao[] = [];
    let team: Sessao[] | undefined = undefined;

    try {
        // Dispara requisições em paralelo para evitar waterfalls se o usuário tiver acesso a team
        const [sessoesRes, teamRes] = await Promise.allSettled([
            apiFetchServer<Sessao[]>("/auth/sessions/me"),
            apiFetchServer<Sessao[]>("/auth/sessions/team"),
        ]);

        if (sessoesRes.status === "fulfilled") {
            sessoes = sessoesRes.value;
        }

        if (teamRes.status === "fulfilled") {
            team = teamRes.value;
        }
    } catch (e) {
        // Erro global se algo falhar muito, mas Promise.allSettled absorve falhas individuais.
    }

    return <SessoesClient initialSessoes={sessoes} initialTeam={team} />;
}
