"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { PlanejamentoOperacionalSafra } from "@/components/agricola/planejamento-operacional-safra";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { ClipboardCheck } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

export default function PlanejamentoOperacionalPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);

    const { data: safra, isLoading } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    if (isLoading || !safra) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-72" />
                <Skeleton className="h-32 w-full max-w-7xl mx-auto" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Planejamento Operacional — ${safraLabel}`}
                icon={<ClipboardCheck className="text-violet-600" size={22} />}
                description={safraLabel}
            />
            <PlanejamentoOperacionalSafra safraId={id} />
        </div>
    );
}
