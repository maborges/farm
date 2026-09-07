"use client";

import { ModuleError } from "@/components/shared/module-error";

export default function AgricolaError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ModuleError moduleLabel="Agrícola" error={error} reset={reset} />;
}
