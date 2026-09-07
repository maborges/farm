"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { FlaskConical, ChevronRight, ChevronLeft, CheckCircle2, XCircle, AlertTriangle, Droplets, Tractor, Clock, Lock } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnaliseSolo {
    id: string;
    data_coleta: string;
    laboratorio: string | null;
    codigo_amostra: string | null;
    ph_agua: number | null;
    fosforo_p: number | null;
    potassio_k: number | null;
    v_pct: number | null;
    saturacao_al_m_pct: number | null;
    tipo_irrigacao: string | null;
    sistema_manejo: string | null;
    cultura_nome: string | null;
    cultura_anterior: string | null;
    validade_meses: number | null;
    vencida: boolean;
}

interface TarefaSoloGerada {
    nutriente: string;
    descricao: string;
    dose_kg_ha: number | null;
    area_ha: number;
    quantidade_total_kg: number | null;
    nivel: string;
    obs: string | null;
}

interface Recomendacao {
    nivel: string;
    label: string;
    necessaria?: boolean;
    dose_t_ha?: number | null;
    rec_dose_kg_ha?: number | null;
    rec_p2o5_kg_ha?: number | null;
    rec_k2o_kg_ha?: number | null;
    rec_n_kg_ha?: number | null;
    obs?: string | null;
    observacao?: string | null;
}

interface MicronutrienteInterp {
    valor_mg_dm3: number;
    simbolo: string;
    nivel: string;
    label: string;
    alerta: boolean;
}

interface LaudoResponse {
    cultura: string;
    cultura_anterior: string | null;
    tipo_irrigacao: string | null;
    sistema_manejo: string | null;
    regiao: string | null;
    fonte_parametros: string;
    vencida: boolean;
    calagem: Recomendacao | null;
    fosforo: Recomendacao | null;
    potassio: Recomendacao | null;
    nitrogenio: Recomendacao | null;
    micronutrientes: Record<string, MicronutrienteInterp>;
}

