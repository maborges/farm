"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import {
  Form, FormControl, FormField, FormItem,
  FormLabel, FormMessage,
} from "@/components/ui/form";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Hash, Loader2, Pencil, RotateCcw, History } from "lucide-react";

interface SequencialConfig {
  entidade: string;
  label: string;
  prefixo: string;
  digitos: number;
  escopo: "ANO" | "GLOBAL";
  personalizado: boolean;
  ultimo_numero: number;
}

const sequencialSchema = z.object({
  prefixo: z.string().min(2, "Mínimo 2 caracteres").max(6, "Máximo 6 caracteres"),
  digitos: z.number().int().min(4, "Mínimo 4 dígitos").max(8, "Máximo 8 dígitos"),
  escopo: z.enum(["ANO", "GLOBAL"]),
});

type SequencialFormValues = z.infer<typeof sequencialSchema>;

const resetSchema = z.object({
  ultimo_numero: z.number().int().min(0, "Não pode ser negativo"),
});

type ResetFormValues = z.infer<typeof resetSchema>;

function exemplo(cfg: Pick<SequencialConfig, "prefixo" | "digitos" | "escopo">): string {
  const numero = "1".padStart(cfg.digitos, "0");
  return cfg.escopo === "ANO" ? `${cfg.prefixo}-2026-${numero}` : `${cfg.prefixo}-${numero}`;
}

