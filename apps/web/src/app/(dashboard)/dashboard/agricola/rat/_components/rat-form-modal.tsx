"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useHasTier } from "@/hooks/use-has-tier";
import { 
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { 
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "@/components/ui/select";
import { Loader2, Plus, FileText } from "lucide-react";
import { RelatorioTecnicoCreateSchema, type RelatorioTecnicoCreate } from "@farm/zod-schemas";
import { useAppStore } from "@/lib/stores/app-store";

interface RatFormModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function RatFormModal({ open, onOpenChange }: RatFormModalProps) {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");

    const { register, handleSubmit, control, reset, formState: { errors } } = useForm<RelatorioTecnicoCreate>({
        resolver: zodResolver(RelatorioTecnicoCreateSchema),
        defaultValues: {
            data_visita: new Date().toISOString().split("T")[0],
            status: "RASCUNHO",
            condicao_climatica: {},
            constatacoes: [],
        }
    });

    const { data: safras = [] } = useQuery({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch<any[]>(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && hasProfessionalTier,
    });

    const { data: talhoes = [] } = useQuery({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch<any[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && hasProfessionalTier,
    });

    const mutation = useMutation({
        mutationFn: (data: any) => apiFetch("/agronomo/rat/", {
            method: "POST",
            body: JSON.stringify(data),
        }),
        onSuccess: () => {
            toast.success("Relatório Técnico cadastrado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["relatorios-tecnicos"] });
            reset();
            onOpenChange(false);
        },
        onError: (err: any) => toast.error(err.message || "Erro ao cadastrar relatório"),
    });

    const inputClass = "h-8 rounded-sm text-xs";

    if (!hasProfessionalTier) {
        return null;
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px] rounded-sm">
                <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-primary">
                            <FileText className="size-5" />
                            Novo Relatório Agrônomo Técnico (RAT)
                        </DialogTitle>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <Label htmlFor="safra_id" className="text-xs font-semibold">Safra</Label>
                                <Controller
                                    name="safra_id"
                                    control={control}
                                    render={({ field }) => (
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <SelectTrigger id="safra_id" className={inputClass}>
                                                <SelectValue placeholder="Selecione a Safra" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-sm">
                                                {safras.map((s: any) => (
                                                    <SelectItem key={s.id} value={s.id}>{s.ano_safra} - {s.cultura}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    )}
                                />
                                {errors.safra_id && <p className="text-[10px] text-destructive">{errors.safra_id.message as string}</p>}
                            </div>

                            <div className="space-y-1.5">
                                <Label htmlFor="talhao_id" className="text-xs font-semibold">Talhão</Label>
                                <Controller
                                    name="talhao_id"
                                    control={control}
                                    render={({ field }) => (
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <SelectTrigger id="talhao_id" className={inputClass}>
                                                <SelectValue placeholder="Selecione o Talhão" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-sm">
                                                {talhoes.map((t: any) => (
                                                    <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    )}
                                />
                                {errors.talhao_id && <p className="text-[10px] text-destructive">{errors.talhao_id.message as string}</p>}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <Label htmlFor="data_visita" className="text-xs font-semibold">Data da Visita</Label>
                                <Input
                                    id="data_visita"
                                    type="date"
                                    className={inputClass}
                                    {...register("data_visita")}
                                />
                                {errors.data_visita && <p className="text-[10px] text-destructive">{errors.data_visita.message as string}</p>}
                            </div>

                            <div className="space-y-1.5">
                                <Label htmlFor="estadio_fenologico" className="text-xs font-semibold">Estádio Fenológico</Label>
                                <Input
                                    id="estadio_fenologico"
                                    placeholder="Ex: V4, R1, enchimento de grãos"
                                    className={inputClass}
                                    {...register("estadio_fenologico")}
                                />
                                {errors.estadio_fenologico && <p className="text-[10px] text-destructive">{errors.estadio_fenologico.message as string}</p>}
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="recomendacoes" className="text-xs font-semibold">Recomendações</Label>
                            <Input 
                                id="recomendacoes" 
                                placeholder="Ex: Monitorar presença de pragas na bordadura" 
                                className={inputClass} 
                                {...register("recomendacoes")} 
                            />
                            {errors.recomendacoes && <p className="text-[10px] text-destructive">{errors.recomendacoes.message as string}</p>}
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="observacoes_gerais" className="text-xs font-semibold">Observações Gerais</Label>
                            <Textarea 
                                id="observacoes_gerais" 
                                placeholder="Descreva as condições gerais observadas..." 
                                className="min-h-[100px] rounded-sm text-xs" 
                                {...register("observacoes_gerais")} 
                            />
                        </div>
                    </div>

                    <DialogFooter className="gap-2">
                        <Button 
                            type="button" 
                            variant="outline" 
                            size="sm" 
                            className="rounded-sm border-none"
                            onClick={() => onOpenChange(false)}
                        >
                            Cancelar
                        </Button>
                        <Button 
                            type="submit" 
                            size="sm" 
                            className="rounded-sm" 
                            disabled={mutation.isPending}
                        >
                            {mutation.isPending ? (
                                <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                            ) : (
                                <Plus className="size-3.5 mr-1.5" />
                            )}
                            {mutation.isPending ? "Salvando..." : "Salvar Relatório"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
