import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { AbastecimentoHeader } from "./_components/abastecimento-header";
import { AbastecimentoList } from "./_components/abastecimento-list";

export const metadata = {
    title: "Abastecimentos — AgroSaaS",
    description: "Controle de consumo de combustível e lubrificantes da frota.",
};

export default async function AbastecimentosPage() {
    return (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-screen-xl mx-auto px-4 md:px-8 py-8">
            <AbastecimentoHeader />
            
            <Suspense fallback={<AbastecimentoSkeleton />}>
                <AbastecimentoList />
            </Suspense>
        </div>
    );
}

function AbastecimentoSkeleton() {
    return (
        <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
                {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-24 w-full" />
                ))}
            </div>
            <Skeleton className="h-[400px] w-full" />
        </div>
    );
}
