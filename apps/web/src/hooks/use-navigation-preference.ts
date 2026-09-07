import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import type { NavigationMode, NavigationModeApi } from "@/types/global";
import { toast } from "sonner";

// Assumindo que a API aceita e retorna UPPERCASE, e o frontend usa lowercase
export function fromApiNavigationMode(mode?: "SIDEBAR" | "MEGA_MENU" | string): NavigationMode {
    if (mode === "MEGA_MENU") return "mega-menu";
    return "sidebar";
}

export function toApiNavigationMode(mode: NavigationMode): "SIDEBAR" | "MEGA_MENU" {
    if (mode === "mega-menu") return "MEGA_MENU";
    return "SIDEBAR";
}

export function useNavigationPreference() {
    const { user, setSession, token, tenant, grupos, unidadesProdutivasAutorizadas, availableTenants } = useAppStore();
    const queryClient = useQueryClient();

    // Fallback defensivo: se não tiver preferência, é 'sidebar'
    const mode = fromApiNavigationMode(user?.navigation_mode);

    const { mutate: setMode, isPending: isUpdating, error } = useMutation({
        mutationFn: async (newMode: NavigationMode) => {
            const apiMode = toApiNavigationMode(newMode);
            const response = await apiFetch<{ navigation_mode: string }>("/auth/me/preferences/navigation", {
                method: "PATCH",
                body: { navigation_mode: apiMode },
            });
            return response;
        },
        onMutate: async (newMode) => {
            // Cancelar queries relativas ao auth (se houvesse cache em React Query do profile)
            // No nosso caso o profile está no Zustand
            const previousMode = mode;
            
            // Cache otimista no Zustand
            if (user) {
                setSession(
                    token as string,
                    tenant,
                    { ...user, navigation_mode: toApiNavigationMode(newMode) },
                    grupos,
                    unidadesProdutivasAutorizadas,
                    availableTenants
                );
            }

            return { previousMode };
        },
        onSuccess: () => {
            toast.success("Modo de navegação atualizado.");
        },
        onError: (err, newMode, context) => {
            // Rollback
            if (user && context?.previousMode) {
                setSession(
                    token as string,
                    tenant,
                    { ...user, navigation_mode: toApiNavigationMode(context.previousMode) },
                    grupos,
                    unidadesProdutivasAutorizadas,
                    availableTenants
                );
            }
            toast.error("Não foi possível alterar o modo de navegação. Tente novamente.");
        },
        onSettled: () => {
            // Aqui normalmente invalidaríamos 'me', mas o estado primário já é Zustand
            // Se houver uma query 'auth-me' no rq, deve ser invalidada
            queryClient.invalidateQueries({ queryKey: ["auth-me"] });
        },
    });

    return {
        mode,
        isLoading: false, // Ler do Zustand é síncrono
        isUpdating,
        setMode,
        error,
    };
}
