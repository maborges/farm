"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { Plus, Beaker } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Sheet } from "@/components/ui/sheet";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PageHeader } from "@/components/shared/page-header";

import { AnalisesKPIs } from "./analises-kpis";
import { AnalisesCharts } from "./analises-charts";
import { AnalisesGrid } from "./analises-grid";
import { LaudoSheet } from "./laudo-sheet";
import { NovaAnaliseModal } from "./nova-analise-modal";
import { EditAnaliseModal, type AnaliseSoloEditData } from "./edit-analise-modal";
import {
    formatTalhaoLabel,
    type TalhaoTerritorialRef,
    type UnidadeProdutivaRef,
} from "./territory-labels";

interface AnaliseSolo {
    id: string;
    talhao_id: string;
    talhao_nome?: string | null;
    data_coleta: string;
    laboratorio?: string;
    codigo_amostra?: string;
    profundidade_cm?: number;
    ph_agua?: number;
    ph_cacl2?: number;
    materia_organica_pct?: number;
    fosforo_p?: number;
    potassio_k?: number;
    calcio_ca?: number;
    magnesio_mg?: number;
    aluminio_al?: number;
    hidrogenio_al_hal?: number;
    ctc?: number;
    v_pct?: number;
    argila_pct?: number;
    created_at: string;
}

interface CulturaApi {
    id: string | number;
    nome: string;
    grupo?: string | null;
    sistema?: boolean | null;
    v_meta_pct_padrao?: number | null;
}

interface CulturaDisponivel {
    id: string;
    nome: string;
    grupo: string | null;
    sistema: boolean;
    v_meta_pct_padrao: number | null;
}

function normalizarCultura(cultura: CulturaApi): CulturaDisponivel {
    return {
        id: String(cultura.id),
        nome: String(cultura.nome),
        grupo: cultura.grupo ?? null,
        sistema: Boolean(cultura.sistema),
        v_meta_pct_padrao: cultura.v_meta_pct_padrao ?? null,
    };
}

function deduplicarCulturas(culturas: CulturaDisponivel[]): CulturaDisponivel[] {
    const porChave = new Map<string, CulturaDisponivel>();
    for (const cultura of culturas) {
        const chave = cultura.id || cultura.nome.toLowerCase();
        if (!porChave.has(chave)) {
            porChave.set(chave, cultura);
        }
    }
    return [...porChave.values()].sort((a, b) => {
        const grupoA = (a.grupo ?? "OUTRO").localeCompare(b.grupo ?? "OUTRO", "pt-BR");
        if (grupoA !== 0) return grupoA;
        return a.nome.localeCompare(b.nome, "pt-BR");
    });
}

interface Recomendacao {
    cultura: string;
    calagem?: { necessaria: boolean; dose_t_ha: number; v_atual_pct: number; v_meta_pct: number; observacao: string; };
    fosforo?: { nivel: string; label: string; rec_p2o5_kg_ha: number; observacao: string; };
    potassio?: { nivel: string; label: string; rec_k2o_kg_ha: number; observacao: string; };
    nitrogenio?: { rec_n_kg_ha: number; observacao: string; };
    interpretacoes: {
        ph?: { nivel: string; label: string; cor: string };
        materia_organica?: { nivel: string; label: string };
        fosforo?: { nivel: string; label: string };
        potassio?: { nivel: string; label: string };
    };
}

