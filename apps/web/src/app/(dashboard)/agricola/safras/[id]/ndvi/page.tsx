"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { NdviTalhao } from "@/components/agricola/ndvi-talhao";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";
import { Satellite } from "lucide-react";
import Link from "next/link";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";
import { getSafraLabel } from "@/lib/safra-label";

interface Safra {
    id: string;
    cultura: string | null;
    ano_safra: string;
}

interface Talhao {
    id: string;
    nome: string;
}

export default function NdviPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.ndvi",
        surface: "agricola.ndvi.page",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });

    const { data: safra, isLoading: loadingSafra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = safra ? getSafraLabel(safra) : "";

    const { data: talhoes = [], isLoading: loadingTalhoes } = useQuery<Talhao[]>({
        queryKey: ["safra-talhoes", id],
        queryFn: () => apiFetch(`/safras/${id}/talhoes`),
        enabled: !!safra,
    });

    if (loadingSafra || loadingTalhoes || !safra) {
        return (
            <div className="space-y-4 p-8">
                <Skeleton className="h-10 w-72" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    if (!hasProfessionalTier) {
        return (
            <div className="space-y-6 p-6">
                <PageHeader
                    title="NDVI — Índice de Vegetação"
                    icon={<Satellite className="text-sky-600" size={22} />}
                    description={`${safraLabel} · Dados Sentinel-2`}
                />
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>NDVI disponível no PROFISSIONAL</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>O plano atual mantém o acesso à safra. Série temporal, sincronização Sentinel-2 e análise de vegetação exigem plano Profissional.</p>
                        <Button
                            asChild
                            size="sm"
                            className="rounded-sm"
                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                feature: "agricola.ndvi",
                                surface: "agricola.ndvi.page",
                                requiredTier: "PROFISSIONAL",
                                ctaLabel: "Ver planos",
                            })}
                        >
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="NDVI — Índice de Vegetação"
                icon={<Satellite className="text-sky-600" size={22} />}
                description={`${safraLabel} · Dados Sentinel-2`}
            />
            {talhoes.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhum talhão vinculado a esta safra.</p>
            ) : (
                <NdviTalhao talhoes={talhoes} />
            )}
        </div>
    );
}
