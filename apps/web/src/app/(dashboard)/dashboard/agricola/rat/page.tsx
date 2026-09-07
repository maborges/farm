import { Suspense } from "react";
import { RelatorioTecnicoList } from "./_components/rat-list";
import { RelatorioTecnicoHeader } from "./_components/rat-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

export default async function RelatorioTecnicoPage() {
    return (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-screen-xl mx-auto px-4 md:px-8 py-8">
            <RelatorioTecnicoHeader />
            
            <Card className="shadow-sm border-border rounded-sm overflow-hidden">
                <CardContent className="p-0">
                    <Suspense fallback={<RatListSkeleton />}>
                        <RelatorioTecnicoList />
                    </Suspense>
                </CardContent>
            </Card>
        </div>
    );
}

function RatListSkeleton() {
    return (
        <div className="p-6 space-y-4">
            <Skeleton className="h-10 w-full rounded-sm" />
            <Skeleton className="h-10 w-full rounded-sm" />
            <Skeleton className="h-10 w-full rounded-sm" />
        </div>
    );
}
