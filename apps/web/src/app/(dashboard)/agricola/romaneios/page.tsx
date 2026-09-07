"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { RomaneiosColheita } from "@/components/agricola/romaneios-colheita";
import { Skeleton } from "@/components/ui/skeleton";

interface Safra {
    id: string;
    cultura: string;
    ano_safra: string;
    status: string;
}

interface Talhao {
    id: string;
    nome: string;
}

interface TalhaoSafra {
    area_id: string;
    nome: string | null;
    area_total_ha: number | null;
}

function formatarTalhao(nome: string | null, areaTotalHa: number | null) {
    const nomeTalhao = nome ?? "Talhão sem nome";
    if (areaTotalHa == null) return nomeTalhao;

    return `${nomeTalhao} — ${areaTotalHa.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha`;
}

export default function RomaneiosPage() {
    const [safraId, setSafraId] = useState<string>("");

    const { data: safras = [], isLoading: loadingSafras } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch("/safras"),
    });

    const { data: talhoesSafra = [], isLoading: loadingTalhoes } = useQuery<TalhaoSafra[]>({
        queryKey: ["safra-talhoes", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/talhoes`),
        enabled: !!safraId,
    });

    const talhoes: Talhao[] = talhoesSafra.map(({ area_id, nome, area_total_ha }) => ({
        id: area_id,
        nome: formatarTalhao(nome, area_total_ha),
    }));

    const safraSelecionada = safras.find(s => s.id === safraId);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Romaneios de Colheita"
                description="Registro e controle de peso, qualidade e produtividade por talhão"
                icon={<FileText className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Romaneios" },
                ]}
            />

            <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-muted-foreground whitespace-nowrap">Safra:</label>
                {loadingSafras ? (
                    <Skeleton className="h-9 w-48" />
                ) : (
                    <div className="min-w-48">
                        <Select value={safraId} onValueChange={setSafraId}>
                            <SelectTrigger className="h-9 rounded-sm">
                                <SelectValue placeholder="Selecione uma safra..." />
                            </SelectTrigger>
                            <SelectContent>
                                {safras.map(s => (
                                    <SelectItem key={s.id} value={s.id}>
                                        {s.cultura} — {s.ano_safra}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </div>

            {!safraId ? (
                <p className="text-sm text-muted-foreground text-center py-16">
                    Selecione uma safra para visualizar os romaneios.
                </p>
            ) : loadingTalhoes ? (
                <Skeleton className="h-48 w-full" />
            ) : (
                <RomaneiosColheita
                    safraId={safraId}
                    talhoes={talhoes}
                    cultura={safraSelecionada?.cultura}
                    anoSafra={safraSelecionada?.ano_safra}
                />
            )}
        </div>
    );
}
