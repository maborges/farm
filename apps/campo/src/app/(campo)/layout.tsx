"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { initSyncListeners } from "@/lib/sync/worker";
import { OfflineBanner } from "@/components/offline-banner";
import { ErrorBoundary } from "@/components/error-boundary";
import { recoverInFlight } from "@/lib/sync/worker";
import { CampoBottomNav } from "@/components/campo/bottom-nav";
import { CampoTopAppBar } from "@/components/campo/top-app-bar";
import { useGps } from "@/hooks/useGps";

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, loadSession, validateDeviceSession } = useSessionStore();
  const { setOnline, pendingCount, isOnline, status } = useSyncStore();
  const gps = useGps(true);

  useEffect(() => {
    loadSession().then(async () => {
      const s = useSessionStore.getState();
      if (!s.session) {
        router.replace("/activate");
      } else {
        const valid = await validateDeviceSession();
        if (!valid) {
          router.replace("/activate?reason=device_revoked");
          return;
        }
        if (!s.isAuthenticated) {
          router.replace("/pin");
        }
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
      {/* Ambient Agtech Background with subtle glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10 bg-background">
        <img
          src="/images/login-bg.png"
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover object-center opacity-30 select-none dark:opacity-20 transition-opacity"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-emerald-950/60 via-background/85 to-background dark:from-emerald-950/80 dark:via-background/90 dark:to-background" />
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-72 w-72 rounded-full bg-emerald-500/15 blur-3xl" />
      </div>

      <div className="flex min-h-dvh flex-col relative z-0">
        <CampoTopAppBar
          pendingCount={pendingCount}
          isOnline={isOnline}
          syncStatus={status}
          gpsStatus={gps.status}
        />

        <div className="px-4 pt-3 sm:px-6">
          <OfflineBanner />
        </div>

        <main className="flex-1 px-4 pb-28 pt-4 sm:px-6 lg:pb-6">
          <div className="campo-pwa-page w-full">{children}</div>
        </main>
        <CampoBottomNav />
      </div>
    </ErrorBoundary>
  );
}
