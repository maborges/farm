"use client";

import { useEffect, useRef } from "react";
import { sendAgroHeartbeat } from "@/lib/auth/agro-auth";

const THROTTLE_INTERVAL_MS = 120_000; // 2 minutos

/**
 * Componente invisível de batimento de sessão (heartbeat) para o PWA Agro.
 *
 * REQUISITOS DE GOVERNANÇA:
 * 1. Não expõe tokens ao JavaScript (opera via cookie HttpOnly).
 * 2. Somente dispara se a página estiver visível (document.visibilityState === 'visible').
 * 3. Somente dispara se houver conexão ativa (navigator.onLine).
 * 4. Não dispara em segundo plano nem gera sessões fantasmas quando offline.
 * 5. Se o servidor responder 401/403, suspende tentativas subsequentes (usuário deslogado/anônimo).
 */
export function SessionHeartbeat() {
  const lastSentRef = useRef<number>(0);
  const isSuspendedRef = useRef<boolean>(false);
  const hasUserActivityRef = useRef<boolean>(true);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Detecta interação real do usuário no PWA
    const markActivity = () => {
      hasUserActivityRef.current = true;
    };

    window.addEventListener("pointerdown", markActivity, { passive: true });
    window.addEventListener("keydown", markActivity, { passive: true });
    window.addEventListener("touchstart", markActivity, { passive: true });

    const trySendHeartbeat = async () => {
      if (isSuspendedRef.current) return;
      if (typeof navigator !== "undefined" && !navigator.onLine) return;
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
      if (!hasUserActivityRef.current) return;

      const now = Date.now();
      if (now - lastSentRef.current < THROTTLE_INTERVAL_MS) return;

      lastSentRef.current = now;
      hasUserActivityRef.current = false;

      const res = await sendAgroHeartbeat();
      if (!res.ok) {
        // Se a sessão for inválida/inexistente ou anônima, suspende o loop
        isSuspendedRef.current = true;
      }
    };

    // Tentativa inicial suave após montagem (2 segundos para não concorrer com carregamento inicial)
    const initialTimer = setTimeout(() => {
      void trySendHeartbeat();
    }, 2000);

    // Intervalo de verificação periódica
    const intervalTimer = setInterval(() => {
      void trySendHeartbeat();
    }, THROTTLE_INTERVAL_MS);

    // Retomada de foco e visibilidade
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        hasUserActivityRef.current = true;
        void trySendHeartbeat();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(intervalTimer);
      window.removeEventListener("pointerdown", markActivity);
      window.removeEventListener("keydown", markActivity);
      window.removeEventListener("touchstart", markActivity);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return null;
}
