"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { initSyncListeners } from "@/lib/sync/worker";
import { OfflineBanner } from "@/components/offline-banner";
import { ErrorBoundary } from "@/components/error-boundary";
import { recoverInFlight } from "@/lib/sync/worker";
import { CampoButton, CampoPill } from "@/components/campo/ui";
import { CampoBottomNav } from "@/components/campo/bottom-nav";

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { session, isAuthenticated, loadSession } = useSessionStore();
  const { setOnline, pendingCount, isOnline, status } = useSyncStore();

  useEffect(() => {
    loadSession().then(() => {
      const s = useSessionStore.getState();
      if (!s.session) {
        router.replace("/activate");
      } else if (!s.isAuthenticated) {
        router.replace("/pin");
      }
    });
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    recoverInFlight();
    const cleanup = initSyncListeners();
    setOnline(navigator.onLine);
    return cleanup;
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <ErrorBoundary>
      <div className="flex min-h-dvh flex-col">
        <div className="px-4 pt-4 sm:px-6">
          <div className="mx-auto flex w-full max-w-[520px] items-center justify-between rounded-[28px] border border-white/10 bg-white/[0.04] px-4 py-3 shadow-[0_20px_60px_rgba(0,0,0,0.22)] backdrop-blur-xl">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.22em] text-emerald-300/80">AgroSaaS Campo</p>
              <div className="mt-1 flex items-center gap-2">
                <span className="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-lime-300 text-lg text-emerald-950 shadow-lg shadow-emerald-950/20">
                  🌾
                </span>
                <div className="min-w-0">
                  <h1 className="truncate text-base font-semibold">{session?.user_name ?? "Operador"}</h1>
                  <p className="truncate text-xs text-white/45">Registros do campo</p>
                </div>
              </div>
            </div>
            <CampoButton variant="secondary" size="sm" onClick={() => router.push("/sync")}>
              <span className={`size-2 rounded-full ${isOnline ? "bg-emerald-400" : "bg-white/40"}`} />
              {pendingCount > 0 ? `${pendingCount} pend.` : status === "syncing" ? "Sincronizando..." : "Sincronizar"}
            </CampoButton>
          </div>
        </div>

        <div className="px-4 pt-3 sm:px-6">
          <OfflineBanner />
        </div>

        <main className="flex-1 px-4 pb-28 pt-4 sm:px-6 lg:pb-6">
          <div className="mx-auto w-full max-w-[860px]">{children}</div>
        </main>
        <CampoBottomNav />
      </div>
    </ErrorBoundary>
  );
}
