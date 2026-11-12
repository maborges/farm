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

interface GrupoItem {
    id: string;
    talhao_id: string;
}

interface Grupo {
    id: string;
    nome: string;
    cor: string | null;
    ordem: number;
    itens: GrupoItem[];
}

interface Talhao {
    id: string;
    nome: string;
    area_ha?: number | null;
    codigo?: string | null;
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

    const { data: grupos = [], isLoading: loadingGrupos } = useQuery<Grupo[]>({
        queryKey: ["grupos-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/grupos-talhoes`),
        enabled: !!safra,
    });

    const talhoes = talhoesSafra
        .map((t) => todasAreas.find((a) => a.id === t.area_id))
        .filter((a): a is Talhao => !!a);

    if (isLoading || loadingTalhoesSafra || loadingAreas || loadingGrupos) {
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
                icon={<Leaf className="text-emerald-600" size={22} />}
                description="Acompanhamento do desenvolvimento e estágios vegetativos e reprodutivos por talhão."
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Safras", href: "/agricola/safras" },
                    { label: safraLabel, href: `/agricola/safras/${id}` },
                    { label: "Fenologia" },
                ]}
            />
            <Tabs defaultValue="registros">
                <TabsList className="rounded-sm">
                    <TabsTrigger value="registros" className="rounded-sm text-xs">
                        Acompanhamento e Registros
                    </TabsTrigger>
                    <TabsTrigger value="grupos" className="rounded-sm text-xs">
                        Grupos de Talhões ({grupos.length})
                    </TabsTrigger>
                </TabsList>
                <TabsContent value="registros" className="mt-4">
                    <SafraFenologia safraId={id} cultura={safra?.cultura ?? null} grupos={grupos} talhoes={talhoes} />
                </TabsContent>
                <TabsContent value="grupos" className="mt-4">
                    <SafraGruposTalhoes safraId={id} fazendaTalhoes={talhoes} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
