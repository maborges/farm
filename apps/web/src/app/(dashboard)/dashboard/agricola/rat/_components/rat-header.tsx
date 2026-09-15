"use client";

import { useState } from "react";
import { Plus, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/shared/page-header";
import { RatFormModal } from "./rat-form-modal";
import { useHasTier } from "@/hooks/use-has-tier";
import { Lock } from "lucide-react";
import Link from "next/link";

export function RelatorioTecnicoHeader() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const hasProfessionalTier = useHasTier("PROFISSIONAL");

    return (
        <>
            <PageHeader
                title="Relatórios Técnicos (RAT)"
                description="Gestão de laudos, recomendações e monitoramento de campo."
                breadcrumbs={[
                    { label: "Agrícola", href: "/dashboard/agricola" },
                    { label: "Relatórios Técnicos" }
                ]}
                actions={
                    hasProfessionalTier ? (
                        <Button
                            size="sm"
                            className="rounded-sm"
                            onClick={() => setIsModalOpen(true)}
                        >
                            <Plus className="size-3.5 mr-1.5" />
                            Novo RAT
                        </Button>
                    ) : (
                        <Button asChild size="sm" variant="outline" className="rounded-sm">
                            <Link href="/dashboard/settings/billing">
                                <Lock className="size-3.5 mr-1.5" />
                                Ver planos
                            </Link>
                        </Button>
                    )
                }
            />
            {!hasProfessionalTier && (
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>RAT disponível no PROFISSIONAL</AlertTitle>
                    <AlertDescription>
                        Relatórios técnicos e prescrições agronômicas exigem plano Profissional.
                    </AlertDescription>
                </Alert>
            )}
            <RatFormModal 
                open={isModalOpen} 
                onOpenChange={setIsModalOpen} 
            />
        </>
    );
}