export function AnalisesClient() {
    const qc = useQueryClient();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [culturaId, setCulturaId] = useState<string>("");
    const [culturaNome, setCulturaNome] = useState("Soja");
    const [showNovaAnalise, setShowNovaAnalise] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [editId, setEditId] = useState<string | null>(null);

    const { data: analises = [] } = useQuery<AnaliseSolo[]>({
        queryKey: ["analises-solo"],
        queryFn: async () => {
            try {
                return await apiFetch<AnaliseSolo[]>("/analises-solo/");
            } catch (err) {
                console.warn("Failed to fetch analises", err);
                return [];
            }
        },
    });

    const { data: talhoes = [] } = useQuery<TalhaoTerritorialRef[]>({
        queryKey: ["talhoes", "analises-solo"],
        queryFn: async () => {
            try {
                return await apiFetch<TalhaoTerritorialRef[]>("/cadastros/areas-rurais/?tipo=TALHAO");
            } catch (err) {
                console.warn("Failed to fetch talhoes", err);
                return [];
            }
        },
    });

    const { data: unidadesProdutivas = [] } = useQuery<UnidadeProdutivaRef[]>({
        queryKey: ["unidades-produtivas", "analises-solo"],
        queryFn: async () => {
            try {
                return await apiFetch<UnidadeProdutivaRef[]>("/unidades-produtivas/");
            } catch (err) {
                console.warn("Failed to fetch unidades produtivas", err);
                return [];
            }
        },
    });

    const { data: culturas = [] } = useQuery<CulturaDisponivel[]>({
        queryKey: ["culturas-disponiveis-solo"],
        queryFn: async () => {
            const fontes = [
                () => apiFetch<CulturaApi[]>("/analises-solo/culturas-disponiveis"),
                () => apiFetch<CulturaApi[]>("/cadastros/culturas", { params: { ativa: true } }),
            ];

            const culturasColetadas: CulturaDisponivel[] = [];
            for (const source of fontes) {
                try {
                    const lista = await source();
                    culturasColetadas.push(...lista.map(normalizarCultura));
                } catch (err) {
                    console.warn("Failed to fetch culturas", err);
                }
            }

            return deduplicarCulturas(culturasColetadas);
        },
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (culturas.length === 0) return;
        const cafe = culturas.find((cultura) => cultura.nome.toLowerCase().includes("cafe") || cultura.nome.toLowerCase().includes("caf\u00e9"));
        console.log("[AnalisesSolo] culturas carregadas", {
            total: culturas.length,
            nomes: culturas.map((cultura) => cultura.nome),
            cafe,
        });
    }, [culturas]);

    const { data: recomendacao = null, isLoading: loadingRec } = useQuery<Recomendacao | null>({
        queryKey: ["recomendacao-solo", selectedId, culturaId, culturaNome],
        queryFn: () => {
            const params = new URLSearchParams({ cultura: culturaNome });
            if (culturaId) params.set("cultura_id", culturaId);
            return apiFetch<Recomendacao>(`/analises-solo/${selectedId}/recomendacoes?${params}`);
        },
        enabled: !!selectedId && hasProfessionalTier,
    });

    function handleCulturaChange(id: string, nome: string) {
        setCulturaId(id);
        setCulturaNome(nome);
    }

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/analises-solo/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["analises-solo"] });
            toast.success("Análise removida com sucesso");
        },
        onError: () => toast.error("Erro ao excluir análise"),
    });

    const selectedAnalise = analises.find(a => a.id === selectedId) ?? null;

    function getTalhaoNome(id: string) {
        const talhao = talhoes.find(t => t.id === id);
        if (!talhao) return "Talhão não informado";
        return formatTalhaoLabel(talhao, unidadesProdutivas);
    }

    const latestPerTalhao = talhoes
        .map(t => {
            const sorted = analises
                .filter(a => a.talhao_id === t.id)
                .sort((a, b) => new Date(b.data_coleta).getTime() - new Date(a.data_coleta).getTime());
            const lat = sorted[0];
            if (!lat) return null;
            return {
                nome: formatTalhaoLabel(t, unidadesProdutivas),
                v_pct: lat.v_pct ?? null,
                ph: lat.ph_agua ?? null,
            };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Análise de Solo"
                description="Gestão analítica de fertilidade. Monitore V% e receba recomendações de calagem e adubação."
                icon={<Beaker className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Análise de Solo" }]}
                actions={
                    <Button variant="outline" size="sm" onClick={() => setShowNovaAnalise(true)}>
                        <Plus className="mr-1.5 size-3.5" /> Nova Amostragem
                    </Button>
                }
            />

            <AnalisesKPIs data={latestPerTalhao} />

            <AnalisesCharts data={latestPerTalhao} />

            <AnalisesGrid
                data={analises}
                onView={setSelectedId}
                onEdit={(id) => setEditId(id)}
                onDelete={(id) => setDeleteId(id)}
                getTalhaoNome={getTalhaoNome}
            />

            <Sheet open={!!selectedId} onOpenChange={open => !open && setSelectedId(null)}>
                <LaudoSheet
                    analise={selectedAnalise}
                    recomendacao={recomendacao}
                    isLoading={hasProfessionalTier && loadingRec}
                    hasProfessionalTier={hasProfessionalTier}
                    talhaoNome={selectedId ? getTalhaoNome(selectedAnalise?.talhao_id ?? "") : ""}
                    cultura={culturaId || culturaNome}
                    culturas={culturas}
                    onCulturaChange={handleCulturaChange}
                />
            </Sheet>

            {editId && (() => {
                const a = analises.find(x => x.id === editId);
                if (!a) return null;
                const editData: AnaliseSoloEditData = { ...a, talhao_nome: getTalhaoNome(a.talhao_id) };
                return <EditAnaliseModal analise={editData} onClose={() => setEditId(null)} />;
            })()}

            {showNovaAnalise && (
                <NovaAnaliseModal
                    onClose={() => setShowNovaAnalise(false)}
                />
            )}

            <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Excluir análise de solo?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. O laudo será removido permanentemente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => deleteId && deleteMutation.mutate(deleteId)}
                        >
                            Excluir
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
