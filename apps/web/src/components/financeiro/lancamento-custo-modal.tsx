"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { HandCoins } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";
import { trackCTA } from "@/lib/analytics";

const CATEGORIAS = [
    { value: "INSUMOS", label: "Insumos" },
    { value: "MAO_OBRA", label: "Mão de obra" },
    { value: "OPERACOES", label: "Operações" },
    { value: "ADMINISTRATIVO", label: "Administrativo" },
] as const;

const schema = z.object({
    descricao: z.string().min(1, "Descrição obrigatória").max(200),
    valor: z.coerce.number().positive("Valor deve ser maior que zero"),
    data: z.string().min(1, "Data obrigatória"),
    categoria: z.string().default("OPERACOES"),
});

type FormInput = z.input<typeof schema>;
type FormData = z.output<typeof schema>;

interface Props {
    open: boolean;
    onClose: () => void;
}

export function LancamentoCustoModal({ open, onClose }: Props) {
    const queryClient = useQueryClient();

    const { register, handleSubmit, reset, setValue, control, formState: { errors } } = useForm<FormInput, unknown, FormData>({
        resolver: zodResolver(schema),
        defaultValues: {
            data: format(new Date(), "yyyy-MM-dd"),
            categoria: "OPERACOES",
        },
    });
    const categoriaAtual = useWatch({ control, name: "categoria" });

    const mutation = useMutation({
        mutationFn: (data: FormData) =>
            apiFetch("/financeiro/lancamentos/", {
                method: "POST",
                body: JSON.stringify({ ...data, tipo: "CUSTO" }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["lancamentos-resumo"] });
            queryClient.invalidateQueries({ queryKey: ["lancamentos-insight"] });
            // Invalida todos os alertas independente do safraId (prefixo)
            queryClient.invalidateQueries({ queryKey: ["financeiro-alertas"], exact: false });
            trackCTA({ event: "upgrade_intention_created", context: "primeiro_custo_lancado" });
            toast.success("Custo registrado com sucesso!");
            reset();
            onClose();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <HandCoins className="size-5 text-primary" />
                        Lançar custo
                    </DialogTitle>
                </DialogHeader>

                <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4 py-2">
                    <div className="space-y-1">
                        <Label htmlFor="descricao">Descrição *</Label>
                        <Input
                            id="descricao"
                            {...register("descricao")}
                            placeholder="Ex: Adubo, Defensivo, Combustível..."
                        />
                        {errors.descricao && (
                            <p className="text-xs text-destructive">{errors.descricao.message}</p>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                            <Label htmlFor="valor">Valor (R$) *</Label>
                            <Input
                                id="valor"
                                type="number"
                                step="0.01"
                                min="0.01"
                                {...register("valor")}
                                placeholder="0,00"
                            />
                            {errors.valor && (
                                <p className="text-xs text-destructive">{errors.valor.message}</p>
                            )}
                        </div>

                        <div className="space-y-1">
                            <Label htmlFor="data">Data *</Label>
                            <Input id="data" type="date" {...register("data")} />
                        </div>
                    </div>

                    <div className="space-y-1">
                        <Label>Categoria</Label>
                        <Select
                            value={categoriaAtual}
                            onValueChange={(v) => setValue("categoria", v)}
                        >
                            <SelectTrigger>
                                <span className="truncate">
                                    {CATEGORIAS.find((c) => c.value === categoriaAtual)?.label ?? "Selecione a categoria"}
                                </span>
                            </SelectTrigger>
                            <SelectContent>
                                {CATEGORIAS.map((c) => (
                                    <SelectItem key={c.value} value={c.value}>
                                        {c.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <DialogFooter className="pt-2">
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={mutation.isPending}>
                            {mutation.isPending ? "Salvando..." : "Salvar custo"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
