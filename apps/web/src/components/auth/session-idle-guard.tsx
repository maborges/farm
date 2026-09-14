"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";

interface SessionConfig {
    chave: string;
    valor: { tempo_inatividade_minutos?: number };
    ativo: boolean;
}

const ACTIVITY_KEY = "agrosaas-last-activity";
const DEFAULT_IDLE_MINUTES = 30;

export function SessionIdleGuard() {
    const token = useAppStore((state) => state.token);
    const logout = useAppStore((state) => state.logout);
    const lastActivityRef = useRef(Date.now());
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const { data } = useQuery<SessionConfig[]>({
        queryKey: ["session-idle-config"],
        queryFn: () => apiFetch("/config/saas"),
        enabled: Boolean(token),
        staleTime: 60_000,
    });

    const minutes = data?.find((item) => item.chave === "sessao" && item.ativo)
        ?.valor?.tempo_inatividade_minutos ?? DEFAULT_IDLE_MINUTES;

    useEffect(() => {
        if (!token) return;

        const schedule = () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            const elapsed = Date.now() - lastActivityRef.current;
            const remaining = Math.max(1000, minutes * 60_000 - elapsed);
            timeoutRef.current = setTimeout(() => {
                void logout();
            }, remaining);
        };

        const markActivity = () => {
            lastActivityRef.current = Date.now();
            localStorage.setItem(ACTIVITY_KEY, String(lastActivityRef.current));
            schedule();
        };

        const persisted = Number(localStorage.getItem(ACTIVITY_KEY) || 0);
        if (persisted > 0) lastActivityRef.current = persisted;
        ["mousedown", "keydown", "touchstart", "scroll", "pointerdown"].forEach((event) =>
            window.addEventListener(event, markActivity, { passive: true }),
        );
        schedule();

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            ["mousedown", "keydown", "touchstart", "scroll", "pointerdown"].forEach((event) =>
                window.removeEventListener(event, markActivity),
            );
        };
    }, [logout, minutes, token]);

    return null;
}
