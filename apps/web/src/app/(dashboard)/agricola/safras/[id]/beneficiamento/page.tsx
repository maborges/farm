"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { BeneficiamentoCafe } from "@/components/agricola/beneficiamento-cafe";
import { Skeleton } from "@/components/ui/skeleton";
import { getSafraLabel } from "@/lib/safra-label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Coffee, Lock } from "lucide-react";
import Link from "next/link";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Safra { id: string; cultura: string | null; ano_safra: string; }
interface Talhao { id: string; nome: string; }

export default function BeneficiamentoPage() {
    const { id } = useParams<{ id: string }>();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.beneficiamento.safra",
        surface: "agricola.beneficiamento.safra.page",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });

    const { data: safra, isLoading: loadingSafra } = useQuery<Safra>({
        queryKey: ["safra", id],
        queryFn: () => apiFetch(`/safras/${id}`),
    });
    const safraLabel = getSafraLabel(safra);

    const { data: talhoesSafra = [], isLoading: loadingTalhoes } = useQuery<{ area_id: string }[]>({
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

    if (loadingSafra || loadingTalhoes) {
        return <div className="space-y-4 p-8"><Skeleton className="h-10 w-64" /><Skeleton className="h-48 w-full" /></div>;
    }

    if (!hasProfessionalTier) {
        return (
            <div className="space-y-6 p-6">
                <PageHeader
                    title={`Beneficiamento — ${safraLabel}`}
                    icon={<Coffee className="text-orange-600" size={22} />}
                    description={safraLabel}
                />
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Beneficiamento disponível no PROFISSIONAL</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>O plano atual mantém a safra aberta. Lotes, KPIs e relatório de rendimento exigem tier PROFISSIONAL.</p>
                        <Button
                            asChild
                            size="sm"
                            className="rounded-sm"
                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                feature: "agricola.beneficiamento.safra",
                                surface: "agricola.beneficiamento.safra.page",
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
                title={`Beneficiamento — ${safraLabel}`}
                icon={<Coffee className="text-orange-600" size={22} />}
                description={safraLabel}
            />
            <BeneficiamentoCafe safraId={id} talhoes={talhoes} />
        </div>
    );
}
