"use client";

import { ModuleError } from "@/components/shared/module-error";

export default function PecuariaError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ModuleError moduleLabel="Pecuária" error={error} reset={reset} />;
}
