"use client";

import { useEffect, type ReactNode } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Droplets, FileText, MapPinned, Ruler, Save, Sprout } from "lucide-react";

const schema = z.object({
    nome: z.string().min(1, "Nome obrigatório"),
    codigo: z.string().optional(),
    descricao: z.string().optional(),
    parent_id: z.string().optional(),
    area_hectares_manual: z.preprocess(
        (val) => (val === "" ? undefined : val),
        z.coerce.number().positive().optional()
    ),
    tipo_solo: z.string().optional(),
    textura_solo: z.string().optional(),
    relevo: z.string().optional(),
    declividade_pct: z.preprocess(
        (val) => (val === "" ? undefined : val),
        z.coerce.number().min(0).max(100).optional()
    ),
    irrigado: z.boolean(),
    sistema_irrigacao: z.string().optional(),
});

type FormInput = z.input<typeof schema>;
type FormData = z.output<typeof schema>;

const TIPO_SOLO_OPTIONS = [
    { value: "LATOSSOLO", label: "Latossolo" },
    { value: "ARGISSOLO", label: "Argissolo" },
    { value: "CAMBISSOLO", label: "Cambissolo" },
    { value: "NEOSSOLO", label: "Neossolo" },
    { value: "NITOSSOLO", label: "Nitossolo" },
    { value: "GLEISSOLO", label: "Gleissolo" },
    { value: "VERTISSOLO", label: "Vertissolo" },
    { value: "ESPODOSSOLO", label: "Espodossolo" },
    { value: "OUTRO", label: "Outro" },
];

const TEXTURA_SOLO_OPTIONS = [
    { value: "ARGILOSA", label: "Argilosa" },
    { value: "MUITO_ARGILOSA", label: "Muito Argilosa" },
    { value: "MEDIA", label: "Média" },
    { value: "ARENOSA", label: "Arenosa" },
    { value: "FRANCO_ARGILOSA", label: "Franco-Argilosa" },
    { value: "FRANCO_ARENOSA", label: "Franco-Arenosa" },
];

const RELEVO_OPTIONS = [
    { value: "PLANO", label: "Plano" },
    { value: "SUAVE_ONDULADO", label: "Suave Ondulado" },
    { value: "ONDULADO", label: "Ondulado" },
    { value: "FORTE_ONDULADO", label: "Forte Ondulado" },
    { value: "MONTANHOSO", label: "Montanhoso" },
];

const IRRIGACAO_OPTIONS = [
    { value: "GOTEJAMENTO", label: "Gotejamento" },
    { value: "PIVO_CENTRAL", label: "Pivô Central" },
    { value: "ASPERSAO", label: "Aspersão" },
    { value: "SULCO", label: "Sulco" },
    { value: "INUNDACAO", label: "Inundação" },
];

interface AreaRural {
    id: string;
    nome: string;
    tipo?: string;
    parent_id?: string;
    area_hectares?: number;
    area_hectares_manual?: number;
    descricao?: string;
    codigo?: string;
    dados_extras?: Record<string, any>;
}

interface Props {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    talhao: AreaRural;
    parentOptions: AreaRural[]; // glebas/areas_rurais disponíveis como pai
    fazendaId: string;
}

