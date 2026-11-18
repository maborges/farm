"use client";

import { useEffect } from "react";
import { useFieldArray, useForm, Controller, useFormContext, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Plus, Trash2, Sprout, X, Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

// Schema será validado com refine para comparar contra a área real do talhão
const areaSchema = z.object({
    area_id: z.string().min(1, "Selecione um talhão"),
    area_ha: z.coerce.number().positive("Deve ser maior que 0"),
});

const cultivoSchema = z.object({
    _id: z.string().optional(), // id do cultivo existente (modo edição)
    cultura: z.string().min(1, "Informe a cultura"),
    cultivar_nome: z.string().optional(),
    areas: z.array(areaSchema).min(1, "Adicione ao menos um talhão"),
    produtividade_meta_sc_ha: z.preprocess(
        v => (v === "" || v === null || v === undefined ? undefined : Number(v)),
        z.number().positive().optional()
    ),
    consorciado: z.boolean().default(false),
    data_inicio: z.string().min(1, "Data de início é obrigatória"),
    data_fim: z.string().optional(),
});

const schema = z.object({
    ano_safra: z.string().regex(/^\d{4}(\/\d{2,4})?$/, "Use o formato AAAA ou AAAA/AA"),
    cultivos: z.array(cultivoSchema).min(1, "Adicione ao menos um cultivo"),
});

type SafraFormData = z.infer<typeof schema>;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AreaRural {
    id: string;
    nome: string;
    area_hectares: number | null;
    area_hectares_manual?: number | null;
}

interface CultivoArea {
    id: string;
    area_id: string;
    area_ha: number;
}

interface CultivoExistente {
    id: string;
    cultura: string;
    cultivar_nome: string | null;
    consorciado: boolean;
    data_inicio: string | null;
    data_fim: string | null;
    produtividade_meta_sc_ha: number | null;
    areas: CultivoArea[];
}

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    safraId?: string;
    initialSafra?: { ano_safra: string };
    initialCultivos?: CultivoExistente[];
}

// ---------------------------------------------------------------------------
// Entrada de cultivo inline
// ---------------------------------------------------------------------------

interface Cultura {
    id: string;
    nome: string;
    variedade?: string | null;
}

