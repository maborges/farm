"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdaptiveCampoSidebar } from "@/components/campo/adaptive-sidebar";
import { CampoBottomNav } from "@/components/campo/bottom-nav";
import { CampoPwaInstallBanner } from "@/components/campo/pwa-install-banner";
import { CampoPwaUpdateBanner } from "@/components/campo/pwa-update-banner";
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
      <div
        id="campo-adaptive-shell"
        data-device-category={layoutProfile.deviceCategory}
        data-execution-mode={layoutProfile.executionMode}
        data-navigation-mode={layoutProfile.navigationMode}
        data-platform-os={layoutProfile.platformOS}
        data-density={layoutProfile.density}
        className="min-h-dvh flex flex-col bg-background text-foreground safe-area-px"
      >
        <CampoTopAppBar
          pendingCount={pendingCount}
          isOnline={isOnline}
          syncStatus={status}
          gpsStatus={gps.status}
        />

        <div className="flex-1 flex w-full max-w-7xl mx-auto">
          <AdaptiveCampoSidebar />

          <main className="flex-1 min-w-0 w-full max-w-5xl mx-auto px-3 sm:px-5 md:px-6 py-3 sm:py-5 pb-24 md:pb-8">
            <div className="flex flex-col gap-3">
              <CampoPwaUpdateBanner />
              <OfflineBanner />
              <CampoPwaInstallBanner />
              <div className="campo-pwa-page w-full">{children}</div>
            </div>
          </main>
        </div>

        <CampoBottomNav />
      </div>
    </ErrorBoundary>
  );
}
