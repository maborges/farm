"use client";

import { useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Form, FormControl, FormField, FormItem,
  FormLabel, FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { parseLocaleNumber } from "@/lib/utils";
import { toast } from "sonner";
import { DollarSign, Truck, Loader2, CreditCard, Package, Check } from "lucide-react";
import { FornecedorCombobox } from "@/components/shared";

interface ItemCotavel {
  id: string;
  produto_id: string;
  produto_nome?: string | null;
  quantidade_solicitada: number;
  quantidade_alocada?: number;
  unidade: string;
  valor_ultima_compra?: number | null;
  data_ultima_compra?: string | null;
}

const saldoPendente = (item: ItemCotavel) => item.quantidade_solicitada - (item.quantidade_alocada ?? 0);

const formatCurrency = (value?: number | null) =>
  value == null
    ? "-"
    : value.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

const decimalOptionalSchema = z.preprocess((value) => {
  if (typeof value === "number") return Number.isFinite(value) ? value : undefined;
  if (typeof value !== "string" || value.trim() === "") return undefined;
  const parsed = parseLocaleNumber(value, NaN);
  return Number.isNaN(parsed) ? undefined : parsed;
}, z.number().optional());

const buildSchema = (itens: ItemCotavel[]) => z.object({
  fornecedor_id: z.string().min(1, "Selecione um fornecedor"),
  condicoes_pagamento: z.string().max(100).optional(),
  prazo_entrega_dias: z.number().int("Informe dias inteiros").min(0, "Prazo não pode ser negativo").optional(),
  itens: z.array(z.object({
    solicitacao_item_id: z.string(),
    incluido: z.boolean(),
    valor_unitario: decimalOptionalSchema,
    quantidade_atendida: decimalOptionalSchema,
  })),
}).superRefine((data, ctx) => {
  if (!data.itens.some((i) => i.incluido && i.valor_unitario && i.valor_unitario > 0)) {
    ctx.addIssue({ code: "custom", message: "Marque ao menos um item e informe o valor unitário.", path: ["itens"] });
  }
  data.itens.forEach((i, idx) => {
    if (!i.incluido) return;
    const saldo = itens[idx] ? saldoPendente(itens[idx]) : Infinity;
    if (i.quantidade_atendida != null && i.quantidade_atendida > saldo) {
      ctx.addIssue({
        code: "custom",
        message: `Não pode superar o saldo pendente (${saldo}).`,
        path: ["itens", idx, "quantidade_atendida"],
      });
    }
  });
});

type FormValues = z.infer<ReturnType<typeof buildSchema>>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  solicitacaoId: string;
  itens: ItemCotavel[];
}

/** Cotação cobrindo múltiplos itens da solicitação — o fornecedor pode não ter
 * preço para todos (cotação parcial); o comprador marca só os que ele cotou. */
