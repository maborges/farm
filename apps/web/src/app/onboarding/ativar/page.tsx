import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { AtivarContaClientPage } from "@/components/onboarding/ativar-conta-page";

function AtivarContaFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-lg space-y-4">
        <Skeleton className="h-8 w-48 mx-auto" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    </div>
  );
}

export default function AtivarContaPage() {
  return (
    <Suspense fallback={<AtivarContaFallback />}>
      <AtivarContaClientPage />
    </Suspense>
  );
}
