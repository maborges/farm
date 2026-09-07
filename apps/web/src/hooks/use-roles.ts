// hooks/use-roles.ts
// Hook para gerenciar dados e operações de perfis de acesso (roles)

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import type { TenantRoleProfile, PermissionLevel } from "@/types/global";

interface CreateRoleData {
    nome: string;
    descricao?: string;
    permissoes: Record<string, PermissionLevel>;
}

interface UseRolesResult {
    roles: TenantRoleProfile[] | undefined;
    systemRoles: TenantRoleProfile[] | undefined;
    customRoles: TenantRoleProfile[] | undefined;
    loading: boolean;
    error: Error | null;
    createRole: (data: CreateRoleData) => Promise<void>;
    updateRole: (roleId: string, data: CreateRoleData) => Promise<void>;
    deleteRole: (roleId: string) => Promise<void>;
    refetch: () => Promise<void>;
}

/**
 * Hook que gerencia dados e operações de perfis de acesso (roles).
 */
export function useRoles(): UseRolesResult {
    const queryClient = useQueryClient();
    const [error, setError] = useState<Error | null>(null);

    // Query
    const { data: roles, isLoading } = useQuery<TenantRoleProfile[]>({
        queryKey: ["team", "roles"],
        queryFn: () => apiFetch("/team/roles"),
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: CreateRoleData) =>
            apiFetch("/team/roles", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Perfil criado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ roleId, data }: { roleId: string; data: CreateRoleData }) =>
            apiFetch(`/team/roles/${roleId}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Perfil atualizado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (roleId: string) =>
            apiFetch(`/team/roles/${roleId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Perfil removido com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const systemRoles = roles?.filter((r) => !r.is_custom);
    const customRoles = roles?.filter((r) => r.is_custom);

    const createRole = async (data: CreateRoleData): Promise<void> => {
        await createMutation.mutateAsync(data);
    };

    const updateRole = async (roleId: string, data: CreateRoleData): Promise<void> => {
        await updateMutation.mutateAsync({ roleId, data });
    };

    const deleteRole = async (roleId: string): Promise<void> => {
        await deleteMutation.mutateAsync(roleId);
    };

    return {
        roles,
        systemRoles,
        customRoles,
        loading: isLoading,
        error,
        createRole,
        updateRole,
        deleteRole,
        refetch: async () => {
            await queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
        },
    };
}
