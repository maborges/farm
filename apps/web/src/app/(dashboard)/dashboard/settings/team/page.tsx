import { apiFetchServer } from "@/lib/api-server";
import { TeamClient } from "./TeamClient";
import type {
    TeamMember,
    TeamStats,
    TeamInvite,
    TenantRoleProfile,
    UnidadeProdutiva
} from "@/types/global";

export default async function TeamPage() {
    let initialStats: TeamStats | null = null;
    let initialMembers: TeamMember[] = [];
    let initialInvites: TeamInvite[] = [];
    let initialRoles: TenantRoleProfile[] = [];
    let initialFazendas: UnidadeProdutiva[] = [];

    try {
        const [statsRes, membersRes, invitesRes, rolesRes, fazendasRes] = await Promise.allSettled([
            apiFetchServer<TeamStats>("/team/stats"),
            apiFetchServer<TeamMember[]>("/team/users"),
            apiFetchServer<TeamInvite[]>("/team/invites"),
            apiFetchServer<TenantRoleProfile[]>("/team/roles"),
            apiFetchServer<UnidadeProdutiva[]>("/unidades-produtivas"),
        ]);

        if (statsRes.status === "fulfilled") initialStats = statsRes.value;
        if (membersRes.status === "fulfilled") initialMembers = membersRes.value;
        if (invitesRes.status === "fulfilled") initialInvites = invitesRes.value;
        if (rolesRes.status === "fulfilled") initialRoles = rolesRes.value;
        if (fazendasRes.status === "fulfilled") initialFazendas = fazendasRes.value;
    } catch (e) {
        // Ignora
    }

    return (
        <TeamClient 
            initialStats={initialStats}
            initialMembers={initialMembers}
            initialInvites={initialInvites}
            initialRoles={initialRoles}
            initialFazendas={initialFazendas}
        />
    );
}
