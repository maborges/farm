"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { SafraFenologia } from "@/components/agricola/safra-fenologia";
import { SafraGruposTalhoes } from "@/components/agricola/safra-grupos-talhoes";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getSafraLabel } from "@/lib/safra-label";
import { Leaf } from "lucide-react";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

interface Talhao {
    id: string;
    nome: string;
}

export default function FenologiaPage() {
    const { id } = useParams<{ id: string }>();

    const { data: safra, isLoading } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    const { data: talhoesSafra = [], isLoading: loadingTalhoesSafra } = useQuery<{ area_id: string }[]>({
        queryKey: ["safra-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/talhoes`),
        enabled: !!safra,
    });

    const { data: todasAreas = [], isLoading: loadingAreas } = useQuery<Talhao[]>({
        queryKey: ["areas-rurais", "fenologia-safra", id],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
        enabled: !!safra,
    });

    const talhoes = talhoesSafra
        .map((t) => todasAreas.find((a) => a.id === t.area_id))
        .filter((a): a is Talhao => !!a);

    if (isLoading || loadingTalhoesSafra || loadingAreas) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title={`Fenologia — ${safraLabel}`}
                icon={<Leaf className="text-green-600" size={22} />}
                description={safraLabel}
            />
            <Tabs defaultValue="registros">
                <TabsList>
                    <TabsTrigger value="registros">Registros por Talhão</TabsTrigger>
                    <TabsTrigger value="grupos">Grupos de Talhões</TabsTrigger>
                </TabsList>
                <TabsContent value="registros" className="mt-4">
                    <SafraFenologia safraId={id} cultura={safra?.cultura ?? null} grupos={[]} talhoes={talhoes} />
                </TabsContent>
                <TabsContent value="grupos" className="mt-4">
                    <SafraGruposTalhoes safraId={id} fazendaTalhoes={[]} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
