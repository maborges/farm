"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod/v4"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import { Loader2, Star } from "lucide-react"
import { useEffect, useState } from "react"

const planSchema = z.object({
    name: z.string().min(1, "Nome é obrigatório"),
    description: z.string().min(1, "Descrição é obrigatória"),
    price: z.coerce.number().min(0, "Preço deve ser positivo"),
    billing_period: z.enum(["monthly", "annually"]),
    features: z.string().transform((val) => val.split("\n").filter(f => f.trim() !== "")),
    is_active: z.boolean(),
    is_default: z.boolean(),
})

type PlanFormValues = z.infer<typeof planSchema>

interface PlanModalProps {
    plan?: any
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function PlanModal({ plan, open, onOpenChange }: PlanModalProps) {
    const { toast } = useToast()
    const queryClient = useQueryClient()

    const {
        register,
        handleSubmit,
        reset,
        setValue,
        watch,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(planSchema),
        defaultValues: {
            name: "",
            description: "",
            price: 0,
            billing_period: "monthly",
            features: "",
            is_active: true,
            is_default: false,
        },
    })

    useEffect(() => {
        if (plan && open) {
            reset({
                ...plan,
                features: plan.features.join("\n")
            })
        } else if (!plan && open) {
            reset({
                name: "",
                description: "",
                price: 0,
                billing_period: "monthly",
                features: "",
                is_active: true,
                is_default: false,
            })
        }
    }, [plan, open, reset])

    const isActive = watch("is_active")
    const billingPeriod = watch("billing_period")

    const mutation = useMutation({
        mutationFn: async (values: PlanFormValues) => {
            if (plan?.id) {
                await apiFetch(`/backoffice/plans/${plan.id}`, {
                    method: "PUT",
                    body: JSON.stringify(values),
                });
            } else {
                await apiFetch("/backoffice/plans", {
                    method: "POST",
                    body: JSON.stringify(values),
                });
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["plans"] })
            toast({
                title: plan?.id ? "Plano atualizado" : "Plano criado",
                description: `O plano foi ${plan?.id ? 'atualizado' : 'criado'} com sucesso.`,
            })
            onOpenChange(false)
        },
        onError: (error: any) => {
            toast({
                title: "Erro",
                description: error.message,
                variant: "destructive",
            })
        },
    })

    const onSubmit = (data: any) => {
        mutation.mutate(data)
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-3xl max-h-[90vh] p-0 flex flex-col overflow-hidden">
                <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
                    <DialogTitle>{plan?.id ? "Editar Plano" : "Novo Plano"}</DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0">
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Nome do Plano</Label>
                            <Input id="name" {...register("name")} placeholder="Ex: Planejamento" />
                            {errors.name && <p className="text-xs text-destructive">{errors.name.message as string}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Descrição</Label>
                            <Textarea id="description" {...register("description")} placeholder="Breve descrição do plano" />
                            {errors.description && <p className="text-xs text-destructive">{errors.description.message as string}</p>}
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="price">Preço</Label>
                                <Input id="price" type="number" step="0.01" {...register("price")} />
                                {errors.price && <p className="text-xs text-destructive">{errors.price.message as string}</p>}
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="billing_period">Ciclo de Cobrança</Label>
                                <Select
                                    value={billingPeriod}
                                    onValueChange={(val) => setValue("billing_period", val as "monthly" | "annually")}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Selecione" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="monthly">Mensal</SelectItem>
                                        <SelectItem value="annually">Anual</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="features">Funcionalidades (uma por linha)</Label>
                            <Textarea
                                id="features"
                                {...register("features")}
                                placeholder="Gestao de rebanho&#10;Controle financeiro"
                                className="min-h-[100px]"
                            />
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-sm border bg-amber-50/30 border-amber-200">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2 text-sm font-medium text-amber-700">
                                    <Star className="size-4" />
                                    Plano Padrão
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Plano atribuído automaticamente no onboarding
                                </p>
                            </div>
                            <Switch
                                id="is_default"
                                checked={watch("is_default")}
                                onCheckedChange={(checked) => setValue("is_default", checked)}
                            />
                        </div>
                        <div className="flex items-center justify-between">
                            <Label htmlFor="is_active">Status Ativo</Label>
                            <Switch
                                id="is_active"
                                checked={isActive}
                                onCheckedChange={(checked) => setValue("is_active", checked)}
                            />
                        </div>
                    </form>
                </div>

                <DialogFooter className="px-6 py-4 border-t shrink-0">
                    <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                        Cancelar
                    </Button>
                    <Button type="submit" disabled={mutation.isPending} onClick={(e) => {
                        e.preventDefault()
                        handleSubmit(onSubmit)()
                    }}>
                        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {plan?.id ? "Atualizar" : "Salvar"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
