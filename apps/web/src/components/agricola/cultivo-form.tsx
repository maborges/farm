"use client";

import { useFieldArray, useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { Trash2, Plus } from "lucide-react";
import { toast } from "sonner";

const cultivoAreaSchema = z.object({
    area_id: z.string().uuid("Talhão inválido"),
    area_ha: z.coerce.number().positive("Área deve ser positiva"),
});

const cultivoFormSchema = z.object({
    cultura: z.string().min(1, "Cultura obrigatória"),
    cultivar_nome: z.string().nullable().optional(),
    areas: z.array(cultivoAreaSchema).min(1, "Informe pelo menos um talhão"),
    produtividade_meta_sc_ha: z.coerce.number().positive().nullable().optional(),
    preco_venda_previsto: z.coerce.number().positive().nullable().optional(),
});

type CultivoFormInput = z.input<typeof cultivoFormSchema>;
type CultivoFormData = z.output<typeof cultivoFormSchema>;

interface AreaRural {
    id: string;
    nome: string;
    area_hectares: number | null;
}

interface Props {
    areas: AreaRural[];
    onSubmit: (data: CultivoFormData) => void;
    isLoading?: boolean;
}

export function CultivoForm({ areas, onSubmit, isLoading = false }: Props) {
    const {
        control,
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm<CultivoFormInput, unknown, CultivoFormData>({
        resolver: zodResolver(cultivoFormSchema),
        defaultValues: {
            areas: [{ area_id: "", area_ha: 0 }],
        },
    });

    const { fields: areaFields, append: appendArea, remove: removeArea } = useFieldArray({
        control,
        name: "areas",
    });

    const selectedAreaIds = watch("areas").map(a => a.area_id);
    const availableAreas = areas.filter(a => !selectedAreaIds.includes(a.id));

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Cultura */}
            <div className="space-y-2">
                <Label htmlFor="cultura">Cultura *</Label>
                <Input
                    id="cultura"
                    placeholder="Ex: Café, Milho, Soja"
                    {...register("cultura")}
                />
                {errors.cultura && <p className="text-xs text-destructive">{errors.cultura.message}</p>}
            </div>

            {/* Cultivar */}
            <div className="space-y-2">
                <Label htmlFor="cultivar_nome">Cultivar</Label>
                <Input
                    id="cultivar_nome"
                    placeholder="Ex: Bourbon, Safrinha"
                    {...register("cultivar_nome")}
                />
            </div>

            {/* Talhões */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <Label>Talhões *</Label>
                    {availableAreas.length > 0 && (
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => appendArea({ area_id: "", area_ha: 0 })}
                        >
                            <Plus className="h-3 w-3 mr-1" /> Adicionar
                        </Button>
                    )}
                </div>

                {areaFields.length === 0 ? (
                    <p className="text-sm text-muted-foreground italic">Nenhum talhão adicionado</p>
                ) : (
                    <div className="space-y-2">
                        {areaFields.map((field, idx) => (
                            <Card key={field.id} className="bg-muted/30">
                                <CardContent className="pt-4">
                                    <div className="grid gap-3 grid-cols-[1fr_120px_auto]">
                                        {/* Talhão Select */}
                                        <Controller
                                            name={`areas.${idx}.area_id`}
                                            control={control}
                                            render={({ field }) => (
                                                <div className="space-y-1">
                                                    <label className="text-xs font-medium">Talhão</label>
                                                    <Select value={field.value} onValueChange={field.onChange}>
                                                        <SelectTrigger className="h-8">
                                                            <SelectValue placeholder="Selecione..." />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {areas
                                                                .filter(a => a.id === field.value || !selectedAreaIds.includes(a.id))
                                                                .map(area => (
                                                                    <SelectItem key={area.id} value={area.id}>
                                                                        {area.nome}
                                                                        {area.area_hectares && ` (${area.area_hectares} ha)`}
                                                                    </SelectItem>
                                                                ))}
                                                        </SelectContent>
                                                    </Select>
                                                    {errors.areas?.[idx]?.area_id && (
                                                        <p className="text-xs text-destructive">{errors.areas[idx]?.area_id?.message}</p>
                                                    )}
                                                </div>
                                            )}
                                        />

                                        {/* Área em ha */}
                                        <div className="space-y-1">
                                            <label className="text-xs font-medium">Área (ha) *</label>
                                            <Input
                                                type="number"
                                                step="0.01"
                                                placeholder="0.00"
                                                className="h-8"
                                                {...register(`areas.${idx}.area_ha`)}
                                            />
                                            {errors.areas?.[idx]?.area_ha && (
                                                <p className="text-xs text-destructive">{errors.areas[idx]?.area_ha?.message}</p>
                                            )}
                                        </div>

                                        {/* Remove button */}
                                        <Button
                                            type="button"
                                            size="icon"
                                            variant="ghost"
                                            className="h-8 w-8 text-destructive hover:text-destructive self-end"
                                            onClick={() => removeArea(idx)}
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
                {errors.areas && typeof errors.areas.message === "string" && (
                    <p className="text-xs text-destructive">{errors.areas.message}</p>
                )}
            </div>

            {/* Produtividade */}
            <div className="grid gap-4 grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="produtividade">Produtividade Meta (sc/ha)</Label>
                    <Input
                        id="produtividade"
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        {...register("produtividade_meta_sc_ha")}
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="preco">Preço Venda Previsto</Label>
                    <Input
                        id="preco"
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        {...register("preco_venda_previsto")}
                    />
                </div>
            </div>

            {/* Submit */}
            <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Salvando..." : "Criar Cultivo"}
            </Button>
        </form>
    );
}
