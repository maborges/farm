"use client";

import { useEffect, useState } from "react";
import { useSyncStore } from "@/lib/stores/sync-store";

export function useNetworkStatus() {
  const { isOnline, setOnline } = useSyncStore();
  const [wasOffline, setWasOffline] = useState(false);
  const [justReconnected, setJustReconnected] = useState(false);

  useEffect(() => {
    const onOnline = () => {
      setOnline(true);
      if (wasOffline) {
        setJustReconnected(true);
        setTimeout(() => setJustReconnected(false), 3000);
      }
      setWasOffline(false);
    };

    const onOffline = () => {
      setOnline(false);
      setWasOffline(true);
      setJustReconnected(false);
    };

    // Sync inicial
    setOnline(navigator.onLine);
    if (!navigator.onLine) setWasOffline(true);

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [wasOffline]);

  return { isOnline, justReconnected };
}
