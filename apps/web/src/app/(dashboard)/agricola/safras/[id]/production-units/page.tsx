"use client";

import React, { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { toast } from "sonner";
import { Plus, Pencil, Power, BarChart2, AlertCircle, Layers } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getSafraLabel } from "@/lib/safra-label";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProductionUnit {
  id: string;
  safra_id: string;
  cultivo_id: string;
  area_id: string;
  cultivo_area_id: string | null;
  percentual_participacao: number;
  area_ha: number;
  status: "ATIVA" | "ENCERRADA";
  data_inicio: string | null;
  data_fim: string | null;
  cultivo_nome: string | null;
  area_nome: string | null;
  created_at: string;
  updated_at: string;
}

interface Safra {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface Cultivo {
  id: string;
  cultura: string;
  cultivar_nome: string | null;
  areas: CultivoArea[];
}

interface CultivoArea {
  id: string;
  area_id: string;
  area_ha: number;
}

interface AreaRural {
  id: string;
  nome: string;
  codigo: string | null;
  unidade_produtiva_id: string;
  area_hectares: number | null;
  area_hectares_manual: number | null;
}

interface UnidadeProdutiva {
  id: string;
  nome: string;
}

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const puSchema = z.object({
  cultivo_id: z.string().uuid("Selecione um cultivo"),
  area_id: z.string().uuid("Selecione uma área"),
  cultivo_area_id: z.string().uuid().nullable().optional(),
  percentual_participacao: z.coerce.number().min(0).max(100),
  area_ha: z.coerce.number().positive("Área deve ser positiva"),
  data_inicio: z.preprocess((value) => (value === "" ? undefined : value), z.string().optional()),
  data_fim: z.preprocess((value) => (value === "" ? undefined : value), z.string().optional()),
});

type PUFormData = z.infer<typeof puSchema>;
type PUFormInput = z.input<typeof puSchema>;

const updateSchema = z.object({
  percentual_participacao: z.coerce.number().min(0).max(100).optional(),
  area_ha: z.coerce.number().positive().optional(),
  data_inicio: z.preprocess((value) => (value === "" ? undefined : value), z.string().optional()),
  data_fim: z.preprocess((value) => (value === "" ? undefined : value), z.string().optional()),
});

type UpdateFormData = z.infer<typeof updateSchema>;
type UpdateFormInput = z.input<typeof updateSchema>;

function toInputValue(value: unknown): string | number {
  return typeof value === "string" || typeof value === "number" ? value : "";
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ProductionUnitsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: safraId } = use(params);
  const qc = useQueryClient();

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ProductionUnit | null>(null);
  const [encerrandoId, setEncerrandoId] = useState<string | null>(null);

  // ---- Queries ----
  const { data: units = [], isLoading, isError, error } = useQuery<ProductionUnit[]>({
    queryKey: ["production-units", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/production-units`),
  });
  const areaIdsJaUsados = new Set(units.map((unit) => unit.area_id));

  const { data: cultivos = [] } = useQuery<Cultivo[]>({
    queryKey: ["cultivos", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
  });

  const { data: safra } = useQuery<Safra>({
    queryKey: ["safra", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}`),
  });
  const safraLabel = safra ? getSafraLabel(safra) : "Safra";
  const { data: unidadesProdutivas = [] } = useQuery<UnidadeProdutiva[]>({
    queryKey: ["unidades-produtivas"],
    queryFn: () => apiFetch("/cadastros/propriedades"),
  });