export interface CultivoAreaInfo {
    id: string;
    area_id: string;
    area_ha: number;
    area_nome?: string;
    analise_solo_id?: string | null;
    analise_status?: string;
    regiao_analise?: string | null;
    cultivo_id: string;
    safra_id: string;
    cultivar_id?: string | null;
    cultura: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const IRRIGACAO_LABEL: Record<string, string> = {
    SEQUEIRO: "Sequeiro",
    GOTEJAMENTO: "Gotejamento",
    PIVO_CENTRAL: "Pivô Central",
    ASPERSAO: "Aspersão",
    SULCO: "Sulco",
};

const MANEJO_LABEL: Record<string, string> = {
    PLANTIO_DIRETO: "Plantio Direto",
    CONVENCIONAL: "Convencional",
    MINIMO: "Cultivo Mínimo",
};

const REGIOES = [
    { value: "_geral", label: "Geral (padrão sistema)" },
    { value: "CERRADO", label: "Cerrado" },
    { value: "SUL", label: "Sul" },
    { value: "NORDESTE", label: "Nordeste" },
    { value: "SUDESTE", label: "Sudeste" },
    { value: "NORTE", label: "Norte" },
];

const NIVEL_COLOR: Record<string, string> = {
    MUITO_BAIXO: "text-red-600 bg-red-50",
    BAIXO: "text-orange-600 bg-orange-50",
    MEDIO: "text-yellow-700 bg-yellow-50",
    ALTO: "text-emerald-700 bg-emerald-50",
    MUITO_ALTO: "text-emerald-800 bg-emerald-100",
};

const NIVEL_BORDER: Record<string, string> = {
    MUITO_BAIXO: "border-l-red-400",
    BAIXO: "border-l-orange-400",
    MEDIO: "border-l-yellow-400",
    ALTO: "border-l-emerald-400",
    MUITO_ALTO: "border-l-emerald-600",
};

const STEPS = ["Análise", "Região", "Laudo", "Confirmar"];

function fmtDate(d: string) {
    try { return format(new Date(d), "dd/MM/yyyy", { locale: ptBR }); }
    catch { return d; }
}

function fmtNum(n: number | null | undefined, suffix = "") {
    if (n == null) return "—";
    return `${n.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}${suffix}`;
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepBar({ current }: { current: number }) {
    return (
        <div className="flex items-center gap-0 mt-3">
            {STEPS.map((label, i) => {
                const num = i + 1;
                const done = current > num;
                const active = current === num;
                return (
                    <div key={i} className="flex items-center flex-1 last:flex-none">
                        <div className="flex flex-col items-center gap-1 min-w-0">
                            <div className={cn(
                                "size-6 rounded-full flex items-center justify-center text-[11px] font-semibold border-2 transition-colors shrink-0",
                                done ? "bg-primary border-primary text-primary-foreground" :
                                active ? "border-primary text-primary bg-background" :
                                "border-muted text-muted-foreground bg-background"
                            )}>
                                {done ? <CheckCircle2 className="size-3.5" /> : num}
                            </div>
                            <span className={cn(
                                "text-[10px] leading-tight text-center whitespace-nowrap",
                                active ? "text-primary font-medium" : "text-muted-foreground"
                            )}>
                                {label}
                            </span>
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className={cn(
                                "h-px flex-1 mx-1 mb-4 transition-colors",
                                done ? "bg-primary" : "bg-muted"
                            )} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Rec card
// ---------------------------------------------------------------------------

function RecCard({ label, rec, unidade, campo, areaHa }: {
    label: string;
    rec: Recomendacao | null | undefined;
    unidade: string;
    campo: string;
    areaHa: number;
}) {
    if (!rec) return null;
    const dose = rec[campo as keyof Recomendacao] as number | null;
    const total = dose != null ? dose * areaHa : null;
    const borderColor = NIVEL_BORDER[rec.nivel] ?? "border-l-muted";
    return (
        <Card className={cn("border-l-4 space-y-2", borderColor)}>
            <div className="flex items-start justify-between gap-2 px-3 pt-3">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide leading-tight">{label}</span>
                <Badge className={cn("text-[10px] h-5 shrink-0", NIVEL_COLOR[rec.nivel] ?? "bg-muted text-muted-foreground")}>
                    {rec.label}
                </Badge>
            </div>
            <div className="px-3">
                {dose != null ? (
                    <div className="space-y-0.5">
                        <p className="text-lg font-bold leading-none tabular-nums">
                            {fmtNum(dose)}
                            <span className="text-xs font-normal text-muted-foreground ml-1">{unidade}</span>
                        </p>
                        {total != null && (
                            <p className="text-xs text-muted-foreground tabular-nums">
                                {fmtNum(total)} {unidade.startsWith("t") ? "t total" : "kg total"}
                            </p>
                        )}
                    </div>
                ) : (
                    <p className="text-xs text-muted-foreground">Sem recomendação</p>
                )}
            </div>
            {rec.obs && <p className="text-[11px] text-muted-foreground italic border-t px-3 py-2 pb-3">{rec.obs}</p>}
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Main drawer
// ---------------------------------------------------------------------------

interface Props {
    area: CultivoAreaInfo;
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function CultivoAnaliseSoloDrawer({ area, open, onClose, onSuccess }: Props) {
    const queryClient = useQueryClient();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.soil_intelligence",
        surface: "agricola.cultivo_analise.drawer",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });
    const [step, setStep] = useState(1);
    const [analiseId, setAnaliseId] = useState<string>(area.analise_solo_id ?? "");
    const [regiao, setRegiao] = useState<string>(area.regiao_analise || "_geral");

    const regiaoParam = regiao === "_geral" ? "" : regiao;

    // Step 1 — análises recentes do talhão
    const { data: analises = [], isLoading: loadingAnalises } = useQuery<AnaliseSolo[]>({
        queryKey: ["analises-solo-area", area.area_id],
        queryFn: () => apiFetch(`/analises-solo/?talhao_id=${area.area_id}&limit=5`),
        enabled: open,
    });

    const selectedAnaliseId = analiseId || analises[0]?.id || "";

    // Step 3 — laudo
    const { data: laudo, isLoading: loadingLaudo } = useQuery<LaudoResponse>({
        queryKey: ["analise-laudo", selectedAnaliseId, regiaoParam, area.cultivar_id],
        queryFn: () => {
            const p = new URLSearchParams();
            if (area.cultivar_id) p.set("cultura_id", area.cultivar_id);
            p.set("cultura", area.cultura);
            if (regiaoParam) p.set("regiao", regiaoParam);
            return apiFetch(`/analises-solo/${selectedAnaliseId}/recomendacoes?${p}`);
        },
        enabled: step === 3 && !!selectedAnaliseId && hasProfessionalTier,
    });

    // Step 4 — preview tarefas
    const { data: tarefas = [], isLoading: loadingTarefas } = useQuery<TarefaSoloGerada[]>({
        queryKey: ["tarefas-solo-preview", area.id, selectedAnaliseId, regiaoParam],
        queryFn: () => {
            const p = new URLSearchParams({ analise_id: selectedAnaliseId });
            if (regiaoParam) p.set("regiao", regiaoParam);
            return apiFetch(`/safras/${area.safra_id}/cultivos/${area.cultivo_id}/areas/${area.id}/tarefas-solo?${p}`);
        },
        enabled: step === 4 && !!selectedAnaliseId && hasProfessionalTier,
    });

    const vincularMut = useMutation({
        mutationFn: (status: "SELECIONADA" | "REJEITADA") =>
            apiFetch(`/safras/${area.safra_id}/cultivos/${area.cultivo_id}/areas/${area.id}/analise`, {
                method: "PATCH",
                body: JSON.stringify({
                    analise_solo_id: status === "SELECIONADA" ? selectedAnaliseId : null,
                    regiao_analise: regiaoParam || null,
                    analise_status: status,
                }),
            }),
        onSuccess: (_, status) => {
            queryClient.invalidateQueries({ queryKey: ["safra-cultivos"] });
            toast.success(status === "SELECIONADA" ? "Análise vinculada!" : "Talhão sem análise.");
            onSuccess();
            handleClose();
        },
        onError: () => toast.error("Erro ao salvar. Tente novamente."),
    });

    const NUTRIENTE_TIPO: Record<string, string> = {
        calagem: "CALAGEM",
        fosforo: "ADUBACAO_FOSFORO",
        potassio: "ADUBACAO_POTASSIO",
        nitrogenio: "ADUBACAO_NITROGENIO",
    };

    const confirmarComTarefasMut = useMutation({
        mutationFn: async () => {
            if (!hasProfessionalTier) {
                trackMonetizationEvent("monetization_blocked", {
                    feature: "agricola.soil_intelligence.confirm_tasks",
                    surface: "agricola.cultivo_analise.drawer",
                    requiredTier: "PROFISSIONAL",
                    ctaLabel: "Confirmar",
                    reason: "mutation_guard",
                });
                throw new Error("Recurso disponível no plano PROFISSIONAL.");
            }
            // 1. Vincula análise ao cultivo area
            await apiFetch(`/safras/${area.safra_id}/cultivos/${area.cultivo_id}/areas/${area.id}/analise`, {
                method: "PATCH",
                body: JSON.stringify({
                    analise_solo_id: selectedAnaliseId,
                    regiao_analise: regiaoParam || null,
                    analise_status: "SELECIONADA",
                }),
            });
            // 2. Persiste UMA única tarefa consolidando os itens necessários (calagem,
            // fósforo, potássio, nitrogênio). Os produtos comerciais e as quantidades
            // reais de cada item são escolhidos depois, na etapa de Planejamento
            // Operacional — aqui só registramos a necessidade agronômica combinada.
            if (tarefas && tarefas.length > 0) {
                const descricao =
                    tarefas.length === 1
                        ? tarefas[0].descricao
                        : `Correção de solo — ${tarefas.map((t) => t.descricao).join(", ")}`;
                const obs = tarefas
                    .map((t) => {
                        const partes = [t.descricao];
                        if (t.dose_kg_ha != null) partes.push(`${t.dose_kg_ha} kg/ha`);
                        if (t.quantidade_total_kg != null) partes.push(`${t.quantidade_total_kg} kg total`);
                        if (t.obs) partes.push(t.obs);
                        return partes.join(" — ");
                    })
                    .join("\n");

                await apiFetch(`/safras/${area.safra_id}/tarefas`, {
                    method: "POST",
                    body: JSON.stringify({
                        talhao_id: area.area_id,
                        cultivo_area_id: area.id,
                        analise_solo_id: selectedAnaliseId,
                        origem: "SOLO",
                        tipo: tarefas.length === 1 ? (NUTRIENTE_TIPO[tarefas[0].nutriente] ?? "OUTRO") : "CORRECAO_SOLO",
                        descricao,
                        obs,
                        prioridade: "ALTA",
                        area_ha: tarefas[0].area_ha,
                    }),
                });
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safra-cultivos"] });
            queryClient.invalidateQueries({ queryKey: ["safras", area.safra_id, "tarefas"] });
            const n = tarefas?.length ?? 0;
            toast.success(
                `Análise vinculada${n > 0 ? ` e 1 tarefa gerada para aprovação${n > 1 ? ` (${n} itens: ${tarefas!.map((t) => t.descricao).join(", ")})` : ""}` : ""}!`
            );
            onSuccess();
            handleClose();
        },
        onError: () => toast.error("Erro ao salvar. Tente novamente."),
    });

    function handleClose() {
        setStep(1);
        setAnaliseId(area.analise_solo_id ?? "");
        setRegiao(area.regiao_analise || "_geral");
        onClose();
    }

    const analiseSelected = analises.find(a => a.id === selectedAnaliseId);

    return (
        <Sheet open={open} onOpenChange={handleClose}>
            <SheetContent className="sm:max-w-md flex flex-col gap-0 p-0">
                {/* Header */}
                <SheetHeader className="px-4 pt-4 pb-3 border-b">
                    <div className="flex items-center gap-2">
                        <FlaskConical className="size-4 text-amber-600 shrink-0" />
                        <SheetTitle className="text-base">Análise de Solo</SheetTitle>
                    </div>
                    <SheetDescription className="text-xs">
                        {area.area_nome ?? "Talhão"} · {area.area_ha.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha · {area.cultura}
                    </SheetDescription>
                    <StepBar current={step} />
                </SheetHeader>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">

                    {/* ── STEP 1: Selecionar análise ── */}
                    {step === 1 && (
                        <>
                            <p className="text-sm text-muted-foreground">Selecione uma análise cadastrada para este talhão:</p>

                            {loadingAnalises && (
                                <div className="space-y-2">
                                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
                                </div>
                            )}

                            {!loadingAnalises && analises.length === 0 && (
                                <div className="rounded-lg border border-dashed p-6 text-center space-y-2">
                                    <AlertTriangle className="size-5 mx-auto text-amber-500" />
                                    <p className="text-sm text-muted-foreground">Nenhuma análise cadastrada para este talhão.</p>
                                    <Link href="/agricola/analises-solo" className="text-xs text-primary underline">
                                        Cadastrar análise
                                    </Link>
                                </div>
                            )}

                            <div className="space-y-2">
                                {analises.map(a => (
                                    <button
                                        key={a.id}
                                        onClick={() => setAnaliseId(a.id)}
                                        className={cn(
                                            "w-full text-left rounded-lg border p-3 transition-colors hover:border-primary/60",
                                            selectedAnaliseId === a.id
                                                ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                                : "border-border"
                                        )}
                                    >
                                        <div className="flex items-center justify-between mb-1.5">
                                            <span className="text-sm font-medium">{fmtDate(a.data_coleta)}</span>
                                            {selectedAnaliseId === a.id
                                                ? <CheckCircle2 className="size-4 text-primary" />
                                                : <div className="size-4 rounded-full border-2 border-muted" />
                                            }
                                        </div>
                                        <div className="grid grid-cols-3 gap-x-3 text-xs text-muted-foreground">
                                            {a.ph_agua != null && <span>pH {a.ph_agua}</span>}
                                            {a.fosforo_p != null && <span>P {a.fosforo_p} mg/dm³</span>}
                                            {a.v_pct != null && <span>V% {a.v_pct}%</span>}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                            {a.tipo_irrigacao && (
                                                <span className="flex items-center gap-0.5 text-[10px] text-blue-600 bg-blue-50 rounded px-1.5 py-0.5">
                                                    <Droplets className="size-2.5" />
                                                    {IRRIGACAO_LABEL[a.tipo_irrigacao] ?? a.tipo_irrigacao}
                                                </span>
                                            )}
                                            {a.sistema_manejo && (
                                                <span className="flex items-center gap-0.5 text-[10px] text-amber-700 bg-amber-50 rounded px-1.5 py-0.5">
                                                    <Tractor className="size-2.5" />
                                                    {MANEJO_LABEL[a.sistema_manejo] ?? a.sistema_manejo}
                                                </span>
                                            )}
                                            {a.vencida && (
                                                <span className="flex items-center gap-0.5 text-[10px] text-red-600 bg-red-50 rounded px-1.5 py-0.5 font-medium">
                                                    <Clock className="size-2.5" />
                                                    Vencida
                                                </span>
                                            )}
                                        </div>
                                        {(a.laboratorio || a.codigo_amostra) && (
                                            <p className="text-[10px] text-muted-foreground mt-1">
                                                {[a.laboratorio, a.codigo_amostra].filter(Boolean).join(" · ")}
                                            </p>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </>
                    )}

                    {/* ── STEP 2: Região ── */}
                    {step === 2 && (
                        <>
                            <p className="text-sm text-muted-foreground">
                                Região para lookup de parâmetros de calagem e adubação:
                            </p>
                            <Select value={regiao} onValueChange={setRegiao}>
                                <SelectTrigger>
                                    <span className="text-sm">
                                        {REGIOES.find(r => r.value === regiao)?.label ?? "Selecionar região..."}
                                    </span>
                                </SelectTrigger>
                                <SelectContent>
                                    {REGIOES.map(r => (
                                        <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                                Se não selecionada, usa os valores gerais do sistema (fallback Embrapa).
                            </p>

                            {analiseSelected && (
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-xs space-y-1">
                                    <p className="font-medium text-foreground">Análise selecionada</p>
                                    <p className="text-muted-foreground">{fmtDate(analiseSelected.data_coleta)}</p>
                                </div>
                            )}
                        </>
                    )}

                    {/* ── STEP 3: Laudo ── */}
                    {step === 3 && (
                        <>
                            {!hasProfessionalTier && (
                                <Alert className="rounded-sm">
                                    <Lock className="size-4" />
                                    <AlertTitle>Laudo inteligente disponível no PROFISSIONAL</AlertTitle>
                                    <AlertDescription className="space-y-3">
                                        <p>
                                            A análise pode permanecer vinculada ao talhão. Recomendações automáticas e geração de tarefas exigem tier PROFISSIONAL.
                                        </p>
                                        <Button
                                            asChild
                                            size="sm"
                                            className="rounded-sm"
                                            onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                                feature: "agricola.soil_intelligence",
                                                surface: "agricola.cultivo_analise.drawer",
                                                requiredTier: "PROFISSIONAL",
                                                ctaLabel: "Ver planos",
                                            })}
                                        >
                                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                                        </Button>
                                    </AlertDescription>
                                </Alert>
                            )}

                            {loadingLaudo && (
                                <div className="space-y-2">
                                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
                                </div>
                            )}

                            {laudo && !loadingLaudo && (
                                <>
                                    {/* Alerta validade */}
                                    {laudo.vencida && (
                                        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                                            <Clock className="size-3.5 shrink-0" />
                                            Análise com validade vencida. Recomendações podem estar desatualizadas.
                                        </div>
                                    )}

                                    {/* Cabeçalho + contexto */}
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <p className="text-sm font-medium flex-1">Recomendações — {laudo.cultura}</p>
                                        <Badge variant="outline" className="text-[10px]">
                                            {laudo.fonte_parametros === "cadastro" ? "Parâmetros cadastrados" : "Embrapa"}
                                        </Badge>
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {laudo.tipo_irrigacao && (
                                            <span className="flex items-center gap-0.5 text-[10px] text-blue-600 bg-blue-50 rounded px-1.5 py-0.5">
                                                <Droplets className="size-2.5" />
                                                {IRRIGACAO_LABEL[laudo.tipo_irrigacao] ?? laudo.tipo_irrigacao}
                                            </span>
                                        )}
                                        {laudo.sistema_manejo && (
                                            <span className="flex items-center gap-0.5 text-[10px] text-amber-700 bg-amber-50 rounded px-1.5 py-0.5">
                                                <Tractor className="size-2.5" />
                                                {MANEJO_LABEL[laudo.sistema_manejo] ?? laudo.sistema_manejo}
                                            </span>
                                        )}
                                        {laudo.cultura_anterior && (
                                            <span className="text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                                                Ant.: {laudo.cultura_anterior}
                                            </span>
                                        )}
                                    </div>

                                    {/* Macronutrientes */}
                                    <div className="grid grid-cols-2 gap-2">
                                        <RecCard label="Calagem" rec={laudo.calagem} unidade="t/ha" campo="dose_t_ha" areaHa={area.area_ha} />
                                        <RecCard label="Fósforo (P₂O₅)" rec={laudo.fosforo} unidade="kg/ha" campo="rec_dose_kg_ha" areaHa={area.area_ha} />
                                        <RecCard label="Potássio (K₂O)" rec={laudo.potassio} unidade="kg/ha" campo="rec_k2o_kg_ha" areaHa={area.area_ha} />
                                        <RecCard label="Nitrogênio" rec={laudo.nitrogenio} unidade="kg/ha" campo="rec_n_kg_ha" areaHa={area.area_ha} />
                                    </div>

                                    {/* Micronutrientes */}
                                    {Object.keys(laudo.micronutrientes).length > 0 && (
                                        <div className="space-y-1.5">
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Micronutrientes</p>
                                            <div className="grid grid-cols-2 gap-2">
                                                {Object.values(laudo.micronutrientes).map(mn => (
                                                    <div key={mn.simbolo} className={cn(
                                                        "rounded-lg border p-2.5 flex items-center justify-between gap-2",
                                                        mn.alerta ? "border-orange-200 bg-orange-50" : "bg-card"
                                                    )}>
                                                        <div>
                                                            <p className="text-xs font-semibold">{mn.simbolo}</p>
                                                            <p className="text-[10px] text-muted-foreground">{mn.valor_mg_dm3} mg/dm³</p>
                                                        </div>
                                                        <Badge className={cn("text-[10px] h-5", NIVEL_COLOR[mn.nivel] ?? "bg-muted")}>
                                                            {mn.label}
                                                        </Badge>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </>
                    )}

                    {/* ── STEP 4: Confirmar tarefas ── */}
                    {step === 4 && (
                        <>
                            {!hasProfessionalTier && (
                                <Alert className="rounded-sm">
                                    <Lock className="size-4" />
                                    <AlertTitle>Geração de tarefas por IA disponível no PROFISSIONAL</AlertTitle>
                                    <AlertDescription>
                                        O plano atual mantém a operação básica do cultivo. A automação de recomendações exige tier PROFISSIONAL.
                                    </AlertDescription>
                                </Alert>
                            )}

                            {loadingTarefas && (
                                <div className="space-y-2">
                                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}
                                </div>
                            )}

                            {!loadingTarefas && tarefas.length === 0 && (
                                <div className="rounded-lg border border-dashed p-5 text-center">
                                    <CheckCircle2 className="size-5 mx-auto text-emerald-600 mb-2" />
                                    <p className="text-sm text-muted-foreground">
                                        Todos os nutrientes em nível adequado. Nenhuma tarefa necessária.
                                    </p>
                                </div>
                            )}

                            {!loadingTarefas && tarefas.length > 0 && (
                                <>
                                    <p className="text-sm text-muted-foreground">
                                        {tarefas.length} tarefa{tarefas.length > 1 ? "s" : ""} serão criadas com status <strong>PENDENTE</strong>:
                                    </p>

                                    <div className="space-y-2">
                                        {tarefas.map((t, i) => (
                                            <Card key={i}>
                                                <div className="flex items-center justify-between gap-2 px-3 pt-3 pb-1">
                                                    <span className="text-sm font-medium">{t.descricao}</span>
                                                    <Badge className={cn("text-[10px] h-5 shrink-0", NIVEL_COLOR[t.nivel] ?? "")}>
                                                        {t.nivel.replace("_", " ")}
                                                    </Badge>
                                                </div>
                                                <div className="px-3 grid grid-cols-2 gap-x-4 text-xs text-muted-foreground">
                                                    {t.dose_kg_ha != null && (
                                                        <span>{fmtNum(t.dose_kg_ha)} kg/ha</span>
                                                    )}
                                                    {t.quantidade_total_kg != null && (
                                                        <span>{fmtNum(t.quantidade_total_kg)} kg total</span>
                                                    )}
                                                </div>
                                                {t.obs && <p className="px-3 text-xs text-muted-foreground italic mt-1 pb-3">{t.obs}</p>}
                                            </Card>
                                        ))}
                                    </div>

                                    <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2.5 text-xs text-amber-800">
                                        Tarefas ficam pendentes até aprovação do responsável.
                                    </div>
                                </>
                            )}

                            <div className="rounded-md border px-3 py-2.5 text-xs text-muted-foreground space-y-1.5">
                                <p><strong className="text-foreground">Só vincular</strong> — salva esta análise como a análise oficial do talhão. Não cria nenhuma tarefa; os itens listados acima ficam só como pré-visualização e são descartados.</p>
                                <p><strong className="text-foreground">Confirmar</strong> — vincula a análise <strong>e</strong> cria 1 tarefa de correção de solo (status Pendente de Aprovação), reunindo os {tarefas.length || "N"} itens acima. Os produtos comerciais de cada item são escolhidos depois, no Planejamento Operacional.</p>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer com ações */}
                <SheetFooter className="flex-col gap-2 border-t px-4 py-3">
                    {step === 1 && (
                        <div className="flex gap-2 w-full">
                            <Button
                                variant="outline"
                                className="flex-1"
                                onClick={() => vincularMut.mutate("REJEITADA")}
                                disabled={vincularMut.isPending}
                            >
                                <XCircle className="size-3.5 mr-1.5" />
                                Sem análise
                            </Button>
                            <Button
                                className="flex-1"
                                disabled={!selectedAnaliseId}
                                onClick={() => setStep(2)}
                            >
                                Próximo
                                <ChevronRight className="size-3.5 ml-1.5" />
                            </Button>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="flex gap-2 w-full">
                            <Button variant="outline" onClick={() => setStep(1)} className="gap-1.5">
                                <ChevronLeft className="size-3.5" /> Voltar
                            </Button>
                            <Button className="flex-1" onClick={() => setStep(3)}>
                                Ver laudo <ChevronRight className="size-3.5 ml-1.5" />
                            </Button>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="flex gap-2 w-full">
                            <Button variant="outline" onClick={() => setStep(2)} className="gap-1.5">
                                <ChevronLeft className="size-3.5" /> Voltar
                            </Button>
                            <Button
                                className="flex-1"
                                onClick={() => {
                                    if (!hasProfessionalTier) {
                                        trackMonetizationEvent("monetization_blocked", {
                                            feature: "agricola.soil_intelligence.generate_tasks",
                                            surface: "agricola.cultivo_analise.drawer",
                                            requiredTier: "PROFISSIONAL",
                                            ctaLabel: "Gerar tarefas",
                                            reason: "disabled_action",
                                        });
                                        return;
                                    }
                                    setStep(4);
                                }}
                                disabled={!hasProfessionalTier || !laudo}
                            >
                                Gerar tarefas <ChevronRight className="size-3.5 ml-1.5" />
                            </Button>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="flex gap-2 w-full">
                            <Button variant="outline" onClick={() => setStep(3)} className="gap-1.5">
                                <ChevronLeft className="size-3.5" /> Voltar
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => vincularMut.mutate("SELECIONADA")}
                                disabled={vincularMut.isPending}
                                title="Salva a análise no talhão, sem criar tarefa nenhuma."
                            >
                                Só vincular
                            </Button>
                            <Button
                                className="flex-1"
                                onClick={() => {
                                    if (!hasProfessionalTier) {
                                        trackMonetizationEvent("monetization_blocked", {
                                            feature: "agricola.soil_intelligence.confirm_tasks",
                                            surface: "agricola.cultivo_analise.drawer",
                                            requiredTier: "PROFISSIONAL",
                                            ctaLabel: "Confirmar",
                                            reason: "disabled_action",
                                        });
                                        return;
                                    }
                                    confirmarComTarefasMut.mutate();
                                }}
                                disabled={!hasProfessionalTier || confirmarComTarefasMut.isPending}
                                title="Salva a análise e cria 1 tarefa de correção de solo com todos os itens necessários."
                            >
                                {confirmarComTarefasMut.isPending ? "Salvando…" : "Confirmar"}
                            </Button>
                        </div>
                    )}
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
