"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { SafraChecklist } from "@/components/agricola/safra-checklist";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { CheckSquare } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
    status: string;
}

export default function ChecklistPage() {
    const { id } = useParams<{ id: string }>();

    const { data: safra, isLoading } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    if (isLoading) {
        return (
            <div className="space-y-4 p-8">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Checklist Agronômico — ${safraLabel}`}
                icon={<CheckSquare className="text-teal-600" size={22} />}
                description={safra ? `${safraLabel} · Fase: ${safra.status}` : ""}
            />
            {safra && <SafraChecklist safraId={id} cultura={safra.cultura} fase={safra.status} />}
        </div>
    );
}