  // ---- Mutations ----
  const createMut = useMutation({
    mutationFn: (data: PUFormData & { cultivo_area_id?: string | null }) =>
      apiFetch(`/safras/${safraId}/production-units`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-units", safraId] });
      toast.success("Unidade produtiva criada.");
      setShowCreate(false);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateFormData }) =>
      apiFetch(`/safras/${safraId}/production-units/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-units", safraId] });
      toast.success("Unidade atualizada.");
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const encerrarMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/safras/${safraId}/production-units/${id}/encerrar`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-units", safraId] });
      toast.success("Unidade encerrada.");
      setEncerrandoId(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ---- Columns ----
  const columns: ColumnDef<ProductionUnit>[] = [
    {
      id: "cultivo",
      header: "Cultivo",
      cell: (_, row) => row.cultivo_nome ?? row.cultivo_id.slice(0, 8),
    },
    {
      id: "area",
      header: "Área",
      cell: (_, row) => row.area_nome ?? row.area_id.slice(0, 8),
    },
    {
      id: "area_ha",
      header: "Área (ha)",
      cell: (_, row) =>
        Number(row.area_ha).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 }),
    },
    {
      id: "percentual",
      header: "Participação",
      cell: (_, row) =>
        `${Number(row.percentual_participacao).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}%`,
    },
    {
      id: "status",
      header: "Status",
      cell: (_, row) => (
        <Badge variant={row.status === "ATIVA" ? "default" : "secondary"}>
          {row.status}
        </Badge>
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
            aria-label="Ver cenários"
            asChild
          >
            <Link href={`/agricola/safras/${safraId}/cenarios`}>
              <BarChart2 className="size-3.5" />
            </Link>
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            aria-label="Editar"
            onClick={() => setEditing(row)}
          >
            <Pencil className="size-3.5" />
          </Button>
          {row.status === "ATIVA" && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive"
              aria-label="Encerrar"
              onClick={() => setEncerrandoId(row.id)}
            >
              <Power className="size-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  // ---- Summary ----
  const totalHa = units.reduce((s, u) => s + Number(u.area_ha), 0);
  const ativas = units.filter((u) => u.status === "ATIVA").length;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={`Unidades Operacionais — ${safraLabel}`}
        icon={<Layers className="text-cyan-600" size={22} />}
        description={`Centro operacional e econômico de ${safraLabel} por cultivo × área`}
        actions={(
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="size-4 mr-1" />
            Nova Unidade Operacional
          </Button>
        )}
      />

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Total de unidades operacionais</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{units.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Unidades operacionais ativas</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{ativas}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Área total (ha)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {totalHa.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabela */}
      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : isError ? (
        <Card className="border-destructive/20 bg-destructive/5">
          <CardContent className="flex flex-col items-start gap-2 py-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-4 text-destructive" />
              <p className="font-medium text-destructive">Não foi possível carregar as unidades operacionais.</p>
            </div>
            <p className="text-sm text-muted-foreground">
              {error instanceof Error ? error.message : "Verifique a permissão do módulo ou a conexão com a API."}
            </p>
          </CardContent>
        </Card>
      ) : units.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
            <AlertCircle className="size-8" />
            <p className="text-sm">Nenhuma unidade operacional cadastrada.</p>
            <p className="text-xs">
              Crie ao menos uma unidade operacional para poder gerar cenários econômicos.
            </p>
            <Button size="sm" variant="outline" onClick={() => setShowCreate(true)}>
              <Plus className="size-4 mr-1" /> Criar agora
            </Button>
          </CardContent>
        </Card>
      ) : units.length > 0 ? (
        <DataTable columns={columns} data={units} />
      ) : null}

      {/* Dialog — Criar */}
      <CreateDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        cultivos={cultivos}
        safraId={safraId}
        areaIdsJaUsados={areaIdsJaUsados}
        unidadesProdutivas={unidadesProdutivas}
        onSubmit={(data) => createMut.mutate(data)}
        loading={createMut.isPending}
      />

      {/* Dialog — Editar */}
      {editing && (
        <EditDialog
          open={!!editing}
          onClose={() => setEditing(null)}
          unit={editing}
          onSubmit={(data) => updateMut.mutate({ id: editing.id, data })}
          loading={updateMut.isPending}
        />
      )}

      {/* Confirmar encerramento */}
      <AlertDialog open={!!encerrandoId} onOpenChange={(o) => !o && setEncerrandoId(null)}>
          <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Encerrar unidade operacional?</AlertDialogTitle>
            <AlertDialogDescription>
              A unidade operacional será marcada como ENCERRADA e não aparecerá em novos cenários.
              Cenários existentes não serão afetados.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => encerrandoId && encerrarMut.mutate(encerrandoId)}
            >
              Encerrar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CreateDialog
// ---------------------------------------------------------------------------

function CreateDialog({
  open,
  onClose,
  cultivos,
  safraId,
  areaIdsJaUsados,
  unidadesProdutivas,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  cultivos: Cultivo[];
  safraId: string;
  areaIdsJaUsados: Set<string>;
  unidadesProdutivas: UnidadeProdutiva[];
  onSubmit: (data: PUFormData & { cultivo_area_id?: string | null }) => void;
  loading: boolean;
}) {
  const form = useForm<PUFormInput, unknown, PUFormData>({
    resolver: zodResolver(puSchema),
    defaultValues: { percentual_participacao: 100, cultivo_area_id: null },
  });

  const selectedCultivoId = form.watch("cultivo_id");
  const selectedCultivo = cultivos.find((cultivo) => cultivo.id === selectedCultivoId);
  const { data: todasAreas = [] } = useQuery<AreaRural[]>({
    queryKey: ["areas-rurais-talhoes-production-units"],
    queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
  });
  const areaOptions = todasAreas
    .map((area) => {
      if (areaIdsJaUsados.has(area.id)) {
        return null;
      }
      const up = unidadesProdutivas.find((u) => u.id === area.unidade_produtiva_id);
      const cultivoArea = selectedCultivo?.areas.find((item) => item.area_id === area.id);
      return {
        areaId: area.id,
        nome: area.nome,
        codigo: area.codigo,
        unidadeProdutivaNome: up?.nome ?? "UP",
        areaHectares: area.area_hectares ?? area.area_hectares_manual,
        cultivoAreaId: cultivoArea?.id ?? null,
      };
    })
    .filter(Boolean) as {
    areaId: string;
    nome: string;
    codigo: string | null;
    unidadeProdutivaNome: string;
    areaHectares: number | null;
    cultivoAreaId: string | null;
  }[];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[720px] p-0 gap-0 overflow-hidden">
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="flex items-center gap-2">
            <Layers />
            Nova Unidade Operacional
          </DialogTitle>
          <div className="text-sm text-muted-foreground">
            Vincule um cultivo a uma área e defina a unidade operacional desta safra.
          </div>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              onSubmit({
                ...data,
                cultivo_area_id: form.getValues("cultivo_area_id") ?? null,
              }),
            )}
            className="flex max-h-[85vh] min-h-0 flex-col"
          >
            <ScrollArea className="min-h-0 flex-1">
              <DialogBody className="px-6 py-5">
                <div className="flex flex-col gap-5">
                  <section className="rounded-sm border bg-muted/30 p-4">
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-foreground">Vinculação da unidade</h3>
                      <p className="text-xs text-muted-foreground">
                        Primeiro escolha o cultivo e a área que serão associados a esta unidade operacional.
                      </p>
                    </div>

                    <div className="flex flex-col gap-4">
                      <FormField
                        control={form.control}
                        name="cultivo_id"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Cultivo *</FormLabel>
                            <Select
                              onValueChange={(value) => {
                                field.onChange(value);
                                form.setValue("area_id", "");
                                form.setValue("cultivo_area_id", null);
                              }}
                              value={field.value}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Selecione o cultivo" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {cultivos.map((c) => (
                                  <SelectItem key={c.id} value={c.id}>
                                    {c.cultura}{c.cultivar_nome ? ` — ${c.cultivar_nome}` : ""}
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
                        name="area_id"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Área *</FormLabel>
                            <Select
                              onValueChange={(value) => {
                                const selectedArea = areaOptions.find((a) => a.areaId === value);
                                field.onChange(value);
                                form.setValue("cultivo_area_id", selectedArea?.cultivoAreaId ?? null);
                              }}
                              value={field.value}
                              disabled={!selectedCultivoId}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue
                                    placeholder={
                                      selectedCultivoId
                                        ? "Selecione a área"
                                        : "Selecione um cultivo primeiro"
                                    }
                                  />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {!selectedCultivoId ? (
                                  <SelectItem value="__empty" disabled>
                                    Selecione um cultivo primeiro
                                  </SelectItem>
                                ) : areaOptions.length === 0 ? (
                                  <SelectItem value="__empty" disabled>
                                    Nenhum talhão disponível
                                  </SelectItem>
                                ) : (
                                  areaOptions.map((a) => (
                                    <SelectItem key={a.areaId} value={a.areaId}>
                                      {a.unidadeProdutivaNome} · {a.nome}
                                      {a.codigo ? ` (${a.codigo})` : ""}
                                      {a.areaHectares != null
                                        ? ` · ${Number(a.areaHectares).toLocaleString("pt-BR", {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 4,
                                          })} ha`
                                        : ""}
                                    </SelectItem>
                                  ))
                                )}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                            {selectedCultivoId && areaOptions.length > 0 && (
                              <p className="text-xs text-muted-foreground">
                                Talhões já vinculados à safra são ocultados automaticamente para evitar duplicidade.
                              </p>
                            )}
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="cultivo_area_id"
                        render={({ field }) => (
                          <input
                            type="hidden"
                            name={field.name}
                            value={field.value ?? ""}
                            onChange={field.onChange}
                            onBlur={field.onBlur}
                            ref={field.ref}
                          />
                        )}
                      />
                    </div>
                  </section>

                  <section className="rounded-sm border bg-muted/30 p-4">
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-foreground">Dimensões e período</h3>
                      <p className="text-xs text-muted-foreground">
                        Informe a área da unidade, a participação no arranjo e o intervalo de vigência.
                      </p>
                    </div>

                    <div className="flex flex-col gap-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <FormField
                          control={form.control}
                          name="area_ha"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Área (ha) *</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  step="0.0001"
                                  placeholder="0,0000"
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
                          name="percentual_participacao"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Participação (%)</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  step="0.01"
                                  min={0}
                                  max={100}
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

                      <div className="grid gap-4 sm:grid-cols-2">
                        <FormField
                          control={form.control}
                          name="data_inicio"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Data início</FormLabel>
                              <FormControl>
                                <Input
                                  type="date"
                                  value={typeof field.value === "string" ? field.value : ""}
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
                          name="data_fim"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Data fim</FormLabel>
                              <FormControl>
                                <Input
                                  type="date"
                                  value={typeof field.value === "string" ? field.value : ""}
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
                    </div>
                  </section>
                </div>
              </DialogBody>
            </ScrollArea>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Salvando..." : "Criar unidade operacional"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// EditDialog
// ---------------------------------------------------------------------------

function EditDialog({
  open,
  onClose,
  unit,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  unit: ProductionUnit;
  onSubmit: (data: UpdateFormData) => void;
  loading: boolean;
}) {
  const form = useForm<UpdateFormInput, unknown, UpdateFormData>({
    resolver: zodResolver(updateSchema),
    defaultValues: {
      percentual_participacao: Number(unit.percentual_participacao),
      area_ha: Number(unit.area_ha),
      data_inicio: unit.data_inicio ?? "",
      data_fim: unit.data_fim ?? "",
    },
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[620px] p-0 gap-0 overflow-hidden">
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="flex items-center gap-2">
            <Pencil />
            Editar unidade operacional
          </DialogTitle>
          <div className="text-sm text-muted-foreground">
            {unit.cultivo_nome ?? "Unidade"} · {unit.area_nome ?? "Área"}
          </div>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex max-h-[85vh] min-h-0 flex-col">
            <div className="min-h-0 flex-1 overflow-auto">
              <DialogBody className="px-6 py-5">
                <div className="flex flex-col gap-5">
                  <section className="rounded-sm border bg-muted/30 p-4">
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-foreground">Ajustes da unidade</h3>
                      <p className="text-xs text-muted-foreground">
                        Atualize os parâmetros operacionais desta unidade na safra.
                      </p>
                    </div>

                    <div className="flex flex-col gap-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <FormField
                          control={form.control}
                          name="area_ha"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Área (ha)</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  step="0.0001"
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
                          name="percentual_participacao"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Participação (%)</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  step="0.01"
                                  min={0}
                                  max={100}
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

                      <div className="grid gap-4 sm:grid-cols-2">
                        <FormField
                          control={form.control}
                          name="data_inicio"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Data início</FormLabel>
                              <FormControl>
                                <Input
                                  type="date"
                                  value={typeof field.value === "string" ? field.value : ""}
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
                          name="data_fim"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Data fim</FormLabel>
                              <FormControl>
                                <Input
                                  type="date"
                                  value={typeof field.value === "string" ? field.value : ""}
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
                    </div>
                  </section>
                </div>
              </DialogBody>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Salvando..." : "Salvar unidade operacional"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
