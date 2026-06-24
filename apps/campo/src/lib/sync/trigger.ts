"use client";

import { logger } from "@/lib/logger";

let scheduled = false;

export function requestSync(): void {
  if (scheduled) return;
  scheduled = true;

  queueMicrotask(() => {
    scheduled = false;
    void (async () => {
      try {
        const { runSync } = await import("./worker");
        await runSync();
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Falha ao disparar sync";
        logger.warn("SyncTrigger", msg);
      }
    })();
  });
}