export function SequenciaisManager({ initialData }: { initialData?: SequencialConfig[] } = {}) {
  const queryClient = useQueryClient();
  const [editando, setEditando] = useState<SequencialConfig | null>(null);
  const [restaurando, setRestaurando] = useState<SequencialConfig | null>(null);
  const [resetando, setResetando] = useState<SequencialConfig | null>(null);

  const { data: configs = [], isLoading } = useQuery<SequencialConfig[]>({
    queryKey: ["config-sequenciais"],
    queryFn: () => apiFetch("config/sequenciais"),
    initialData: initialData ?? undefined,
  });

  const form = useForm<SequencialFormValues>({
    resolver: zodResolver(sequencialSchema),
    defaultValues: { prefixo: "", digitos: 6, escopo: "ANO" },
  });
  const prefixo = form.watch("prefixo");
  const digitos = form.watch("digitos");
  const escopo = form.watch("escopo");

  useEffect(() => {
    if (editando) {
      form.reset({ prefixo: editando.prefixo, digitos: editando.digitos, escopo: editando.escopo });
    }
  }, [editando, form]);

  const resetForm = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { ultimo_numero: 0 },
  });

  useEffect(() => {
    if (resetando) {
      resetForm.reset({ ultimo_numero: resetando.ultimo_numero });
    }
  }, [resetando, resetForm]);

  const salvarMutation = useMutation({
    mutationFn: (payload: { entidade: string } & SequencialFormValues) =>
      apiFetch(`config/sequenciais/${payload.entidade}`, {
        method: "PUT",
        body: JSON.stringify({ prefixo: payload.prefixo, digitos: payload.digitos, escopo: payload.escopo }),
      }),
    onSuccess: () => {
      toast.success("Padrão de código de referência atualizado.");
      queryClient.invalidateQueries({ queryKey: ["config-sequenciais"] });
      setEditando(null);
      setRestaurando(null);
    },
    onError: (err: Error) => toast.error(err.message || "Falha ao salvar."),
  });

  function onSubmit(values: SequencialFormValues) {
    if (!editando) return;
    salvarMutation.mutate({ entidade: editando.entidade, ...values });
  }

  const resetMutation = useMutation({
    mutationFn: ({ entidade, ultimo_numero }: { entidade: string } & ResetFormValues) =>
      apiFetch(`config/sequenciais/${entidade}/resetar`, {
        method: "POST",
        body: JSON.stringify({ ultimo_numero }),
      }),
    onSuccess: () => {
      toast.success("Numeração ajustada.");
      queryClient.invalidateQueries({ queryKey: ["config-sequenciais"] });
      setResetando(null);
    },
    onError: (err: Error) => toast.error(err.message || "Falha ao ajustar numeração."),
  });

  function onSubmitReset(values: ResetFormValues) {
    if (!resetando) return;
    resetMutation.mutate({ entidade: resetando.entidade, ...values });
  }

  const columns: ColumnDef<SequencialConfig>[] = [
    { id: "label", header: "Entidade", accessorKey: "label", sortable: true },
    {
      id: "exemplo",
      header: "Exemplo",
      accessorFn: (row) => exemplo(row),
      cell: (value) => <span className="font-mono text-xs">{value}</span>,
    },
    {
      id: "escopo",
      header: "Escopo",
      accessorFn: (row) => (row.escopo === "ANO" ? "Reinicia por ano" : "Contínuo"),
    },
    {
      id: "ultimo_numero",
      header: "Último emitido",
      accessorFn: (row) => row.ultimo_numero,
      cell: (value) => <span className="font-mono text-xs tabular-nums">{value}</span>,
    },
    {
      id: "padrao",
      header: "Padrão",
      exportable: false,
      filterable: false,
      cell: (_, row) =>
        row.personalizado ? (
          <Badge variant="outline" className="h-4 rounded-sm text-[9px] font-black uppercase">Personalizado</Badge>
        ) : (
          <Badge variant="secondary" className="h-4 rounded-sm text-[9px] font-black uppercase">Padrão da aplicação</Badge>
        ),
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            aria-label="Editar"
            onClick={() => setEditando(row)}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            aria-label="Ajustar numeração"
            onClick={() => setResetando(row)}
          >
            <History className="size-3.5" />
          </Button>
          {row.personalizado && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive"
              aria-label="Restaurar padrão"
              onClick={() => setRestaurando(row)}
            >
              <RotateCcw className="size-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Código de referência legível gerado automaticamente para comunicação com fornecedores/clientes
        (ex: <span className="font-mono">PED-2026-000123</span>). A aplicação define um padrão, mas
        cada fazenda pode personalizar o prefixo, a quantidade de dígitos e se a numeração reinicia por ano.
      </p>

      <DataTable
        data={configs}
        columns={columns}
        isLoading={isLoading}
        searchable={true}
        exportable={true}
        emptyMessage="Nenhuma entidade com código de referência configurável."
      />

      <Dialog open={!!editando} onOpenChange={(open) => !open && setEditando(null)}>
        <DialogContent className="sm:max-w-[440px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Hash className="size-4" />
              </div>
              <div className="min-w-0">
                <DialogTitle>Código de referência</DialogTitle>
                <DialogDescription className="truncate text-xs leading-tight">{editando?.label}</DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
              <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-2.5">
                <FormField
                  control={form.control}
                  name="prefixo"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Prefixo</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={6}
                          className="h-8 rounded-sm uppercase"
                          onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                        />
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="digitos"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Quantidade de dígitos</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={4}
                          max={8}
                          className="h-8 rounded-sm"
                          value={field.value}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="escopo"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Escopo da numeração</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ANO">Reinicia todo ano</SelectItem>
                            <SelectItem value="GLOBAL">Contínuo (nunca reinicia)</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />

                <div className="rounded-sm border bg-muted/20 p-3">
                  <p className="mb-0.5 text-[9px] font-black uppercase text-muted-foreground tracking-wider">Prévia</p>
                  <p className="font-mono text-sm font-bold text-primary">
                    {exemplo({ prefixo: prefixo || "?", digitos: digitos || 6, escopo: escopo || "ANO" })}
                  </p>
                </div>
              </DialogBody>

              <DialogFooter className="border-t px-4 py-2.5">
                <Button type="button" variant="ghost" size="sm" onClick={() => setEditando(null)}>
                  Cancelar
                </Button>
                <Button type="submit" variant="outline" size="sm" disabled={salvarMutation.isPending}>
                  {salvarMutation.isPending ? (
                    <>
                      <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                      Salvando...
                    </>
                  ) : "Salvar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!resetando} onOpenChange={(open) => !open && setResetando(null)}>
        <DialogContent className="sm:max-w-[440px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <History className="size-4" />
              </div>
              <div className="min-w-0">
                <DialogTitle>Ajustar numeração</DialogTitle>
                <DialogDescription className="truncate text-xs leading-tight">{resetando?.label}</DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <Form {...resetForm}>
            <form onSubmit={resetForm.handleSubmit(onSubmitReset)} className="flex min-h-0 flex-1 flex-col">
              <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-2.5">
                <p className="text-xs text-muted-foreground">
                  Use para continuar uma numeração já em uso em um controle legado (planilha, sistema
                  anterior etc). O próximo código emitido será o número informado + 1.
                </p>

                <FormField
                  control={resetForm.control}
                  name="ultimo_numero"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Último número já utilizado</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          className="h-8 rounded-sm"
                          value={field.value}
                          onChange={(e) => field.onChange(Number(e.target.value))}
                        />
                      </FormControl>
                      <FormMessage className="text-[10px]" />
                    </FormItem>
                  )}
                />

                {resetando && (
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="mb-0.5 text-[9px] font-black uppercase text-muted-foreground tracking-wider">Próximo código emitido</p>
                    <p className="font-mono text-sm font-bold text-primary">
                      {exemplo({
                        prefixo: resetando.prefixo,
                        digitos: resetando.digitos,
                        escopo: resetando.escopo,
                      }).replace(/\d+$/, String((resetForm.watch("ultimo_numero") || 0) + 1).padStart(resetando.digitos, "0"))}
                    </p>
                  </div>
                )}
              </DialogBody>

              <DialogFooter className="border-t px-4 py-2.5">
                <Button type="button" variant="ghost" size="sm" onClick={() => setResetando(null)}>
                  Cancelar
                </Button>
                <Button type="submit" variant="outline" size="sm" disabled={resetMutation.isPending}>
                  {resetMutation.isPending ? (
                    <>
                      <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                      Salvando...
                    </>
                  ) : "Confirmar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!restaurando} onOpenChange={(open) => !open && setRestaurando(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restaurar padrão da aplicação?</AlertDialogTitle>
            <AlertDialogDescription>
              O código de referência de <strong>{restaurando?.label}</strong> voltará ao formato padrão
              da aplicação. Números já emitidos não são alterados.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={salvarMutation.isPending}
              onClick={() =>
                restaurando &&
                salvarMutation.mutate({
                  entidade: restaurando.entidade,
                  prefixo: restaurando.prefixo,
                  digitos: restaurando.digitos,
                  escopo: restaurando.escopo,
                })
              }
            >
              Restaurar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
