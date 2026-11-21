import { Suspense } from "react";

import { ImportacaoPlanilhaWizard } from "@/components/pecuaria/importacao-planilha-wizard";
import { Skeleton } from "@/components/ui/skeleton";

export default function PecuariaImportarPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 space-y-4">
          <Skeleton className="h-12 w-80 rounded-sm" />
          <Skeleton className="h-64 w-full rounded-sm" />
        </div>
      }
    >
      <ImportacaoPlanilhaWizard />
    </Suspense>
  );
}
