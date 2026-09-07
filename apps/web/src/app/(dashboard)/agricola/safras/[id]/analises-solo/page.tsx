"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { AnaliseSoloPanel } from "@/components/agricola/analise-solo";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowRight, FlaskConical } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
    talhao_id?: string;
}

interface Talhao {
    id: string;
    nome: string;
}

interface CultivoArea {
    area_id: string;
}

interface Cultivo {
    id: string;
    areas: CultivoArea[];
}

interface AnaliseSolo {
    id: string;
    talhao_id: string;
    data_coleta: string;
    laboratorio?: string | null;
    codigo_amostra?: string | null;
    profundidade_cm?: number | null;
    ph_agua?: number | null;
    v_pct?: number | null;
    created_at: string;
}

export default function AnaliseSoloSafraPage() {
    const { id } = useParams<{ id: string }>();

    const { data: safra, isLoading: loadingSafra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    const { data: talhoesSafra = [] } = useQuery<{ area_id: string }[]>({
        queryKey: ["safra-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/talhoes`),
    });

    const { data: cultivos = [] } = useQuery<Cultivo[]>({
        queryKey: ["safra-cultivos", id],
        queryFn: () => apiFetch(`/safras/${id}/cultivos`),
    });

    const { data: todasAreas = [], isLoading: loadingTalhoes } = useQuery<Talhao[]>({
        queryKey: ["areas-rurais"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    });

    const { data: analises = [], isLoading: loadingAnalises, isError: isAnalisesError, error: analisesError } = useQuery<AnaliseSolo[]>({
        queryKey: ["analises-solo-safra", id],
        queryFn: () => apiFetch("/analises-solo/"),
        enabled: !!safra,
    });

    const talhaoIds = talhoesSafra.length > 0
        ? talhoesSafra.map((talhao) => talhao.area_id)
        : Array.from(new Set(cultivos.flatMap((cultivo) => cultivo.areas.map((area) => area.area_id))));

    const talhoesDaSafra = talhaoIds
        .map((talhaoId) => todasAreas.find((area) => area.id === talhaoId))
        .filter((a): a is Talhao => !!a);

    const talhoes: Talhao[] = talhoesDaSafra;

    if (loadingSafra || loadingTalhoes || loadingAnalises) {
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
                title={`Análise de Solo — ${safraLabel}`}
                icon={<FlaskConical className="text-amber-600" size={22} />}
                description={safraLabel}
            />
            {isAnalisesError ? (
                <Alert variant="destructive">
                    <AlertCircle className="size-4" />
                    <AlertTitle>Erro ao carregar análises de solo</AlertTitle>
                    <AlertDescription>
                        {analisesError instanceof Error ? analisesError.message : "Não foi possível carregar os dados da safra."}
                    </AlertDescription>
                </Alert>
            ) : (
                <AnaliseSoloPanel talhoes={talhoes} analises={analises} />
            )}
            <div className="flex justify-end">
                <Button asChild>
                    <Link href="/agricola/analises-solo">
                        Abrir módulo completo
                        <ArrowRight className="size-4" />
                    </Link>
                </Button>
            </div>
        </div>
    );
}
