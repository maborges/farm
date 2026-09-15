"use client";

import React from "react";
import { IAPlanoAcaoCard } from "@/components/ia/ia-plano-acao-card";
import { PageHeader } from "@/components/shared/page-header";
import { Separator } from "@/components/ui/separator";
import { useSearchParams } from "next/navigation";
import { Zap } from "lucide-react";

export default function IAPlanoAcaoPage() {
    const searchParams = useSearchParams();
    const safraId = searchParams.get("safra_id");

    const breadcrumbs = [
        { label: "Dashboard", href: "/dashboard" },
        { label: "IA", href: "/dashboard/ia/performance" },
        { label: "Plano de Ação" }
    ];

    return (
        <div className="flex flex-1 flex-col gap-6 p-6">
            <PageHeader 
                title="Plano de Ação"
                description="Estratégias geradas pela inteligência artificial para otimização da safra."
                icon={<Zap className="text-primary animate-pulse" size={24} />}
                breadcrumbs={breadcrumbs}
            />

            <Separator className="rounded-sm" />
            
            <div className="max-w-4xl mx-auto w-full">
                <IAPlanoAcaoCard safraId={safraId || undefined} />
            </div>
        </div>
    );
}
