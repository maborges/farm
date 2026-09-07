import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { FlaskConical } from "lucide-react";

export default function Loading() {
    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto w-full animate-in fade-in duration-500">
            {/* Header Skeleton */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <FlaskConical className="text-muted-foreground/20" />
                        <Skeleton className="h-8 w-64" />
                    </div>
                    <Skeleton className="h-4 w-96 max-w-full" />
                </div>
                <Skeleton className="h-9 w-32" />
            </div>

            {/* KPI Skeletons */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[1, 2, 3, 4].map((i) => (
                    <Card key={i} className="border-none bg-muted/20">
                        <CardContent className="p-4 space-y-2">
                            <Skeleton className="h-3 w-16" />
                            <Skeleton className="h-8 w-24" />
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Charts Skeletons */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2].map((i) => (
                    <Card key={i} className="border-border/40">
                        <CardHeader className="pb-2">
                            <Skeleton className="h-5 w-48 mb-1" />
                            <Skeleton className="h-3 w-64" />
                        </CardHeader>
                        <CardContent>
                            <Skeleton className="h-[220px] w-full rounded-sm" />
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Grid Skeleton */}
            <Card className="border-border/40">
                <CardHeader className="pb-3 border-b">
                    <Skeleton className="h-5 w-40 mb-1" />
                    <Skeleton className="h-3 w-72" />
                </CardHeader>
                <div className="divide-y divide-border/40">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="flex items-center justify-between p-4">
                            <div className="flex items-center gap-4">
                                <Skeleton className="size-10 rounded-sm" />
                                <div className="space-y-2">
                                    <Skeleton className="h-4 w-32" />
                                    <Skeleton className="h-3 w-48" />
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="hidden md:flex gap-4">
                                    <Skeleton className="h-8 w-12" />
                                    <Skeleton className="h-8 w-12" />
                                    <Skeleton className="h-8 w-12" />
                                </div>
                                <Skeleton className="h-8 w-24" />
                            </div>
                        </div>
                    ))}
                </div>
            </Card>
        </div>
    );
}
