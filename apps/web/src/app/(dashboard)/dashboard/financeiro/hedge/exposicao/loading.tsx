import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function LoadingExposicao() {
    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Exposição Física × Financeira"
                description="Carregando dados de risco..."
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Exposição" },
                ]}
            />

            {/* Risco Global Skeleton */}
            <Card className="rounded-sm border-0 shadow-sm bg-gradient-to-r from-card to-muted/30">
                <CardContent className="pt-6">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                        <div className="space-y-4">
                            <Skeleton className="h-4 w-40 rounded-sm" />
                            <Skeleton className="h-10 w-32 rounded-sm" />
                        </div>
                        <div className="md:w-1/2 space-y-4">
                            <Skeleton className="h-4 w-full max-w-[200px] rounded-sm" />
                            <Skeleton className="h-4 w-full rounded-sm" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="space-y-4 mt-6">
                <div className="flex gap-4">
                    <Skeleton className="h-10 w-32 rounded-sm" />
                    <Skeleton className="h-10 w-32 rounded-sm" />
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                    {[1, 2, 3, 4].map(i => (
                        <Card key={i} className="rounded-sm">
                            <CardHeader className="pb-2">
                                <Skeleton className="h-4 w-24 rounded-sm" />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-8 w-16 rounded-sm mb-2" />
                                <Skeleton className="h-3 w-32 rounded-sm" />
                            </CardContent>
                        </Card>
                    ))}
                </div>

                <Card className="rounded-sm mt-6">
                    <CardHeader className="pb-3 flex flex-row items-center justify-between">
                        <Skeleton className="h-5 w-48 rounded-sm" />
                        <Skeleton className="h-8 w-24 rounded-sm" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-full rounded-sm" />
                            <Skeleton className="h-10 w-full rounded-sm" />
                            <Skeleton className="h-10 w-full rounded-sm" />
                            <Skeleton className="h-10 w-full rounded-sm" />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
