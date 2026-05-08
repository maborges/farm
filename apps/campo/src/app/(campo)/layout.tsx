"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { initSyncListeners } from "@/lib/sync/worker";
import { SyncStatusBar } from "@/components/sync-status-bar";

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
    const cleanup = initSyncListeners();
    setOnline(navigator.onLine);
    return cleanup;
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <div className="flex flex-col min-h-dvh">
      <SyncStatusBar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
