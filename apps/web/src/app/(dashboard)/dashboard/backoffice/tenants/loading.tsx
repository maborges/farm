import { Skeleton } from "@/components/ui/skeleton";
import { Building2, ShieldCheck, Users } from "lucide-react";

export default function TenantsLoading() {
    return (
        <div className="p-6 space-y-6 w-full">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="space-y-2">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-4 w-96" />
                </div>
                <Skeleton className="h-9 w-40" />
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[Building2, ShieldCheck, Users].map((Icon, index) => (
                    <div key={index} className="p-4 rounded-sm border bg-card shadow-sm flex items-center gap-4">
                        <div className="h-10 w-10 rounded-sm bg-muted flex items-center justify-center">
                            <Icon size={20} className="text-muted-foreground" />
                        </div>
                        <div className="space-y-2">
                            <Skeleton className="h-3 w-32" />
                            <Skeleton className="h-8 w-16" />
                        </div>
                    </div>
                ))}
            </div>

            {/* Table */}
            <div className="rounded-sm border bg-card shadow-sm overflow-hidden">
                <div className="p-4 space-y-3">
                    {/* Table Header */}
                    <div className="grid grid-cols-6 gap-4 pb-3 border-b">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                    </div>

                    {/* Table Rows */}
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((row) => (
                        <div key={row} className="grid grid-cols-6 gap-4 py-3 border-b last:border-0">
                            <div className="space-y-1">
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-3 w-3/4" />
                            </div>
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-6 w-20" />
                            <div className="space-y-1">
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-3 w-16" />
                            </div>
                            <div className="flex justify-end gap-2">
                                <Skeleton className="h-7 w-24" />
                                <Skeleton className="h-7 w-24" />
                                <Skeleton className="h-7 w-24" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
