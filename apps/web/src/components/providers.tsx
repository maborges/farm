"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import { Toaster } from "sonner";

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
                {children}
            </ThemeProvider>
        </QueryClientProvider>
    );
}
