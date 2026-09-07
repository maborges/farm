"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { MonitoramentoRegistro } from "@/components/agricola/monitoramento-registro";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { Bug } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

interface Talhao {
    id: string;
    nome: string;
}

export default function MonitoramentoPage() {
    const { id } = useParams<{ id: string }>();

    const { data: safra, isLoading: loadingSafra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    const { data: talhoesSafra = [], isLoading: loadingTalhoes } = useQuery<{ area_id: string; principal: boolean }[]>({
        queryKey: ["safra-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/talhoes`),
    });

    const { data: todasAreas = [] } = useQuery<Talhao[]>({
        queryKey: ["areas-rurais"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    });

    const talhoes: Talhao[] = talhoesSafra
        .map(t => todasAreas.find(a => a.id === t.area_id))
        .filter((a): a is Talhao => !!a);

    if (loadingSafra || loadingTalhoes || !safra) {
        return (
            <div className="space-y-4 p-8">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Monitoramento Fitossanitário — ${safraLabel}`}
                icon={<Bug className="text-red-600" size={22} />}
                description={safraLabel}
            />
            <MonitoramentoRegistro safraId={id} talhoes={talhoes} />
        </div>
    );
}
