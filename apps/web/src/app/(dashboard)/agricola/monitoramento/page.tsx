"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Bug, ChevronRight, Microscope } from "lucide-react";
import { cn } from "@/lib/utils";

interface Safra {
    id: string;
    cultura: string;
    ano_safra: string;
    status: string;
}

const STATUS_COR: Record<string, string> = {
    PLANEJADA: "bg-blue-100 text-blue-700",
    PREPARO_SOLO: "bg-amber-100 text-amber-700",
    PLANTIO: "bg-lime-100 text-lime-700",
    DESENVOLVIMENTO: "bg-emerald-100 text-emerald-700",
    COLHEITA: "bg-orange-100 text-orange-700",
    POS_COLHEITA: "bg-purple-100 text-purple-700",
};

const STATUS_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
};

export default function MonitoramentoGlobalPage() {
    const router = useRouter();

    const { data: safras = [], isLoading } = useQuery<Safra[]>({
        queryKey: ["safras-ativas"],
        queryFn: () => apiFetch("/safras/?encerradas=false"),
    });

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Pragas & Doenças"
                description="Selecione uma safra para registrar ou consultar monitoramentos de pragas, doenças e plantas daninhas."
                icon={<Bug className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Pragas & Doenças" },
                ]}
            />

            {isLoading ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-20" />)}
                </div>
            ) : safras.length === 0 ? (
                <div className="text-center py-16 text-muted-foreground text-sm">
                    Nenhuma safra ativa encontrada.
                </div>
            ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {safras.map(safra => (
                        <Card
                            key={safra.id}
                            className="cursor-pointer hover:border-primary/40 hover:shadow-md transition-all shadow-sm"
                            onClick={() => router.push(`/agricola/safras/${safra.id}/monitoramento`)}
                        >
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-sm bg-muted">
                                    <Bug className="size-5 text-muted-foreground" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-sm truncate">{safra.cultura ?? "Safra"}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {safra.ano_safra}
                                        
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    <Badge className={cn("text-xs", STATUS_COR[safra.status] ?? "bg-muted")}>
                                        {STATUS_LABEL[safra.status] ?? safra.status}
                                    </Badge>
                                    <ChevronRight className="size-4 text-muted-foreground" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
