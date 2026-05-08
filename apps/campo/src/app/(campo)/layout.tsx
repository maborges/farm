"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { initSyncListeners } from "@/lib/sync/worker";
import { OfflineBanner } from "@/components/offline-banner";
import { ErrorBoundary } from "@/components/error-boundary";
import { recoverInFlight } from "@/lib/sync/worker";

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { session, isAuthenticated, loadSession } = useSessionStore();
  const { setOnline } = useSyncStore();

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
      <div className="flex flex-col min-h-dvh">
        <OfflineBanner />
        <main className="flex-1">{children}</main>
      </div>
    </ErrorBoundary>
  );
}
