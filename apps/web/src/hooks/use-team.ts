// hooks/use-team.ts
// Hook para gerenciar dados e operações da equipe

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import type { TeamMember, TeamStats, TeamInvite, TenantRoleProfile } from "@/types/global";

interface UseTeamResult {
    members: TeamMember[] | undefined;
    stats: TeamStats | undefined;
    invites: TeamInvite[] | undefined;
    roles: TenantRoleProfile[] | undefined;
    loading: boolean;
    error: Error | null;
    inviteMember: (data: { email: string; role_id: string; unidade_produtiva_ids?: string[] }) => Promise<void>;
    removeMember: (memberId: string) => Promise<void>;
    updateMemberRole: (memberId: string, roleId: string) => Promise<void>;
    cancelInvite: (inviteId: string) => Promise<void>;
    refetch: () => Promise<void>;
}

/**
 * Hook que gerencia dados e operações da equipe.
 * Inclui membros, estatísticas, convites e perfis.
 */
export function useTeam(): UseTeamResult {
    const queryClient = useQueryClient();
    const [error, setError] = useState<Error | null>(null);

    // Queries
    const { data: members, isLoading: membersLoading } = useQuery<TeamMember[]>({
        queryKey: ["team", "users"],
        queryFn: () => apiFetch("/team/users"),
    });

    const { data: stats, isLoading: statsLoading } = useQuery<TeamStats>({
        queryKey: ["team", "stats"],
        queryFn: () => apiFetch("/team/stats"),
    });

    const { data: invites } = useQuery<TeamInvite[]>({
        queryKey: ["team", "invites"],
        queryFn: () => apiFetch("/team/invites"),
    });

    const { data: roles } = useQuery<TenantRoleProfile[]>({
        queryKey: ["team", "roles"],
        queryFn: () => apiFetch("/team/roles"),
    });

    // Mutations
    const inviteMutation = useMutation({
        mutationFn: (data: { email: string; role_id: string; unidade_produtiva_ids?: string[] }) =>
            apiFetch("/team/invite", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            toast.success("Convite enviado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const removeMutation = useMutation({
        mutationFn: (memberId: string) =>
            apiFetch(`/team/users/${memberId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Membro removido com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const updateRoleMutation = useMutation({
        mutationFn: ({ memberId, roleId }: { memberId: string; roleId: string }) =>
            apiFetch(`/team/users/${memberId}/role`, {
                method: "PATCH",
                body: JSON.stringify({ role_id: roleId }),
            }),
        onSuccess: () => {
            toast.success("Perfil atualizado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const cancelInviteMutation = useMutation({
        mutationFn: (inviteId: string) =>
            apiFetch(`/team/invites/${inviteId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Convite cancelado!");
            queryClient.invalidateQueries({ queryKey: ["team", "invites"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const inviteMember = async (data: { email: string; role_id: string; unidade_produtiva_ids?: string[] }): Promise<void> => {
        await inviteMutation.mutateAsync(data);
    };

    const removeMember = async (memberId: string): Promise<void> => {
        await removeMutation.mutateAsync(memberId);
    };

    const updateMemberRole = async (memberId: string, roleId: string): Promise<void> => {
        await updateRoleMutation.mutateAsync({ memberId, roleId });
    };

    const cancelInvite = async (inviteId: string): Promise<void> => {
        await cancelInviteMutation.mutateAsync(inviteId);
    };

    return {
        members,
        stats,
        invites,
        roles,
        loading: membersLoading || statsLoading,
        error,
        inviteMember,
        removeMember,
        updateMemberRole,
        cancelInvite,
        refetch: async () => {
            await queryClient.invalidateQueries({ queryKey: ["team"] });
        },
    };
}
