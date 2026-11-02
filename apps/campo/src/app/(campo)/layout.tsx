"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdaptiveCampoSidebar } from "@/components/campo/adaptive-sidebar";
import { CampoBottomNav } from "@/components/campo/bottom-nav";
import { CampoPwaInstallBanner } from "@/components/campo/pwa-install-banner";
import { CampoTopAppBar } from "@/components/campo/top-app-bar";
import { ErrorBoundary } from "@/components/error-boundary";
import { OfflineBanner } from "@/components/offline-banner";
import { useGps } from "@/hooks/useGps";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { initSyncListeners, recoverInFlight } from "@/lib/sync/worker";

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, loadSession, validateDeviceSession } = useSessionStore();
  const { setOnline, pendingCount, isOnline, status } = useSyncStore();
  const { layoutProfile } = useDeviceContext();
  const gps = useGps(true);

  useEffect(() => {
    void loadSession().then(async () => {
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
  }, [loadSession, router, validateDeviceSession]);

  useEffect(() => {
    if (!isAuthenticated) return;
    recoverInFlight();
    const cleanup = initSyncListeners();
    setOnline(navigator.onLine);
    return cleanup;
  }, [isAuthenticated, setOnline]);

  if (!isAuthenticated) return null;

  return (
    <ErrorBoundary>
      {/* Ambient Agtech Background with subtle glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10 bg-background">
        <img
          src="/images/login-bg.png"
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover object-center opacity-25 select-none dark:opacity-15 transition-opacity"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-emerald-950/55 via-background/88 to-background dark:from-emerald-950/75 dark:via-background/92 dark:to-background" />
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-72 w-72 rounded-full bg-emerald-500/15 blur-3xl" />
      </div>

      <div
        data-device-category={layoutProfile.deviceCategory}
        data-execution-mode={layoutProfile.executionMode}
        data-navigation-mode={layoutProfile.navigationMode}
        data-density={layoutProfile.density}
        className="relative z-0 flex min-h-dvh w-full overflow-x-hidden"
      >
        {/* Sidebar retrátil (Rail em Tablet 768px+, Sidebar expandida em Desktop 1024px+) */}
        <AdaptiveCampoSidebar />

        <div className="flex min-h-dvh min-w-0 flex-1 flex-col">
          <CampoTopAppBar
            pendingCount={pendingCount}
            isOnline={isOnline}
            syncStatus={status}
            gpsStatus={gps.status}
          />

          <div className="mx-auto flex w-full max-w-lg md:max-w-5xl lg:max-w-6xl flex-col gap-2 px-3 pt-2.5 sm:px-5">
            <OfflineBanner />
            <CampoPwaInstallBanner />
          </div>

          <main className="mx-auto flex-1 w-full max-w-lg md:max-w-5xl lg:max-w-6xl px-3 pb-24 pt-3 sm:px-5 md:pb-8">
            <div className="campo-pwa-page w-full">{children}</div>
          </main>

          {/* Bottom Navigation nativa exclusiva para Mobile (< 768px) */}
          <CampoBottomNav />
        </div>
      </div>
    </ErrorBoundary>
  );
}
