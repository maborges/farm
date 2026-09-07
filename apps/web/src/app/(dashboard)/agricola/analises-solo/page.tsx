import { Suspense } from "react";
import { AnalisesClient } from "@/app/(dashboard)/dashboard/agricola/analises-solo/components/analises-client";
import { Skeleton } from "@/components/ui/skeleton";

function LoadingFallback() {
    return (
        <div className="space-y-6">
            <div className="space-y-2">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-96" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24" />)}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Skeleton className="h-64" />
                <Skeleton className="h-64" />
            </div>
            <Skeleton className="h-80" />
        </div>
    );
}

export const metadata = {
    title: "Análise de Solo | AgroSaaS",
    description: "Gestão técnica de fertilidade e recomendações de correção de solo.",
};

export default async function AnaliseSoloPage() {
    return (
        <Suspense fallback={<LoadingFallback />}>
            <AnalisesClient />
        </Suspense>
    );
}
