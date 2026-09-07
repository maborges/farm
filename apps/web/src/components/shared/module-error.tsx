"use client";

import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ModuleErrorProps {
  moduleLabel: string;
  error: Error & { digest?: string };
  reset: () => void;
}

export function ModuleError({ moduleLabel, error, reset }: ModuleErrorProps) {
  return (
    <div className="flex w-full flex-1 flex-col items-center justify-center gap-4 p-24 text-center">
      <AlertTriangle className="size-12 text-destructive" />
      <div className="space-y-1">
        <h2 className="text-xl font-bold">Algo deu errado em {moduleLabel}</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          Não foi possível carregar esta página. Tente novamente ou volte mais tarde.
        </p>
        {error.digest && (
          <p className="font-mono text-xs text-muted-foreground/70">Código: {error.digest}</p>
        )}
      </div>
      <Button size="sm" variant="outline" className="rounded-sm" onClick={() => reset()}>
        <RotateCw data-icon="inline-start" />
        Tentar novamente
      </Button>
    </div>
  );
}
