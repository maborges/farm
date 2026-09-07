"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "@/lib/stores/app-store";

export function SessionGuard({ children }: { children: React.ReactNode }) {
    const { token, _hasHydrated } = useAppStore();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // Só redireciona após o Zustand terminar de hidratar do localStorage.
        // Sem esse check, o refresh redirecionava para login porque o token
        // ainda era null antes da hidratação completar.
        if (_hasHydrated && !token) {
            router.replace("/login");
        }
    }, [token, _hasHydrated, router, pathname]);

    if (!_hasHydrated || !token) {
        return (
            <div className="flex min-h-dvh items-center justify-center bg-neutral-900">
                <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
            </div>
        );
    }

    return <>{children}</>;
}