function CultivoEntry({
    index, control, register, errors, areas, watch, remove, canRemove, culturas,
}: {
    index: number;
    control: any;
    register: any;
    errors: any;
    areas: AreaRural[];
    watch: any;
    remove: () => void;
    canRemove: boolean;
    culturas: Cultura[];
}) {
    const { setValue } = useFormContext();
    const { fields, append, remove: removeArea } = useFieldArray({
        control,
        name: `cultivos.${index}.areas`,
    });

    const selectedAreaIds: string[] =
        watch(`cultivos.${index}.areas`)?.map((a: any) => a.area_id) ?? [];
    const cultivoErrors = errors?.cultivos?.[index];

    return (
        <div className="rounded-lg border bg-muted/30 p-4 space-y-4">
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Cultivo {index + 1}
                </span>
                {canRemove && (
                    <Button
                        type="button" size="icon" variant="ghost"
                        className="size-6 text-muted-foreground hover:text-destructive"
                        onClick={remove}
                    >
                        <X className="size-3.5" />
                    </Button>
                )}
            </div>

            {/* Cultura */}
            <div className="space-y-1.5">
                <Label className="text-xs">Cultura *</Label>
                <Controller
                    control={control}
                    name={`cultivos.${index}.cultura`}
                    render={({ field: f }) => {
                        const selectedId = culturas.find(c => c.nome === f.value)?.id || f.value;
                        return (
                            <Select 
                                value={selectedId} 
                                onValueChange={(val) => {
                                    const selected = culturas.find(c => c.id === val);
                                    if (selected) {
                                        f.onChange(selected.nome);
                                        if (selected.variedade && !watch(`cultivos.${index}.cultivar_nome`)) {
                                            setValue(`cultivos.${index}.cultivar_nome`, selected.variedade, { shouldDirty: true });
                                        }
                                    } else {
                                        f.onChange(val);
                                    }
                                }}
                            >
                                <SelectTrigger className={cn("h-8 text-sm", cultivoErrors?.cultura && "border-destructive")}>
                                    <SelectValue placeholder="Selecione a cultura" />
                                </SelectTrigger>
                                <SelectContent className="max-h-72">
                                    {culturas.map(c => (
                                        <SelectItem key={c.id} value={c.id} className="text-sm">
                                            {c.nome}
                                            {c.variedade && <span className="text-muted-foreground ml-1">· {c.variedade}</span>}
                                        </SelectItem>
                                    ))}
                                    {f.value && !culturas.find(c => c.nome === f.value) && (
                                        <SelectItem value={f.value} className="text-sm">
                                            {f.value}
                                        </SelectItem>
                                    )}
                                </SelectContent>
                            </Select>
                        );
                    }}
                />
                {cultivoErrors?.cultura && (
                    <p className="text-xs text-destructive">{cultivoErrors.cultura.message}</p>
                )}
            </div>

            {/* Cultivar */}
            <div className="space-y-1.5">
                <Label className="text-xs">
                    Cultivar <span className="font-normal text-muted-foreground">(opcional)</span>
                </Label>
                <Input
                    placeholder="Ex: Bourbon Amarelo"
                    {...register(`cultivos.${index}.cultivar_nome`)}
                    className="h-8 text-sm"
                />
            </div>

            {/* Talhões */}
            <div className="space-y-2">
                <Label className="text-xs">Talhões *</Label>

                {fields.length === 0 && (
                    <p className="text-xs text-muted-foreground">Nenhum talhão adicionado.</p>
                )}

                {fields.map((field, aIdx) => {
                    const selectedTalhao = areas.find(a => a.id === watch(`cultivos.${index}.areas.${aIdx}.area_id`));
                    const selectedTalhaoArea = selectedTalhao?.area_hectares ?? selectedTalhao?.area_hectares_manual;
                    return (
                    <div key={field.id} className="p-2 rounded bg-muted/30 border grid grid-cols-12 gap-2 items-start">
                        {/* Talhão */}
                        <div className="col-span-6 space-y-0.5">
                            <Label className="text-xs font-medium">Talhão *</Label>
                            <Controller
                                control={control}
                                name={`cultivos.${index}.areas.${aIdx}.area_id`}
                                render={({ field: f }) => {
                                    const handleAreaChange = (areaId: string) => {
                                        f.onChange(areaId);
                                        const selectedArea = areas.find(a => a.id === areaId);
                                        const selectedAreaHa = selectedArea?.area_hectares ?? selectedArea?.area_hectares_manual;
                                        if (selectedAreaHa && selectedAreaHa > 0) {
                                            const currentArea = watch(`cultivos.${index}.areas.${aIdx}.area_ha`);
                                            const areaValue = Number(currentArea) || 0;
                                            if (areaValue === 0) {
                                                const numValue = Number(selectedAreaHa);
                                                setValue(`cultivos.${index}.areas.${aIdx}.area_ha`, numValue, { shouldValidate: true, shouldDirty: true });
                                            }
                                        }
                                    };
                                    return (
                                    <Select value={f.value} onValueChange={handleAreaChange}>
                                        <SelectTrigger className="h-7 text-xs text-left">
                                                {selectedTalhao ? (
                                                    <span className="text-xs">
                                                        {selectedTalhao.nome}
                                                        {selectedTalhaoArea != null && (
                                                            <span className="text-muted-foreground ml-1">({selectedTalhaoArea} ha)</span>
                                                        )}
                                                    </span>
                                                ) : (
                                                    <span className="text-muted-foreground text-xs">Selecione</span>
                                                )}
                                        </SelectTrigger>
                                        <SelectContent>
                                            {areas
                                                .filter(a => !selectedAreaIds.includes(a.id) || a.id === f.value)
                                                .map(a => {
                                                    const areaHa = a.area_hectares ?? a.area_hectares_manual;
                                                    return (
                                                        <SelectItem key={a.id} value={a.id} className="text-xs">
                                                            {a.nome} {areaHa != null && `· ${areaHa} ha`}
                                                        </SelectItem>
                                                    );
                                                })}
                                        </SelectContent>
                                    </Select>
                                    );
                                }}
                            />
                        </div>

                        {/* Área a Plantar */}
                        <div className="col-span-4 space-y-0.5">
                            <Label htmlFor={`area_ha_${aIdx}`} className="text-xs font-medium">
                                Plantar (ha) {selectedTalhaoArea != null && <span className="font-normal text-muted-foreground">máx {selectedTalhaoArea}</span>}
                            </Label>
                            <Input
                                id={`area_ha_${aIdx}`}
                                type="number" step="0.01"
                                placeholder={selectedTalhaoArea?.toString() ?? "0.00"}
                                {...register(`cultivos.${index}.areas.${aIdx}.area_ha`, {
                                    validate: (v: number) => {
                                        if (!selectedTalhaoArea) return true;
                                        if (!v || v <= 0) return "Deve ser > 0";
                                        if (v > selectedTalhaoArea) return `Máximo ${selectedTalhaoArea} ha`;
                                        return true;
                                    },
                                })}
                                className="h-7 text-xs w-full"
                            />
                            {errors?.cultivos?.[index]?.areas?.[aIdx]?.area_ha && (
                                <p className="text-xs text-destructive">{(errors.cultivos[index].areas[aIdx].area_ha as any).message}</p>
                            )}
                        </div>

                        {/* Delete */}
                        <div className="col-span-2 flex justify-end">
                            <Button
                                type="button" size="icon" variant="ghost"
                                className="size-7 text-muted-foreground hover:text-destructive"
                                onClick={() => removeArea(aIdx)}
                            >
                                <Trash2 className="size-3" />
                            </Button>
                        </div>
                    </div>
                    );
                })}

                {cultivoErrors?.areas && typeof cultivoErrors.areas.message === "string" && (
                    <p className="text-xs text-destructive">{cultivoErrors.areas.message}</p>
                )}

                <Button
                    type="button" size="sm" variant="outline"
                    className="h-7 text-xs gap-1"
                    onClick={() => append({ area_id: "", area_ha: 0 })}
                    disabled={areas.length > 0 && selectedAreaIds.length >= areas.length}
                >
                    <Plus className="size-3" /> Talhão
                </Button>
            </div>

            {/* Meta de produtividade */}
            <div className="space-y-1.5">
                <Label className="text-xs">
                    Meta de Produtividade{" "}
                    <span className="font-normal text-muted-foreground">(sc/ha, opcional)</span>
                </Label>
                <Input
                    type="number" step="0.01" placeholder="0.00"
                    {...register(`cultivos.${index}.produtividade_meta_sc_ha`)}
                    className="h-8 text-sm w-36"
                />
            </div>

            {/* Consorciado */}
            <div className="flex items-center gap-2">
                <Controller
                    control={control}
                    name={`cultivos.${index}.consorciado`}
                    render={({ field: f }) => (
                        <Checkbox
                            checked={f.value}
                            onCheckedChange={f.onChange}
                            id={`consorciado_${index}`}
                        />
                    )}
                />
                <Label htmlFor={`consorciado_${index}`} className="text-xs font-medium cursor-pointer">
                    Consorciado <span className="font-normal text-muted-foreground">(cultivos que compartilham espaço)</span>
                </Label>
            </div>

            {/* Período de ocupação */}
            <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                    <Label className="text-xs">Início da ocupação *</Label>
                    <Input
                        type="date"
                        {...register(`cultivos.${index}.data_inicio`)}
                        className={cn("h-8 text-sm", cultivoErrors?.data_inicio && "border-destructive")}
                    />
                    {cultivoErrors?.data_inicio && (
                        <p className="text-xs text-destructive">{cultivoErrors.data_inicio.message}</p>
                    )}
                </div>
                <div className="space-y-1.5">
                    <Label className="text-xs">
                        Fim da ocupação <span className="font-normal text-muted-foreground">(opcional)</span>
                    </Label>
                    <Input
                        type="date"
                        {...register(`cultivos.${index}.data_fim`)}
                        className="h-8 text-sm"
                    />
                </div>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Dialog principal
// ---------------------------------------------------------------------------

export function SafraCreateDialog({ open, onOpenChange, safraId, initialSafra, initialCultivos }: Props) {
    const isEditing = !!safraId;
    const qc = useQueryClient();

    const { data: areas = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais-talhoes"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
        enabled: open,
    });

    const { data: culturas = [] } = useQuery<Cultura[]>({
        queryKey: ["culturas", "ativas"],
        queryFn: () => apiFetch("/cadastros/culturas", { params: { ativa: true } }),
        enabled: open,
    });

    const methods = useForm<SafraFormData>({
        resolver: zodResolver(schema) as any,
        defaultValues: {
            ano_safra: "",
            cultivos: [{ cultura: "", cultivar_nome: "", areas: [], consorciado: false, data_inicio: "", data_fim: undefined }],
        },
    });

    const { register, control, handleSubmit, watch, reset, formState: { errors } } = methods;

    // Inicializar useFieldArray ANTES do useEffect
    const { fields: cultivoFields, append: appendCultivo, remove: removeCultivo } = useFieldArray({
        control,
        name: "cultivos",
    });

    // Popula o formulário com os dados existentes (modo edição)
    useEffect(() => {
        if (isEditing && initialSafra && initialCultivos && initialCultivos.length > 0) {
            const fmtDate = (d: string | null | undefined) => d ? d.split("T")[0] : "";
            reset({
                ano_safra: initialSafra.ano_safra,
                cultivos: initialCultivos.map(c => ({
                    _id: c.id,
                    cultura: c.cultura,
                    cultivar_nome: c.cultivar_nome ?? "",
                    areas: (c.areas ?? []).map(a => ({ area_id: a.area_id, area_ha: a.area_ha })),
                    consorciado: c.consorciado,
                    data_inicio: fmtDate(c.data_inicio),
                    data_fim: fmtDate(c.data_fim) || undefined,
                    produtividade_meta_sc_ha: c.produtividade_meta_sc_ha ?? undefined,
                })),
            });
        }
    }, [isEditing, initialSafra, initialCultivos, reset]);

    const mutation = useMutation({
        mutationFn: async (data: SafraFormData) => {
            if (isEditing && safraId) {
                // 1. Atualiza o ano da safra
                await apiFetch(`/safras/${safraId}`, {
                    method: "PATCH",
                    body: JSON.stringify({ ano_safra: data.ano_safra }),
                });

                // IDs dos cultivos que existem no form
                const formIds = data.cultivos.filter(c => c._id).map(c => c._id!);
                // Deletar cultivos removidos pelo usuário
                const originalIds = (initialCultivos ?? []).map(c => c.id);
                await Promise.all(
                    originalIds
                        .filter(id => !formIds.includes(id))
                        .map(id => apiFetch(`/safras/${safraId}/cultivos/${id}`, { method: "DELETE" }))
                );

                // 2. Atualizar ou criar cultivos
                await Promise.all(data.cultivos.map(async c => {
                    const payload = {
                        cultura: c.cultura,
                        cultivar_nome: c.cultivar_nome || null,
                        produtividade_meta_sc_ha: c.produtividade_meta_sc_ha || null,
                        consorciado: c.consorciado,
                        data_inicio: c.data_inicio || null,
                        data_fim: c.data_fim || null,
                    };
                    if (c._id) {
                        await apiFetch(`/safras/${safraId}/cultivos/${c._id}`, {
                            method: "PATCH",
                            body: JSON.stringify(payload),
                        });
                        await apiFetch(`/safras/${safraId}/cultivos/${c._id}/areas`, {
                            method: "PUT",
                            body: JSON.stringify(c.areas),
                        });
                    } else {
                        await apiFetch(`/safras/${safraId}/cultivos`, {
                            method: "POST",
                            body: JSON.stringify({ ...payload, areas: c.areas }),
                        });
                    }
                }));
            } else {
                await apiFetch("/safras/", {
                    method: "POST",
                    body: JSON.stringify({
                        ano_safra: data.ano_safra,
                        cultivos: data.cultivos.map(c => ({
                            cultura: c.cultura,
                            cultivar_nome: c.cultivar_nome || null,
                            areas: c.areas,
                            produtividade_meta_sc_ha: c.produtividade_meta_sc_ha || null,
                            consorciado: c.consorciado,
                            data_inicio: c.data_inicio || null,
                            data_fim: c.data_fim || null,
                        })),
                    }),
                });
            }
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["safras"] });
            if (isEditing && safraId) {
                qc.invalidateQueries({ queryKey: ["safra", safraId] });
                qc.invalidateQueries({ queryKey: ["safra-cultivos", safraId] });
                toast.success("Safra atualizada com sucesso!");
            } else {
                toast.success("Safra criada com sucesso!");
            }
            reset();
            onOpenChange(false);
        },
        onError: (err: any) => {
            toast.error(err?.message ?? (isEditing ? "Erro ao atualizar safra" : "Erro ao criar safra"));
        },
    });

    function handleClose() {
        reset();
        onOpenChange(false);
    }

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="max-w-lg flex flex-col gap-0 p-0 max-h-[85vh]">
                {/* Header */}
                <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
                    <div className="flex items-center gap-2.5">
                        <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Sprout className="size-4 text-primary" />
                        </div>
                        <div>
                            <DialogTitle className="text-base leading-tight">{isEditing ? "Editar Safra" : "Nova Safra"}</DialogTitle>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {isEditing ? "Atualize os dados da safra planejada" : "Defina o ano agrícola e os cultivos desta safra"}
                            </p>
                        </div>
                    </div>
                </DialogHeader>

                {/* Corpo scrollável */}
                <FormProvider {...methods}>
                <form
                    id="safra-form"
                    onSubmit={handleSubmit(d => mutation.mutate(d as SafraFormData))}
                    className="flex-1 overflow-y-auto px-4 space-y-3 py-3"
                >
                    {/* Ano safra */}
                    <div className="space-y-1">
                        <Label htmlFor="ano_safra" className="text-xs font-medium">Ano Agrícola *</Label>
                        <Input
                            id="ano_safra"
                            placeholder="Ex: 2025 ou 2025/26"
                            autoFocus
                            {...register("ano_safra")}
                            className={cn("h-8 text-sm", errors.ano_safra && "border-destructive")}
                        />
                        {errors.ano_safra ? (
                            <p className="text-xs text-destructive">{errors.ano_safra.message}</p>
                        ) : (
                            <p className="text-xs text-muted-foreground">Formato: AAAA ou AAAA/AA</p>
                        )}
                    </div>

                    <Separator className="my-2" />

                    {/* Cultivos */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label className="text-xs font-medium">Cultivos *</Label>
                            <Button
                                type="button" size="sm" variant="outline"
                                className="h-7 text-xs gap-1"
                                onClick={() => appendCultivo({ cultura: "", cultivar_nome: "", areas: [], consorciado: false, data_inicio: "", data_fim: undefined })}
                            >
                                <Plus className="size-3" /> Cultivo
                            </Button>
                        </div>

                        {errors.cultivos && typeof (errors.cultivos as any).message === "string" && (
                            <p className="text-xs text-destructive">{(errors.cultivos as any).message}</p>
                        )}

                        {cultivoFields.map((field, idx) => (
                            <CultivoEntry
                                key={field.id}
                                index={idx}
                                control={control}
                                register={register}
                                errors={errors}
                                areas={areas}
                                culturas={culturas}
                                watch={watch}
                                remove={() => removeCultivo(idx)}
                                canRemove={cultivoFields.length > 1}
                            />
                        ))}
                    </div>

                    {/* Espaço no final para não cortar o último card */}
                    <div className="h-2" />
                </form>
                </FormProvider>

                <DialogFooter>
                    <Button type="button" variant="outline" onClick={handleClose} disabled={mutation.isPending}>
                        Cancelar
                    </Button>
                    <Button type="submit" form="safra-form" disabled={mutation.isPending}>
                        {mutation.isPending
                            ? <><Loader2 className="size-3.5 mr-1.5 animate-spin" />{isEditing ? "Salvando..." : "Criando..."}</>
                            : isEditing ? "Salvar Alterações" : "Criar Safra"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
