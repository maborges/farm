"use client";

import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const FASES = [
    { key: "PLANEJADA",        label: "Planejamento",    cor: "bg-blue-500" },
    { key: "PREPARO_SOLO",     label: "Preparo Solo",    cor: "bg-amber-500" },
    { key: "PLANTIO",          label: "Plantio",         cor: "bg-lime-500" },
    { key: "DESENVOLVIMENTO",  label: "Desenvolvimento", cor: "bg-emerald-500" },
    { key: "COLHEITA",         label: "Colheita",        cor: "bg-orange-500" },
    { key: "POS_COLHEITA",     label: "Pós-Colheita",   cor: "bg-purple-500" },
];

interface SafraCard {
    id: string;
    cultura: string | null;
    ano_safra: string;
    status: string;
}

interface SafrasKanbanProps {
    safrasPorFase: Record<string, SafraCard[]>;
}

export function SafrasKanban({ safrasPorFase }: SafrasKanbanProps) {
    const router = useRouter();
    const fasesComDados = FASES.filter(f => (safrasPorFase[f.key]?.length ?? 0) > 0);

    if (fasesComDados.length === 0) {
        return (
            <div className="text-center py-12 text-muted-foreground text-sm">
                Nenhuma safra ativa encontrada.
            </div>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {fasesComDados.map(fase => {
                const safras = safrasPorFase[fase.key] ?? [];
                return (
                    <div key={fase.key} className="space-y-2">
                        {/* Header da coluna */}
                        <div className="flex items-center gap-2">
                            <div className={cn("size-2.5 rounded-full", fase.cor)} />
                            <span className="text-sm font-semibold">{fase.label}</span>
                            <Badge variant="secondary" className="text-xs ml-auto rounded-sm">{safras.length}</Badge>
                        </div>

                        {/* Cards de safra */}
                        <div className="flex flex-row flex-wrap gap-3">
                            {safras.map(safra => (
                                <Card
                                    key={safra.id}
                                    className="min-w-[180px] flex-1 shadow-sm rounded-sm cursor-pointer hover:border-primary/40 hover:shadow-md transition-all"
                                    onClick={() => router.push(`/agricola/safras/${safra.id}`)}
                                >
                                    <CardContent className="p-3">
                                        <p className="font-semibold text-sm">{safra.cultura ?? "—"}</p>
                                        <p className="text-xs text-muted-foreground">{safra.ano_safra}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