export function TalhaoFormDialog({ open, onOpenChange, talhao, parentOptions, fazendaId }: Props) {
    const queryClient = useQueryClient();

    const { register, handleSubmit, setValue, reset, control, formState: { errors } } = useForm<FormInput, unknown, FormData>({
        resolver: zodResolver(schema),
        defaultValues: {
            nome: "",
            codigo: "",
            descricao: "",
            parent_id: "",
            area_hectares_manual: undefined,
            tipo_solo: "",
            textura_solo: "",
            relevo: "",
            declividade_pct: undefined,
            irrigado: false,
            sistema_irrigacao: "",
        }
    });

    const parentId = useWatch({ control, name: "parent_id" });
    const tipoSolo = useWatch({ control, name: "tipo_solo" });
    const texturaSolo = useWatch({ control, name: "textura_solo" });
    const relevo = useWatch({ control, name: "relevo" });
    const irrigado = useWatch({ control, name: "irrigado" });
    const sistemaIrrigacao = useWatch({ control, name: "sistema_irrigacao" });

    useEffect(() => {
        if (open && talhao) {
            reset({
                nome: talhao.nome ?? "",
                codigo: talhao.codigo ?? "",
                descricao: talhao.descricao ?? "",
                parent_id: talhao.parent_id ?? "",
                area_hectares_manual: talhao.area_hectares_manual ?? undefined,
                tipo_solo: talhao.dados_extras?.tipo_solo ?? "",
                textura_solo: talhao.dados_extras?.textura_solo ?? "",
                relevo: talhao.dados_extras?.relevo ?? "",
                declividade_pct: talhao.dados_extras?.declividade_pct ?? undefined,
                irrigado: !!talhao.dados_extras?.irrigado,
                sistema_irrigacao: talhao.dados_extras?.sistema_irrigacao ?? "",
            });
        }
    }, [open, talhao, reset]);

    const mutation = useMutation({
        mutationFn: (data: FormData) => {
            const payload = {
                nome: data.nome,
                codigo: data.codigo || null,
                descricao: data.descricao || null,
                parent_id: data.parent_id || null,
                area_hectares_manual: data.area_hectares_manual ?? null,
                dados_extras: {
                    ...(talhao.dados_extras ?? {}),
                    tipo_solo: data.tipo_solo || null,
                    textura_solo: data.textura_solo || null,
                    relevo: data.relevo || null,
                    declividade_pct: data.declividade_pct ?? null,
                    irrigado: data.irrigado,
                    sistema_irrigacao: data.irrigado ? (data.sistema_irrigacao || null) : null,
                },
            };
            return apiFetch(`/cadastros/areas-rurais/${talhao.id}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
                headers: { "Content-Type": "application/json" }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["areas-rurais", fazendaId] });
            toast.success("Talhão atualizado");
            onOpenChange(false);
        },
        onError: (e: Error) => toast.error(e.message || "Erro ao salvar"),
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="!w-[min(520px,calc(100vw-2rem))] !max-w-[min(520px,calc(100vw-2rem))] rounded-sm p-0">
                <DialogHeader className="border-b px-4 py-2.5">
                    <div className="flex items-center gap-3">
                        <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                            <MapPinned className="size-4" />
                        </div>
                        <div className="min-w-0">
                            <DialogTitle className="truncate">
                                Editar Talhão
                            </DialogTitle>
                            <DialogDescription className="truncate text-xs leading-tight">
                                Dados cadastrais e agronômicos de {talhao?.nome}.
                            </DialogDescription>
                        </div>
                        <Badge variant="outline" className="ml-auto shrink-0 rounded-sm">
                            {talhao?.tipo ?? "TALHAO"}
                        </Badge>
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="flex min-h-0 flex-1 flex-col">
                    <div className="grid min-h-0 flex-1 gap-2.5 px-4 py-2.5">
                        <DialogSection icon={<FileText className="size-3.5" />} title="Identificação">
                            <FormField label="Nome *" error={errors.nome?.message}>
                                <Input {...register("nome")} placeholder="Ex: Talhão A" aria-invalid={!!errors.nome} />
                            </FormField>
                            <div className="grid gap-2.5 sm:grid-cols-2">
                                <FormField label="Código">
                                    <Input {...register("codigo")} placeholder="Ex: TAL-01" />
                                </FormField>
                                <FormField label="Área informada (ha)">
                                    <Input
                                        type="number"
                                        step="0.01"
                                        {...register("area_hectares_manual")}
                                        placeholder="Ex: 12,50"
                                        className="tabular-nums"
                                    />
                                </FormField>
                            </div>
                            {parentOptions.length > 0 && (
                                <FormField label="Gleba / Área Rural pai">
                                    <Select
                                        value={parentId ?? ""}
                                        onValueChange={(v: string) => setValue("parent_id", v === "__none__" ? "" : v)}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="Nenhuma" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">Nenhuma</SelectItem>
                                            {parentOptions.map((p) => (
                                                <SelectItem key={p.id} value={p.id}>
                                                    {p.nome} ({p.tipo?.replace("_", " ")})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormField>
                            )}
                            <FormField label="Descrição">
                                <Textarea {...register("descricao")} rows={2} placeholder="Observações gerais..." />
                            </FormField>
                        </DialogSection>

                        <DialogSection icon={<Sprout className="size-3.5" />} title="Solo e Relevo">
                            <div className="grid gap-2.5 sm:grid-cols-2">
                                <FormField label="Tipo de solo">
                                    <Select value={tipoSolo ?? ""} onValueChange={(v: string) => setValue("tipo_solo", v === "__none__" ? "" : v)}>
                                        <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">Não informado</SelectItem>
                                            {TIPO_SOLO_OPTIONS.map((option) => (
                                                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormField>
                                <FormField label="Textura">
                                    <Select value={texturaSolo ?? ""} onValueChange={(v: string) => setValue("textura_solo", v === "__none__" ? "" : v)}>
                                        <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">Não informada</SelectItem>
                                            {TEXTURA_SOLO_OPTIONS.map((option) => (
                                                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormField>
                                <FormField label="Relevo">
                                    <Select value={relevo ?? ""} onValueChange={(v: string) => setValue("relevo", v === "__none__" ? "" : v)}>
                                        <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__none__">Não informado</SelectItem>
                                            {RELEVO_OPTIONS.map((option) => (
                                                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormField>
                                <FormField label="Declividade (%)" error={errors.declividade_pct?.message}>
                                    <Input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        max="100"
                                        {...register("declividade_pct")}
                                        placeholder="Ex: 5"
                                        className="tabular-nums"
                                        aria-invalid={!!errors.declividade_pct}
                                    />
                                </FormField>
                            </div>
                        </DialogSection>

                        <DialogSection icon={<Droplets className="size-3.5" />} title="Irrigação">
                            <div className="flex items-center justify-between rounded-sm border bg-background px-2.5 py-2">
                                <div className="flex flex-col gap-0.5">
                                    <Label htmlFor="talhao-irrigado" className="text-sm font-medium">Talhão irrigado</Label>
                                    <span className="text-xs text-muted-foreground">Sistema de irrigação instalado.</span>
                                </div>
                                <Switch
                                    id="talhao-irrigado"
                                    checked={irrigado}
                                    onCheckedChange={(v) => {
                                        setValue("irrigado", v);
                                        if (!v) setValue("sistema_irrigacao", "");
                                    }}
                                />
                            </div>

                            {irrigado && (
                                <FormField label="Sistema de irrigação">
                                    <Select value={sistemaIrrigacao ?? ""} onValueChange={(v: string) => setValue("sistema_irrigacao", v)}>
                                        <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            {IRRIGACAO_OPTIONS.map((option) => (
                                                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormField>
                            )}

                            <div className="rounded-sm border bg-muted/30 px-2.5 py-2 text-xs text-muted-foreground">
                                <div className="mb-1 flex items-center gap-2 font-medium text-foreground">
                                    <Ruler className="size-3.5 text-primary" />
                                    Geometria e área calculada
                                </div>
                                A geometria é editada diretamente no mapa.
                            </div>
                        </DialogSection>
                    </div>

                    <DialogFooter className="border-t px-4 py-2.5">
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending} size="sm">
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={mutation.isPending} size="sm">
                            <Save className="size-3.5" />
                            {mutation.isPending ? "Salvando..." : "Salvar Alterações"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function FormField({
    label,
    error,
    className,
    children,
}: {
    label: string;
    error?: string;
    className?: string;
    children: ReactNode;
}) {
    return (
        <div className={`grid gap-1.5 ${className ?? ""}`}>
            <Label>{label}</Label>
            {children}
            {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
    );
}

function DialogSection({
    icon,
    title,
    children,
}: {
    icon: ReactNode;
    title: string;
    children: ReactNode;
}) {
    return (
        <section className="grid gap-2.5 rounded-sm border bg-muted/20 p-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <span className="text-primary">{icon}</span>
                {title}
            </div>
            {children}
        </section>
    );
}
