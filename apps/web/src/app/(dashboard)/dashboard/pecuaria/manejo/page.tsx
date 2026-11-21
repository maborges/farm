import { Suspense } from "react";

import { ManejoClient } from "@/components/pecuaria/manejo-client";
import { Skeleton } from "@/components/ui/skeleton";

export default function PecuariaManejoPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 space-y-6">
          <Skeleton className="h-12 w-72 rounded-sm" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Skeleton className="h-24 w-full rounded-sm" />
            <Skeleton className="h-24 w-full rounded-sm" />
            <Skeleton className="h-24 w-full rounded-sm" />
            <Skeleton className="h-24 w-full rounded-sm" />
          </div>
          <Skeleton className="h-80 w-full rounded-sm" />
        </div>
      }
    >
      <ManejoClient />
    </Suspense>
  );
}
