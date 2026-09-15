"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { QrCode } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { RastreabilidadeLotes } from "@/components/agricola/rastreabilidade-lotes";
import { useHasTier } from "@/hooks/use-has-tier";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";
import Link from "next/link";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Safra { id: string; cultura: string; ano_safra: string; }

export default function RastreabilidadePage() {
    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch("/safras/"),
    });
    const hasEnterpriseTier = useHasTier("ENTERPRISE");

    useMonetizationPromptTracking(!hasEnterpriseTier, {
        feature: "agricola.rastreabilidade",
        surface: "agricola.rastreabilidade.page",
        requiredTier: "ENTERPRISE",
        ctaLabel: "Ver planos",
    });

    return (
        <div className="p-8 space-y-6 flex flex-col">
            <PageHeader
                title="Rastreabilidade"
                description="Lotes com QR code — do campo ao consumidor"
                icon={<QrCode className="text-primary" size={24} />}
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Rastreabilidade" },
                ]}
            />
            {!hasEnterpriseTier ? (
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Rastreabilidade disponível no ENTERPRISE</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>Lotes auditáveis, cadeia de rastreio e certificações exigem plano Enterprise.</p>
                        <Button
                            asChild
                            size="sm"
                            className="rounded-sm"
                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                feature: "agricola.rastreabilidade",
                                surface: "agricola.rastreabilidade.page",
                                requiredTier: "ENTERPRISE",
                                ctaLabel: "Ver planos",
                            })}
                        >
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            ) : (
                <RastreabilidadeLotes safras={safras} />
            )}
        </div>
    );
}
