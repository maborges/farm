"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2 } from "lucide-react";

const abastecimentoSchema = z.object({
    equipamento_id: z.string().uuid("Selecione um equipamento"),
    data: z.string().min(1, "Data é obrigatória"),
    horimetro_na_data: z.coerce.number().min(0, "Mínimo 0"),
    km_na_data: z.coerce.number().min(0).optional(),
    tipo_combustivel: z.string().default("DIESEL"),
    litros: z.coerce.number().min(0.1, "Mínimo 0,1 L"),
    preco_litro: z.coerce.number().min(0, "Mínimo 0"),
    tanque_cheio: z.boolean().default(true),
    local: z.enum(["INTERNO", "EXTERNO"]),
    observacoes: z.string().optional(),
});

type AbastecimentoFormValues = z.infer<typeof abastecimentoSchema>;
type AbastecimentoFormInput = z.input<typeof abastecimentoSchema>;

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initialData?: any;
}

export function AbastecimentoFormModal({ open, onOpenChange, initialData }: Props) {
    const queryClient = useQueryClient();
    
    const { data: maquinas } = useQuery<any[]>({
        queryKey: ["maquinas"],
        queryFn: () => apiFetch("/frota/maquinas"),
        enabled: open,
    });

    const form = useForm<AbastecimentoFormInput, unknown, AbastecimentoFormValues>({
        resolver: zodResolver(abastecimentoSchema),
        defaultValues: initialData || {
            data: new Date().toISOString().split("T")[0],
            tipo_combustivel: "DIESEL",
            tanque_cheio: true,
            local: "INTERNO",
            preco_litro: 0,
            litros: 0,
            horimetro_na_data: 0,
        },
    });

    const toInputValue = (value: unknown): string | number => {
        return typeof value === "string" || typeof value === "number" ? value : "";
    };

    const mutation = useMutation({
        mutationFn: (values: AbastecimentoFormValues) => {
            const url = initialData ? `/frota/abastecimentos/${initialData.id}` : "/frota/abastecimentos";
            return apiFetch(url, {
                method: initialData ? "PATCH" : "POST",
                body: JSON.stringify({
                    ...values,
                    data: new Date(values.data).toISOString(),
                }),
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["abastecimentos"] });
            toast.success(initialData ? "Registro atualizado!" : "Abastecimento registrado!");
            onOpenChange(false);
            form.reset();
        },
        onError: (error: unknown) => {
            toast.error(error instanceof Error ? error.message : "Erro ao salvar registro");
        },
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-h-[calc(100dvh-2rem)] w-[calc(100%-1rem)] overflow-y-auto rounded-sm sm:max-w-[600px]">
                <Form {...form}>
                    <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
                        <DialogHeader>
                            <DialogTitle>{initialData ? "Editar Abastecimento" : "Novo Abastecimento"}</DialogTitle>
                        </DialogHeader>

                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <FormField
                                control={form.control}
                                name="equipamento_id"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Equipamento</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger className="h-10 rounded-sm">
                                                    <SelectValue placeholder="Selecione..." />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {maquinas?.map((m) => (
                                                    <SelectItem key={m.id} value={m.id}>
                                                        {m.nome}
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
                                name="data"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Data</FormLabel>
                                        <FormControl>
                                            <Input type="date" className="h-10 rounded-sm" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <FormField
                                control={form.control}
                                name="horimetro_na_data"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Horímetro</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                step="0.1"
                                                className="h-10 rounded-sm"
                                                name={field.name}
                                                value={toInputValue(field.value)}
                                                onChange={field.onChange}
                                                onBlur={field.onBlur}
                                                ref={field.ref}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="litros"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Litros</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                step="0.01"
                                                className="h-10 rounded-sm"
                                                name={field.name}
                                                value={toInputValue(field.value)}
                                                onChange={field.onChange}
                                                onBlur={field.onBlur}
                                                ref={field.ref}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="preco_litro"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Preço/L (R$)</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                step="0.001"
                                                className="h-10 rounded-sm"
                                                name={field.name}
                                                value={toInputValue(field.value)}
                                                onChange={field.onChange}
                                                onBlur={field.onBlur}
                                                ref={field.ref}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <FormField
                                control={form.control}
                                name="local"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Local de Abastecimento</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger className="h-10 rounded-sm">
                                                    <SelectValue placeholder="Selecione..." />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="INTERNO">Silo Próprio (Estoque)</SelectItem>
                                                <SelectItem value="EXTERNO">Posto Externo (Financeiro)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="tipo_combustivel"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Combustível</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger className="h-10 rounded-sm">
                                                    <SelectValue placeholder="Selecione..." />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="DIESEL S10">Diesel S10</SelectItem>
                                                <SelectItem value="DIESEL S500">Diesel S500</SelectItem>
                                                <SelectItem value="GASOLINA">Gasolina</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="tanque_cheio"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-sm border p-3">
                                    <FormControl>
                                        <Checkbox
                                            checked={Boolean(field.value)}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Tanque Cheio?</FormLabel>
                                    </div>
                                </FormItem>
                            )}
                        />

                        <DialogFooter className="gap-2">
                            <Button className="w-full sm:w-auto" variant="outline" type="button" onClick={() => onOpenChange(false)}>
                                Cancelar
                            </Button>
                            <Button className="w-full sm:w-auto" type="submit" disabled={mutation.isPending}>
                                {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {initialData ? "Salvar Alterações" : "Registrar Abastecimento"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
