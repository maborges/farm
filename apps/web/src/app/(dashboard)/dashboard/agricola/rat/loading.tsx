import { Skeleton } from "@/components/ui/skeleton";

export default function RatLoading() {
    return (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-screen-xl mx-auto px-4 md:px-8 py-8">
            <div className="space-y-4">
                <Skeleton className="h-10 w-64 rounded-sm" />
                <Skeleton className="h-4 w-full max-w-md rounded-sm" />
            </div>
            
            <div className="grid gap-4 md:grid-cols-3">
                <Skeleton className="h-24 w-full rounded-sm" />
                <Skeleton className="h-24 w-full rounded-sm" />
                <Skeleton className="h-24 w-full rounded-sm" />
            </div>

            <div className="rounded-sm border border-border overflow-hidden bg-card">
                <div className="p-6 space-y-4">
                    <Skeleton className="h-8 w-64 rounded-sm" />
                    <Skeleton className="h-64 w-full rounded-sm" />
                </div>
            </div>
        </div>
    );
}
