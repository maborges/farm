"use client";

import { useSyncExternalStore } from "react";
import { WifiOff } from "lucide-react";

let isHydrated = false;

function subscribeOnline(callback: () => void) {
  isHydrated = true;
  queueMicrotask(() => {
    callback();
  });
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getOnlineSnapshot() {
  if (!isHydrated || typeof navigator === "undefined") {
    return true;
  }
  return navigator.onLine;
}

function getOnlineServerSnapshot() {
  return true;
}

export function ConnectionStatus() {
  const isOnline = useSyncExternalStore(
    subscribeOnline,
    getOnlineSnapshot,
    getOnlineServerSnapshot
  );

  if (isOnline) {
    return null;
  }

  return (
    <div
      className="fixed top-[calc(3.75rem+env(safe-area-inset-top,0px))] left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full text-xs font-medium flex items-center gap-2 shadow-lg bg-amber-600 text-white animate-in fade-in duration-300"
      role="status"
      aria-live="polite"
    >
      <WifiOff className="w-3.5 h-3.5" />
      <span>Modo Offline — exibindo dados salvos</span>
    </div>
  );
}
