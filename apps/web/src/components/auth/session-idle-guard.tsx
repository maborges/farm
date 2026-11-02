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
    const lastActivityRef = useRef(0);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const { data } = useQuery<SessionConfig | SessionConfig[]>({
        queryKey: ["session-idle-config"],
        queryFn: () => apiFetch("/config/saas/sessao"),
        enabled: Boolean(token),
        staleTime: 60_000,
    });

    const sessionItem = Array.isArray(data)
        ? data.find((item) => item.chave === "sessao" && item.ativo)
        : data?.chave === "sessao" && data?.ativo
          ? data
          : undefined;
    const configuredMinutes = sessionItem?.valor?.tempo_inatividade_minutos;
    const minutes = Number.isFinite(configuredMinutes) && configuredMinutes > 0
        ? configuredMinutes
        : DEFAULT_IDLE_MINUTES;

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
        if (Number.isFinite(persisted) && persisted > 0 && persisted <= Date.now()) {
            lastActivityRef.current = persisted;
        } else {
            lastActivityRef.current = Date.now();
            localStorage.setItem(ACTIVITY_KEY, String(lastActivityRef.current));
        }
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