export function CotacaoMultiItemDialog({ isOpen, onClose, solicitacaoId, itens }: Props) {
  const queryClient = useQueryClient();

  const schema = buildSchema(itens);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      fornecedor_id: "",
      condicoes_pagamento: "",
      prazo_entrega_dias: undefined,
      itens: itens.map((item) => ({ solicitacao_item_id: item.id, incluido: false, valor_unitario: undefined, quantidade_atendida: saldoPendente(item) })),
    },
  });
  const { fields } = useFieldArray({ control: form.control, name: "itens" });

  useEffect(() => {
    if (isOpen) {
      form.reset({
        fornecedor_id: "",
        condicoes_pagamento: "",
        prazo_entrega_dias: undefined,
        itens: itens.map((item) => ({ solicitacao_item_id: item.id, incluido: false, valor_unitario: undefined, quantidade_atendida: saldoPendente(item) })),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, solicitacaoId]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes`, {
        method: "POST",
        body: JSON.stringify({
          fornecedor_id: values.fornecedor_id,
          condicoes_pagamento: values.condicoes_pagamento,
          prazo_entrega_dias: values.prazo_entrega_dias,
          itens: values.itens
            .filter((i) => i.incluido && i.valor_unitario)
            .map((i) => ({
              solicitacao_item_id: i.solicitacao_item_id,
              valor_unitario: i.valor_unitario,
              quantidade_atendida: i.quantidade_atendida,
            })),
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes-cotacoes", solicitacaoId] });
      toast.success("Cotação registrada com sucesso!");
      onClose();
    },
    onError: () => toast.error("Erro ao registrar cotação."),
  });

  function onSubmit(values: FormValues) {
    mutation.mutate(values);
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[740px] rounded-sm p-0">
        <DialogHeader className="border-b px-4 py-2.5">
          <div className="flex items-center gap-3">
            <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <DollarSign className="size-4" />
            </div>
            <div className="min-w-0">
              <DialogTitle>Registrar Cotação</DialogTitle>
              <DialogDescription className="truncate text-xs leading-tight">
                {itens.length} itens — marque os que este fornecedor cotou
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
            <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-2.5">
              <FormField
                control={form.control}
                name="fornecedor_id"
                render={({ field }) => (
                  <FormItem className="space-y-1">
                    <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Fornecedor</FormLabel>
                    <FormControl>
                      <FornecedorCombobox
                        value={field.value}
                        onChange={field.onChange}
                        onSelectFornecedor={(f) => {
                          if (!form.getValues("condicoes_pagamento")) {
                            form.setValue("condicoes_pagamento", f.condicoes_pagamento ?? "");
                          }
                          if (f.prazo_entrega_dias != null && form.getValues("prazo_entrega_dias") == null) {
                            form.setValue("prazo_entrega_dias", f.prazo_entrega_dias);
                          }
                        }}
                      />
                    </FormControl>
                    <FormMessage className="text-[10px]" />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="condicoes_pagamento"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Condições de Pagamento</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                          <Input placeholder="Ex: 30% adiantado + 30 dias" {...field} className="pl-9 h-8 rounded-sm text-xs" />
                        </div>
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="prazo_entrega_dias"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Prazo (Dias)</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Truck className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                          <Input
                            type="number"
                            min="0"
                            step="1"
                            placeholder="0"
                            name={field.name}
                            ref={field.ref}
                            onBlur={field.onBlur}
                            value={field.value ?? ""}
                            onChange={(event) => field.onChange(event.target.value === "" ? undefined : event.target.valueAsNumber)}
                            className="pl-9 h-8 rounded-sm text-xs w-full"
                          />
                        </div>
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />
              </div>

              <div className="space-y-1.5 mt-2">
                <p className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Itens cotados</p>
                <div className="rounded-sm border divide-y overflow-hidden">
                  <div className="flex items-center gap-3 bg-muted/40 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                    <div className="shrink-0 w-4" />
                    <div className="shrink-0 size-8" />
                    <div className="min-w-0 flex-1" />
                    <div className="shrink-0 w-28 text-right">Últ. Compra</div>
                    <div className="shrink-0 w-24 text-center">Quantidade</div>
                    <div className="shrink-0 w-32 text-center">Valor unitário</div>
                  </div>
                  {fields.map((field, index) => {
                    const item = itens[index];
                    const incluido = form.watch(`itens.${index}.incluido`);
                    return (
                      <div key={field.id} className={`flex items-center gap-3 px-3 py-2.5 transition-colors ${incluido ? "bg-card" : "bg-muted/30 opacity-70"}`}>
                        <FormField
                          control={form.control}
                          name={`itens.${index}.incluido`}
                          render={({ field }) => (
                            <FormItem className="mb-0 space-y-0 shrink-0">
                              <FormControl>
                                <Checkbox checked={field.value} onCheckedChange={field.onChange} className="mt-0.5" />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                        <div className={`flex size-8 items-center justify-center rounded-sm shrink-0 ${incluido ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
                          <Package className="size-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <span className={`block truncate text-xs font-semibold ${incluido ? "" : "line-through text-muted-foreground"}`}>{item?.produto_nome}</span>
                          <span className="text-[10px] text-muted-foreground font-mono font-medium">
                            {item && item.quantidade_alocada ? (
                              <>Saldo pendente: {saldoPendente(item).toFixed(1)} {item.unidade} <span className="opacity-70">(de {item.quantidade_solicitada.toFixed(1)})</span></>
                            ) : (
                              <>Solicitado: {Number(item?.quantidade_solicitada).toFixed(1)} {item?.unidade}</>
                            )}
                          </span>
                        </div>
                        <div
                          className="w-28 shrink-0 text-right font-mono text-xs font-semibold text-muted-foreground"
                          title={item?.data_ultima_compra ? `Última compra em ${new Date(item.data_ultima_compra).toLocaleDateString("pt-BR")}` : "Sem compra anterior"}
                        >
                          {formatCurrency(item?.valor_ultima_compra)}
                        </div>
                        <FormField
                          control={form.control}
                          name={`itens.${index}.quantidade_atendida`}
                          render={({ field, fieldState }) => (
                            <FormItem className="mb-0 w-24 shrink-0 space-y-0">
                              <FormControl>
                                <Input
                                  type="text"
                                  inputMode="decimal"
                                  placeholder="Qtd."
                                  disabled={!incluido}
                                  name={field.name}
                                  ref={field.ref}
                                  onBlur={field.onBlur}
                                  value={field.value ?? ""}
                                  onChange={(event) => {
                                    field.onChange(event.target.value);
                                  }}
                                  className={`h-8 rounded-sm text-xs font-mono font-medium ${!incluido ? "bg-muted cursor-not-allowed" : ""} ${fieldState.error ? "border-destructive" : ""}`}
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name={`itens.${index}.valor_unitario`}
                          render={({ field }) => (
                            <FormItem className="mb-0 w-32 shrink-0 space-y-0">
                              <FormControl>
                                <div className="relative">
                                  <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                                  <Input
                                    type="text"
                                    inputMode="decimal"
                                    placeholder="0.00"
                                    disabled={!incluido}
                                    name={field.name}
                                    ref={field.ref}
                                    onBlur={field.onBlur}
                                    value={field.value ?? ""}
                                    onChange={(event) => {
                                      field.onChange(event.target.value);
                                    }}
                                    className={`pl-7 h-8 rounded-sm text-xs font-mono font-medium ${!incluido ? "bg-muted cursor-not-allowed" : ""}`}
                                  />
                                </div>
                              </FormControl>
                            </FormItem>
                          )}
                        />
                      </div>
                    );
                  })}
                </div>
                {form.formState.errors.itens?.root?.message && (
                  <p className="text-[10px] font-medium text-destructive">{form.formState.errors.itens.root.message}</p>
                )}
              </div>
            </DialogBody>

            <DialogFooter className="border-t px-4 py-2.5">
              <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" variant="default" size="sm" disabled={mutation.isPending}>
                {mutation.isPending ? (
                  <>
                    <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  <>
                    <Check data-icon="inline-start" className="size-3" />
                    Registrar Cotação
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
