"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { RomaneiosColheita } from "@/components/agricola/romaneios-colheita";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { Wheat } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

interface Talhao {
    id: string;
    nome: string;
}

interface TalhaoSafra {
    area_id: string;
    nome: string | null;
    area_total_ha: number | null;
}

function formatarTalhao(nome: string | null, areaTotalHa: number | null) {
    const nomeTalhao = nome ?? "Talhão sem nome";
    if (areaTotalHa == null) return nomeTalhao;

    return `${nomeTalhao} — ${areaTotalHa.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha`;
}

export default function RomaneiosSafraPage() {
    const { id } = useParams<{ id: string }>();

    const { data: safra, isLoading: loadingSafra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    const { data: talhoesSafra = [], isLoading: loadingTalhoes } = useQuery<TalhaoSafra[]>({
        queryKey: ["safra-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/talhoes`),
    });

    const talhoes: Talhao[] = talhoesSafra.map(({ area_id, nome, area_total_ha }) => ({
        id: area_id,
        nome: formatarTalhao(nome, area_total_ha),
    }));

    if (loadingSafra || loadingTalhoes) {
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
                title={`Romaneios de Colheita — ${safraLabel}`}
                icon={<Wheat className="text-yellow-600" size={22} />}
                description={safraLabel}
            />
            <RomaneiosColheita
                safraId={id}
                talhoes={talhoes}
                cultura={safra?.cultura ?? undefined}
                anoSafra={safra?.ano_safra}
            />
        </div>
    );
}
