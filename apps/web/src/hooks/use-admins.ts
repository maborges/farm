// hooks/use-admins.ts
// Hook para gerenciar dados e operações de administradores do backoffice

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import type { Admin, AdminStats, BackofficeRole } from "@/types/global";

interface CreateAdminData {
    nome: string;
    email: string;
    password: string;
    role: BackofficeRole;
}

interface UpdateAdminData {
    nome: string;
    role: BackofficeRole;
    ativo: boolean;
}

interface ResetPasswordData {
    nova_senha: string;
}

interface UseAdminsResult {
    admins: Admin[] | undefined;
    stats: AdminStats | undefined;
    loading: boolean;
    error: Error | null;
    createAdmin: (data: CreateAdminData) => Promise<void>;
    updateAdmin: (adminId: string, data: UpdateAdminData) => Promise<void>;
    deleteAdmin: (adminId: string) => Promise<void>;
    resetPassword: (adminId: string, data: ResetPasswordData) => Promise<void>;
    refetch: () => Promise<void>;
}

/**
 * Hook que gerencia dados e operações de administradores do backoffice.
 */
export function useAdmins(): UseAdminsResult {
    const queryClient = useQueryClient();
    const [error, setError] = useState<Error | null>(null);

    // Queries
    const { data: admins, isLoading: adminsLoading } = useQuery<Admin[]>({
        queryKey: ["backoffice", "admins"],
        queryFn: () => apiFetch("/backoffice/admins"),
    });

    const { data: stats } = useQuery<AdminStats>({
        queryKey: ["backoffice", "admins", "stats"],
        queryFn: () => apiFetch("/backoffice/admins/stats"),
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: CreateAdminData) =>
            apiFetch("/backoffice/admins", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Admin criado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ adminId, data }: { adminId: string; data: UpdateAdminData }) =>
            apiFetch(`/backoffice/admins/${adminId}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Admin atualizado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (adminId: string) =>
            apiFetch(`/backoffice/admins/${adminId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Admin removido com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const resetPasswordMutation = useMutation({
        mutationFn: ({ adminId, data }: { adminId: string; data: ResetPasswordData }) =>
            apiFetch(`/backoffice/admins/${adminId}/reset-password`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            toast.success("Senha resetada com sucesso!");
        },
        onError: (err: Error) => {
            setError(err);
            toast.error(err.message);
        },
    });

    const createAdmin = async (data: CreateAdminData): Promise<void> => {
        await createMutation.mutateAsync(data);
    };

    const updateAdmin = async (adminId: string, data: UpdateAdminData): Promise<void> => {
        await updateMutation.mutateAsync({ adminId, data });
    };

    const deleteAdmin = async (adminId: string): Promise<void> => {
        await deleteMutation.mutateAsync(adminId);
    };

    const resetPassword = async (adminId: string, data: ResetPasswordData): Promise<void> => {
        await resetPasswordMutation.mutateAsync({ adminId, data });
    };

    return {
        admins,
        stats,
        loading: adminsLoading,
        error,
        createAdmin,
        updateAdmin,
        deleteAdmin,
        resetPassword,
        refetch: async () => {
            await queryClient.invalidateQueries({ queryKey: ["backoffice", "admins"] });
            await queryClient.invalidateQueries({ queryKey: ["backoffice", "admins", "stats"] });
        },
    };
}
