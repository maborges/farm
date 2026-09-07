"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import type { TenantCustomPermissions } from "@/types/global";

interface MinhaPermissaoResponse {
    perfil_nome: string | null;
    permissoes: TenantCustomPermissions;
    origem: "fazenda" | "tenant";
}

/**
 * Re-sincroniza as permissões do usuário sempre que a UP ativa muda.
 *
 * O `custom_permissions` da sessão só é carregado no login (perfil padrão do
 * tenant) — se a UP ativa tiver um override de perfil (`perfil_fazenda_id`),
 * o menu ficaria com as permissões erradas até um novo login. Este componente
 * busca a permissão efetiva para a UP atual e atualiza a sessão sem exigir
 * relogin, da mesma forma que FazendasSync mantém a lista de UPs em dia.
 */
export function FazendaPermissionSync() {
    const activeFazendaId = useAppStore((s) => s.activeFazendaId);
    const tenantId = useAppStore((s) => s.tenant?.id);
    const token = useAppStore((s) => s.token);
    const isOwner = useAppStore((s) => s.user?.tenant_role === "owner");
    const setCustomPermissions = useAppStore((s) => s.setCustomPermissions);
    const hasHydrated = useAppStore((s) => s._hasHydrated);

    const { data } = useQuery<MinhaPermissaoResponse>({
        queryKey: ["minhas-permissoes", tenantId, activeFazendaId],
        queryFn: () =>
            apiFetch(`/team/me/permissoes${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`, {
                suppressErrorLog: true,
            }),
        enabled: hasHydrated && !!token && !!tenantId && !isOwner,
        staleTime: 0,
        retry: false,
    });

    useEffect(() => {
        if (data) {
            setCustomPermissions(data.permissoes);
        }
    }, [data, setCustomPermissions]);

    return null;
}
