"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

export interface LoginTentativasInfo {
    email: string;
    tentativas_count: number;
    bloqueado: boolean;
    data_bloqueio: string | null;
    data_desbloqueio: string | null;
    ultima_tentativa: string | null;
    motivo_falha: string | null;
}

/* ─── Backoffice (Admin SaaS) ─── */

export function useLoginTentativas(email: string | null) {
    return useQuery<LoginTentativasInfo>({
        queryKey: ["login-tentativas", email],
        // Usuários sem falhas anteriores retornam 404; isso é normal para o badge de bloqueio.
        queryFn: () => apiFetch(`/backoffice/login/tentativas/${email}`, { suppressErrorLog: true }),
        enabled: !!email,
        retry: false,
    });
}

export function useDesbloquearUsuario() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (email: string) =>
            apiFetch("/backoffice/login/desbloquear", {
                method: "POST",
                body: JSON.stringify({ email }),
            }),
        onSuccess: (_data, email) => {
            toast.success(`Usuário ${email} desbloqueado com sucesso!`);
            queryClient.invalidateQueries({ queryKey: ["login-tentativas"] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "users"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });
}

export function useBloqueadosRecentes(limit = 50) {
    return useQuery<{ total: number; bloqueados: LoginTentativasInfo[] }>({
        queryKey: ["bloqueados-recentes", limit],
        queryFn: () => apiFetch(`/backoffice/login/bloqueados?limit=${limit}`),
    });
}

/* ─── Reset de senha de usuário global ─── */

export interface ResetPasswordResult {
    success: boolean;
    senha_temporaria: string;
    email_enviado: boolean;
    usuario_email: string;
}

export function useResetUserPassword() {
    const queryClient = useQueryClient();

    return useMutation<ResetPasswordResult, Error, { userId: string; enviarEmail: boolean }>({
        mutationFn: ({ userId, enviarEmail }) =>
            apiFetch(`/backoffice/users/${userId}/reset-password?enviar_email=${enviarEmail}`, {
                method: "POST",
            }),
        onSuccess: (data) => {
            toast.success(`Senha resetada para ${data.usuario_email}`);
            if (!data.email_enviado && data.senha_temporaria) {
                toast.info(`Senha temporária: ${data.senha_temporaria}`, { duration: 10000 });
            }
            queryClient.invalidateQueries({ queryKey: ["backoffice", "users"] });
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao resetar senha"),
    });
}

/* ─── Tenant (Gestor) ─── */

export function useTenantLoginTentativas(usuarioId: string | null) {
    return useQuery<LoginTentativasInfo>({
        queryKey: ["tenant-login-tentativas", usuarioId],
        // 404 é esperado quando o usuário nunca teve tentativa de login falha — não é erro.
        queryFn: () => apiFetch(`/auth/tenant/usuarios/${usuarioId}/login-tentativas`, { suppressErrorLog: true }),
        enabled: !!usuarioId,
        retry: false,
    });
}

export function useDesbloquearTenantUsuario() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (usuarioId: string) =>
            apiFetch(`/auth/tenant/usuarios/${usuarioId}/desbloquear-login`, {
                method: "POST",
            }),
        onSuccess: () => {
            toast.success("Usuário desbloqueado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["tenant-login-tentativas"] });
            queryClient.invalidateQueries({ queryKey: ["team", "users"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });
}
