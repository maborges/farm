"use client";

import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Copy, FlaskConical, Loader2, Save, ChevronRight, ChevronLeft, X } from "lucide-react";

import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
    formatTalhaoLabel,
    type TalhaoTerritorialRef,
    type UnidadeProdutivaRef,
} from "./territory-labels";

// ─── Helpers ────────────────────────────────────────────────────────────────
function toNum(v: unknown): number | undefined {
    if (v === "" || v === null || v === undefined) return undefined;
    const n = Number(v);
    return isNaN(n) ? undefined : n;
}
function optionalNumber() {
    return z.preprocess(toNum, z.number().optional());
}

function toInputValue(value: unknown): string {
    return value === null || value === undefined ? "" : String(value);
}

// ─── Regras de validação ─────────────────────────────────────────────────────
type CampoQuimico =
    | "ph_agua"
    | "materia_organica_pct"
    | "fosforo_p"
    | "potassio_k"
    | "calcio_ca"
    | "magnesio_mg"
    | "ph_cacl2"
    | "ctc"
    | "v_pct"
    | "argila_pct";

const REGRAS_QUIMICA: { field: CampoQuimico; label: string; min: number; max: number; required: boolean }[] = [
    { field: "ph_agua", label: "pH", min: 3.5, max: 9.0, required: true },
    { field: "materia_organica_pct", label: "MO (%)", min: 0, max: 15, required: true },
    { field: "fosforo_p", label: "P", min: 0, max: 200, required: true },
    { field: "potassio_k", label: "K", min: 0, max: 500, required: true },
    { field: "calcio_ca", label: "Ca", min: 0, max: 20, required: true },
    { field: "magnesio_mg", label: "Mg", min: 0, max: 10, required: true },
    { field: "ph_cacl2", label: "pH CaCl₂", min: 3.5, max: 9.0, required: false },
    { field: "ctc", label: "CTC", min: 0, max: 40, required: false },
    { field: "v_pct", label: "V%", min: 0, max: 100, required: false },
    { field: "argila_pct", label: "Argila", min: 0, max: 100, required: false },
];

// ─── Schema ─────────────────────────────────────────────────────────────────
const schema = z.object({
    talhao_id: z.string().min(1, "Selecione o talhão"),
    data_coleta: z.string().min(1, "Informe a data de coleta"),
    laboratorio: z.string().optional(),
    codigo_amostra: z.string().optional(),
    profundidade_cm: optionalNumber(),
    ph_agua: optionalNumber(),
    ph_cacl2: optionalNumber(),
    materia_organica_pct: optionalNumber(),
    fosforo_p: optionalNumber(),
    potassio_k: optionalNumber(),
    calcio_ca: optionalNumber(),
    magnesio_mg: optionalNumber(),
    aluminio_al: optionalNumber(),
    hidrogenio_al_hal: optionalNumber(),
    ctc: optionalNumber(),
    v_pct: optionalNumber(),
    argila_pct: optionalNumber(),
}).superRefine((data, ctx) => {
    for (const { field, label, min, max, required } of REGRAS_QUIMICA) {
        const v = data[field];
        if (v === undefined) {
            if (required)
                ctx.addIssue({ code: z.ZodIssueCode.custom, path: [field], message: `${label} é obrigatório` });
        } else if (v < min || v > max) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom, path: [field],
                message: `${label}: valor fora do intervalo (${min} – ${max})`
            });
        }
    }

    const podeCalcularCtc = (data.hidrogenio_al_hal ?? 0) > 0;
    if (!data.ctc && !podeCalcularCtc)
        ctx.addIssue({
            code: z.ZodIssueCode.custom, path: ["ctc"],
            message: "Informe a CTC ou o H+Al (para cálculo automático)"
        });

    const temCtc = data.ctc || podeCalcularCtc;
    if (!data.v_pct && !temCtc)
        ctx.addIssue({
            code: z.ZodIssueCode.custom, path: ["v_pct"],
            message: "Informe V% ou a CTC (para cálculo automático)"
        });
});

type FormValues = z.infer<typeof schema>;

// ─── Props ───────────────────────────────────────────────────────────────────
interface NovaAnaliseModalProps {
    onClose: () => void;
}

