"use client";

import { ModuleError } from "@/components/shared/module-error";

export default function FinanceiroError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ModuleError moduleLabel="Financeiro" error={error} reset={reset} />;
}
