"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import { toast, Toaster } from "sonner";
import { isStaleServerActionError } from "@/lib/server-action-errors";

function SonnerProvider() {
    const { resolvedTheme } = useTheme();
    return (
        <Toaster
            position="top-right"
            theme={resolvedTheme === "dark" ? "dark" : "light"}
            richColors
            closeButton
        />
    );
}

function ServerActionErrorHandler() {
    const lastNotificationRef = useRef(0);

    const notify = useCallback((error: unknown) => {
        if (!isStaleServerActionError(error) || Date.now() - lastNotificationRef.current < 3000) {
            return;
        }

        lastNotificationRef.current = Date.now();
        toast.error("A página precisa ser atualizada", {
            description: "O sistema foi atualizado enquanto esta página estava aberta. Atualize para continuar.",
            duration: Infinity,
            action: {
                label: "Atualizar página",
                onClick: () => window.location.reload(),
            },
        });
    }, []);

    useEffect(() => {
        const handleRejection = (event: PromiseRejectionEvent) => notify(event.reason);
        const handleError = (event: ErrorEvent) => notify(event.error ?? event.message);

        window.addEventListener("unhandledrejection", handleRejection);
        window.addEventListener("error", handleError);
        return () => {
            window.removeEventListener("unhandledrejection", handleRejection);
            window.removeEventListener("error", handleError);
        };
    }, [notify]);

    return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 1000 * 60 * 5, // Cache por 5 minutos
                refetchOnWindowFocus: false, // Não recarrega ao alt-tab pra economizar consumo da nossa Cloud
                retry: 1 // Tenta só mais uma vez se der erro de rede rápido
            },
        },
    }));

    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
                <SonnerProvider />
                <ServerActionErrorHandler />
                {children}
            </ThemeProvider>
        </QueryClientProvider>
    );
}
