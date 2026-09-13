"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export function OfflineStatus() {
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  if (!offline) return null;
  return <div className="fixed bottom-3 left-1/2 z-[var(--z-toast)] flex -translate-x-1/2 items-center gap-2 rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900 shadow-lg dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"><WifiOff className="size-3.5" aria-hidden="true" />Modo offline: alterações serão retomadas quando a conexão voltar.</div>;
}

