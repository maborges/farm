"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { OrcamentoSafra } from "@/components/agricola/orcamento-safra";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { BarChart2 } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

export default function OrcamentoPage({ params }: { params: Promise<{ id: string }> }) {
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
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Orçamento de Custeio — ${safraLabel}`}
                icon={<BarChart2 className="text-violet-600" size={22} />}
                description={safraLabel}
            />
            <OrcamentoSafra safraId={id} />
        </div>
    );
}