interface AnaliseSoloCopySource {
    id: string;
    talhao_id: string;
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

const CAMPOS_TEXTO_COPIA_ANALISE = [
    "laboratorio",
    "codigo_amostra",
] as const satisfies readonly (keyof FormValues)[];

const CAMPOS_NUMERICOS_COPIA_ANALISE = [
    "profundidade_cm",
    "ph_agua",
    "ph_cacl2",
    "materia_organica_pct",
    "fosforo_p",
    "potassio_k",
    "calcio_ca",
    "magnesio_mg",
    "aluminio_al",
    "hidrogenio_al_hal",
    "ctc",
    "v_pct",
    "argila_pct",
] as const satisfies readonly (keyof FormValues)[];

function normalizarDataColeta(data: string | null | undefined): string {
    if (!data) return new Date().toISOString().split("T")[0];
    return data.split("T")[0];
}

// ─── Component ───────────────────────────────────────────────────────────────
export function NovaAnaliseModal({ onClose }: NovaAnaliseModalProps) {
    const qc = useQueryClient();
    const [step, setStep] = useState<"geral" | "quimica">("geral");
    const [copySourceId, setCopySourceId] = useState<string>("");

    const form = useForm<z.input<typeof schema>, unknown, FormValues>({
        resolver: zodResolver(schema),
        defaultValues: {
            talhao_id: "",
            data_coleta: new Date().toISOString().split("T")[0],
            laboratorio: "",
            codigo_amostra: "",
            profundidade_cm: 20,
        },
    });

    const { data: talhoes = [] } = useQuery<TalhaoTerritorialRef[]>({
        queryKey: ["talhoes", "nova-analise-solo"],
        queryFn: () => apiFetch<TalhaoTerritorialRef[]>("/cadastros/areas-rurais?tipo=TALHAO"),
    });

    const { data: unidadesProdutivas = [] } = useQuery<UnidadeProdutivaRef[]>({
        queryKey: ["unidades-produtivas", "nova-analise-solo"],
        queryFn: () => apiFetch<UnidadeProdutivaRef[]>("/unidades-produtivas/"),
    });

    const { data: analises = [] } = useQuery<AnaliseSoloCopySource[]>({
        queryKey: ["analises-solo"],
        queryFn: () => apiFetch<AnaliseSoloCopySource[]>("/analises-solo/"),
    });

    const mutation = useMutation({
        mutationFn: (data: FormValues) =>
            apiFetch("/analises-solo/", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["analises-solo"] });
            toast.success("Análise de solo registrada com sucesso!");
            form.reset();
            setStep("geral");
            setCopySourceId("");
            onClose();
        },
        onError: () => toast.error("Erro ao registrar análise de solo"),
    });

    const selectedTalhaoId = form.watch("talhao_id");

    const copySources = useMemo(() => {
        return analises
            .filter(analise => analise.talhao_id && analise.talhao_id !== selectedTalhaoId)
            .sort((a, b) => new Date(b.data_coleta).getTime() - new Date(a.data_coleta).getTime());
    }, [analises, selectedTalhaoId]);

    useEffect(() => {
        if (!copySourceId) return;
        const source = analises.find(analise => analise.id === copySourceId);
        if (!source || source.talhao_id === selectedTalhaoId) {
            setCopySourceId("");
        }
    }, [analises, copySourceId, selectedTalhaoId]);

    function getTalhaoNome(talhaoId: string): string {
        const talhao = talhoes.find(item => item.id === talhaoId);
        return talhao ? formatTalhaoLabel(talhao, unidadesProdutivas) : "Talhão não informado";
    }

    function formatCopySourceLabel(analise: AnaliseSoloCopySource): string {
        const data = normalizarDataColeta(analise.data_coleta).split("-").reverse().join("/");
        const codigo = analise.codigo_amostra ? ` · ${analise.codigo_amostra}` : "";
        return `${getTalhaoNome(analise.talhao_id)} · ${data}${codigo}`;
    }

    function aplicarCopia(sourceId: string) {
        const source = analises.find(analise => analise.id === sourceId);
        if (!source || source.talhao_id === selectedTalhaoId) return;

        form.setValue("data_coleta", normalizarDataColeta(source.data_coleta), {
            shouldDirty: true,
            shouldValidate: false,
        });

        for (const field of CAMPOS_TEXTO_COPIA_ANALISE) {
            form.setValue(field, source[field] ?? "", { shouldDirty: true, shouldValidate: false });
        }

        for (const field of CAMPOS_NUMERICOS_COPIA_ANALISE) {
            form.setValue(field, source[field] ?? undefined, { shouldDirty: true, shouldValidate: false });
        }

        setCopySourceId(sourceId);
        void form.trigger();
        toast.success("Dados da amostragem copiados para o novo talhão.");
    }

    function handleClose() {
        form.reset();
        setStep("geral");
        setCopySourceId("");
        onClose();
    }

    function onSubmit(values: FormValues) {
        mutation.mutate(values);
    }

    const inputClass =
        "w-full rounded-sm border border-border bg-transparent px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors placeholder:text-muted-foreground";

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
                            <h2 className="font-bold text-foreground text-sm">Nova Amostragem de Solo</h2>
                            <p className="text-xs text-muted-foreground">Registre os parâmetros do laudo laboratorial</p>
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
                        className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-sm transition-all ${step === "geral"
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
                        className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-sm transition-all ${step === "quimica"
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
                                    <FormField
                                        control={form.control}
                                        name="talhao_id"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel className="text-xs font-semibold text-muted-foreground">
                                                    Talhão <span className="text-destructive">*</span>
                                                </FormLabel>
                                                <Select onValueChange={field.onChange} value={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger className="rounded-sm">
                                                            <SelectValue
                                                                placeholder={
                                                                    (() => {
                                                                        const talhao = talhoes.find(t => t.id === field.value);
                                                                        if (!talhao) return "Selecione o talhão";
                                                                        return formatTalhaoLabel(talhao, unidadesProdutivas);
                                                                    })()
                                                                }
                                                            />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent className="rounded-sm">
                                                        {talhoes.map((t) => (
                                                            <SelectItem key={t.id} value={t.id}>
                                                                {(() => {
                                                                    return formatTalhaoLabel(t, unidadesProdutivas);
                                                                })()}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

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

                                    <div className="col-span-2 rounded-sm border border-dashed border-border bg-muted/20 p-3">
                                        <div className="mb-2 flex items-start gap-2">
                                            <Copy className="mt-0.5 size-3.5 text-primary" />
                                            <div>
                                                <p className="text-xs font-semibold text-foreground">
                                                    Copiar dados de outro talhão
                                                </p>
                                                <p className="text-[11px] text-muted-foreground">
                                                    Selecione uma amostragem existente para preencher laboratório, código, profundidade e parâmetros químicos.
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <Select
                                                value={copySourceId}
                                                onValueChange={aplicarCopia}
                                                disabled={!selectedTalhaoId || copySources.length === 0}
                                            >
                                                <SelectTrigger className="rounded-sm">
                                                    <SelectValue
                                                        placeholder={
                                                            !selectedTalhaoId
                                                                ? "Selecione o talhão destino primeiro"
                                                                : copySources.length === 0
                                                                  ? "Nenhuma amostragem em outro talhão"
                                                                  : "Escolha a amostragem de origem"
                                                        }
                                                    />
                                                </SelectTrigger>
                                                <SelectContent className="rounded-sm">
                                                    {copySources.map((analise) => (
                                                        <SelectItem key={analise.id} value={analise.id}>
                                                            {formatCopySourceLabel(analise)}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            {copySourceId && (
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    className="shrink-0"
                                                    onClick={() => setCopySourceId("")}
                                                >
                                                    Limpar
                                                </Button>
                                            )}
                                        </div>
                                    </div>

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
                                                        value={toInputValue(field.value)}
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
                                                    <Input
                                                        placeholder="Ex.: IAC, EMBRAPA..."
                                                        className="rounded-sm"
                                                        {...field}
                                                    />
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
                                                    <Input
                                                        placeholder="Ex.: AM-001"
                                                        className="rounded-sm"
                                                        {...field}
                                                    />
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
                                                { name: "ph_agua", label: "pH (H₂O)", placeholder: "5.5", required: true },
                                                { name: "ph_cacl2", label: "pH (CaCl₂)", placeholder: "4.8", required: false },
                                                { name: "materia_organica_pct", label: "M.O. (%)", placeholder: "2.8", required: true },
                                                { name: "fosforo_p", label: "P (mg/dm³)", placeholder: "12.4", required: true },
                                                { name: "potassio_k", label: "K (mmol/dm³)", placeholder: "3.2", required: true },
                                                { name: "calcio_ca", label: "Ca (mmol/dm³)", placeholder: "20.0", required: true },
                                                { name: "magnesio_mg", label: "Mg (mmol/dm³)", placeholder: "10.0", required: true },
                                                { name: "aluminio_al", label: "Al (mmol/dm³)", placeholder: "2.0", required: false },
                                                { name: "hidrogenio_al_hal", label: "H+Al (mmol/dm³)", placeholder: "45.0", required: false },
                                                { name: "ctc", label: "CTC (mmol/dm³)", placeholder: "40", required: false },
                                                { name: "v_pct", label: "V% (Sat. Bases)", placeholder: "47.6", required: false },
                                                { name: "argila_pct", label: "Argila (%)", placeholder: "38.0", required: false },
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
                                                                value={toInputValue(field.value)}
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
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setStep("geral")}
                                    >
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
                                            const ok = await form.trigger(["talhao_id", "data_coleta"]);
                                            if (ok) setStep("quimica");
                                        }}
                                    >
                                        Próximo <ChevronRight className="ml-1.5 size-3.5" />
                                    </Button>
                                )}
                                {step === "quimica" && (
                                    <Button
                                        type="submit"
                                        size="sm"
                                        disabled={mutation.isPending}
                                    >
                                        {mutation.isPending ? (
                                            <>
                                                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                                                Salvando...
                                            </>
                                        ) : (
                                            <>
                                                <Save className="mr-1.5 size-3.5" />
                                                Registrar Laudo
                                            </>
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
