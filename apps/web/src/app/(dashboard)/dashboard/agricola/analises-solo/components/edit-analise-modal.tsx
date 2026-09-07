"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { FlaskConical, Loader2, Save, ChevronRight, ChevronLeft, X } from "lucide-react";
import {
    Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

// ─── Types ────────────────────────────────────────────────────────────────────
export interface AnaliseSoloEditData {
    id: string;
    talhao_id: string;
    talhao_nome: string;
    data_coleta: string;
    laboratorio?: string | null;
    codigo_amostra?: string | null;
    profundidade_cm?: number | null;
    ph_agua?: number | null;
    ph_cacl2?: number | null;
    materia_organica_pct?: number | null;
    fosforo_p?: number | null;
    potassio_k?: number | null;
    calcio_ca?: number | null;
    magnesio_mg?: number | null;
    aluminio_al?: number | null;
    hidrogenio_al_hal?: number | null;
    ctc?: number | null;
    v_pct?: number | null;
    argila_pct?: number | null;
}

interface Props {
    analise: AnaliseSoloEditData;
    onClose: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function toNum(v: unknown) {
    if (v === "" || v === null || v === undefined) return undefined;
    const n = Number(v);
    return isNaN(n) ? undefined : n;
}
function optionalNumber() {
    return z.preprocess(toNum, z.number().optional());
}

// ─── Schema ──────────────────────────────────────────────────────────────────
const schema = z.object({
    data_coleta:         z.string().min(1, "Informe a data de coleta"),
    laboratorio:         z.string().optional(),
    codigo_amostra:      z.string().optional(),
    profundidade_cm:     optionalNumber(),
    ph_agua:             optionalNumber(),
    ph_cacl2:            optionalNumber(),
    materia_organica_pct: optionalNumber(),
    fosforo_p:           optionalNumber(),
    potassio_k:          optionalNumber(),
    calcio_ca:           optionalNumber(),
    magnesio_mg:         optionalNumber(),
    aluminio_al:         optionalNumber(),
    hidrogenio_al_hal:   optionalNumber(),
    ctc:                 optionalNumber(),
    v_pct:               optionalNumber(),
    argila_pct:          optionalNumber(),
});

type FormValues = z.infer<typeof schema>;

// ─── Component ───────────────────────────────────────────────────────────────
export function EditAnaliseModal({ analise, onClose }: Props) {
    const qc = useQueryClient();
    const [step, setStep] = useState<"geral" | "quimica">("geral");

    const form = useForm<FormValues>({
        resolver: zodResolver(schema) as any,
        defaultValues: {
            data_coleta:          analise.data_coleta ?? "",
            laboratorio:          analise.laboratorio ?? "",
            codigo_amostra:       analise.codigo_amostra ?? "",
            profundidade_cm:      analise.profundidade_cm ?? undefined,
            ph_agua:              analise.ph_agua ?? undefined,
            ph_cacl2:             analise.ph_cacl2 ?? undefined,
            materia_organica_pct: analise.materia_organica_pct ?? undefined,
            fosforo_p:            analise.fosforo_p ?? undefined,
            potassio_k:           analise.potassio_k ?? undefined,
            calcio_ca:            analise.calcio_ca ?? undefined,
            magnesio_mg:          analise.magnesio_mg ?? undefined,
            aluminio_al:          analise.aluminio_al ?? undefined,
            hidrogenio_al_hal:    analise.hidrogenio_al_hal ?? undefined,
            ctc:                  analise.ctc ?? undefined,
            v_pct:                analise.v_pct ?? undefined,
            argila_pct:           analise.argila_pct ?? undefined,
        },
    });

    const mutation = useMutation({
        mutationFn: (data: FormValues) =>
            apiFetch(`/analises-solo/${analise.id}`, { method: "PATCH", body: JSON.stringify(data) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["analises-solo"] });
            toast.success("Análise atualizada com sucesso!");
            onClose();
        },
        onError: () => toast.error("Erro ao atualizar análise de solo"),
    });

    function handleClose() {
        setStep("geral");
        onClose();
    }

    function onSubmit(values: FormValues) {
        mutation.mutate(values);
    }

    return (
        <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4 bg-black/50">
            <div className="bg-card w-full max-w-2xl rounded-sm shadow-xl border border-border">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <div className="flex items-center gap-3">
                        <div className="size-9 rounded-sm bg-[var(--module-agro-bg)] flex items-center justify-center">
                            <FlaskConical className="size-4 text-[var(--module-agro)]" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-sm">Editar Análise de Solo</h2>
                            <p className="text-xs text-muted-foreground">
                                Talhão: <span className="font-medium text-foreground">{analise.talhao_nome}</span>
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        aria-label="Fechar modal"
                        className="size-8 rounded-sm hover:bg-muted flex items-center justify-center transition-colors"
                    >
                        <X className="size-4 text-muted-foreground" />
                    </button>
                </div>

                {/* Step indicators */}
                <div className="px-6 py-3 bg-muted/30 border-b border-border flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => setStep("geral")}
                        className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-sm transition-all ${
                            step === "geral"
                                ? "bg-primary text-primary-foreground shadow-sm"
                                : "text-muted-foreground hover:bg-muted"
                        }`}
                    >
                        1. Identificação
                    </button>
                    <div className="h-px w-4 bg-border" />
                    <button
                        type="button"
                        onClick={() => setStep("quimica")}
                        className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-sm transition-all ${
                            step === "quimica"
                                ? "bg-primary text-primary-foreground shadow-sm"
                                : "text-muted-foreground hover:bg-muted"
                        }`}
                    >
                        2. Análise Química
                    </button>
                </div>

                {/* Form */}
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)}>
                        <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">

                            {step === "geral" && (
                                <div className="grid grid-cols-2 gap-4">
                                    {/* Talhão — somente leitura */}
                                    <div className="space-y-1.5">
                                        <p className="text-xs font-semibold text-muted-foreground">Talhão</p>
                                        <div className="w-full rounded-sm border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                                            {analise.talhao_nome}
                                        </div>
                                    </div>

                                    <FormField
                                        control={form.control}
                                        name="data_coleta"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                    Data de Coleta <span className="text-destructive">*</span>
                                                </FormLabel>
                                                <FormControl>
                                                    <Input type="date" className="rounded-sm" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <FormField
                                        control={form.control}
                                        name="profundidade_cm"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                    Profundidade (cm)
                                                </FormLabel>
                                                <FormControl>
                                                    <Input
                                                        type="number"
                                                        placeholder="20"
                                                        className="rounded-sm"
                                                        value={field.value ?? ""}
                                                        onChange={(e) => field.onChange(e.target.value)}
                                                    />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <FormField
                                        control={form.control}
                                        name="laboratorio"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                    Laboratório
                                                </FormLabel>
                                                <FormControl>
                                                    <Input placeholder="Ex.: IAC, EMBRAPA..." className="rounded-sm" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <FormField
                                        control={form.control}
                                        name="codigo_amostra"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                    Código da Amostra
                                                </FormLabel>
                                                <FormControl>
                                                    <Input placeholder="Ex.: AM-001" className="rounded-sm" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>
                            )}

                            {step === "quimica" && (
                                <>
                                    <div className="flex items-start justify-between gap-2">
                                        <p className="text-xs font-semibold text-muted-foreground">
                                            Parâmetros do laudo laboratorial
                                        </p>
                                        <p className="text-[10px] text-muted-foreground italic text-right">
                                            <span className="text-destructive">*</span> obrigatório — CTC e V% calculados automaticamente se H+Al informado
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-3 gap-3">
                                        {(
                                            [
                                                { name: "ph_agua",             label: "pH (H₂O)",       placeholder: "5.5",  required: true  },
                                                { name: "ph_cacl2",            label: "pH (CaCl₂)",     placeholder: "4.8",  required: false },
                                                { name: "materia_organica_pct",label: "M.O. (%)",       placeholder: "2.8",  required: true  },
                                                { name: "fosforo_p",           label: "P (mg/dm³)",     placeholder: "12.4", required: true  },
                                                { name: "potassio_k",          label: "K (mmol/dm³)",   placeholder: "3.2",  required: true  },
                                                { name: "calcio_ca",           label: "Ca (mmol/dm³)",  placeholder: "28.0", required: true  },
                                                { name: "magnesio_mg",         label: "Mg (mmol/dm³)",  placeholder: "10.0", required: true  },
                                                { name: "aluminio_al",         label: "Al (mmol/dm³)",  placeholder: "2.0",  required: false },
                                                { name: "hidrogenio_al_hal",   label: "H+Al (mmol/dm³)",placeholder: "45.0", required: false },
                                                { name: "ctc",                 label: "CTC (mmol/dm³)", placeholder: "86.2", required: false },
                                                { name: "v_pct",               label: "V% (Sat. Bases)",placeholder: "47.6", required: false },
                                                { name: "argila_pct",          label: "Argila (%)",     placeholder: "38.0", required: false },
                                            ] as const
                                        ).map(({ name, label, placeholder, required }) => (
                                            <FormField
                                                key={name}
                                                control={form.control}
                                                name={name}
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                            {label}{required && <span className="text-destructive ml-0.5">*</span>}
                                                        </FormLabel>
                                                        <FormControl>
                                                            <Input
                                                                type="number"
                                                                step="0.1"
                                                                placeholder={placeholder}
                                                                className="rounded-sm"
                                                                value={field.value ?? ""}
                                                                onChange={(e) => field.onChange(e.target.value)}
                                                            />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>

                        <Separator />

                        {/* Footer */}
                        <div className="flex justify-between items-center px-6 py-4">
                            <div>
                                {step === "quimica" && (
                                    <Button type="button" variant="ghost" size="sm" onClick={() => setStep("geral")}>
                                        <ChevronLeft className="mr-1.5 size-3.5" /> Voltar
                                    </Button>
                                )}
                            </div>
                            <div className="flex gap-3">
                                <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
                                    Cancelar
                                </Button>
                                {step === "geral" && (
                                    <Button
                                        type="button"
                                        size="sm"
                                        onClick={async () => {
                                            const ok = await form.trigger(["data_coleta"]);
                                            if (ok) setStep("quimica");
                                        }}
                                    >
                                        Próximo <ChevronRight className="ml-1.5 size-3.5" />
                                    </Button>
                                )}
                                {step === "quimica" && (
                                    <Button type="submit" size="sm" disabled={mutation.isPending}>
                                        {mutation.isPending ? (
                                            <><Loader2 className="mr-1.5 size-3.5 animate-spin" />Salvando...</>
                                        ) : (
                                            <><Save className="mr-1.5 size-3.5" />Salvar alterações</>
                                        )}
                                    </Button>
                                )}
                            </div>
                        </div>
                    </form>
                </Form>
            </div>
        </div>
    );
}
