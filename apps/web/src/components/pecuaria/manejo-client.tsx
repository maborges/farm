"use client";

import { useMemo, useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  Activity,
  CalendarDays,
  ClipboardList,
  DollarSign,
  Loader2,
  Plus,
  RefreshCcw,
  Scale,
  Syringe,
  Users,
} from "lucide-react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod/v4";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

import { apiFetch } from "@/lib/api";
import { fetchLotes, type LoteBovino } from "@/lib/pecuaria/lotes-api";
import { useAppStore } from "@/lib/stores/app-store";
import { formatCurrency } from "@/lib/utils";

const TIPOS_EVENTO = [
  "PESAGEM",
  "VACINACAO",
  "MEDICACAO",
  "NASCIMENTO",
  "COMPRA",
  "MORTE",
  "TRANSFERENCIA",
  "VENDA",
  "ABATE",
  "CASTRACAO",
] as const;

export type TipoEvento = (typeof TIPOS_EVENTO)[number];

export interface ManejoLote {
  id: string;
  lote_id: string;
  tipo_evento: TipoEvento;
  data_evento: string;
  quantidade_cabecas?: number | null;
  peso_total_kg?: number | null;
  custo_total?: number | null;
  valor_venda?: number | null;
  observacoes?: string | null;
  created_at?: string | null;
}

const EVENTO_META: Record<TipoEvento, { label: string; badgeClass: string }> = {
  NASCIMENTO: {
    label: "Nascimento",
    badgeClass:
      "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  },
  COMPRA: {
    label: "Compra",
    badgeClass:
      "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-300",
  },
  MORTE: {
    label: "Morte / Baixa",
    badgeClass:
      "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300",
  },
  PESAGEM: {
    label: "Pesagem",
    badgeClass:
      "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  },
  VACINACAO: {
    label: "Vacinação",
    badgeClass:
      "border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300",
  },
  MEDICACAO: {
    label: "Medicação",
    badgeClass:
      "border-teal-200 bg-teal-50 text-teal-700 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300",
  },
  TRANSFERENCIA: {
    label: "Transferência",
    badgeClass:
      "border-stone-200 bg-stone-50 text-stone-700 dark:border-stone-700 dark:bg-stone-900/40 dark:text-stone-300",
  },
  VENDA: {
    label: "Venda",
    badgeClass:
      "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300",
  },
  ABATE: {
    label: "Abate",
    badgeClass:
      "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950/40 dark:text-orange-300",
  },
  CASTRACAO: {
    label: "Castração",
    badgeClass:
      "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300",
  },
};

function isOptionalNonNegativeNumber(raw: string): boolean {
  if (!raw.trim()) return true;
  const parsed = Number(raw.replace(",", "."));
  return Number.isFinite(parsed) && parsed >= 0;
}

function isOptionalPositiveInteger(raw: string): boolean {
  if (!raw.trim()) return true;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed >= 1;
}

const manejoFormSchema = z.object({
  lote_id: z.string().min(1, "Selecione um lote"),
  tipo_evento: z.enum(TIPOS_EVENTO),
  data_evento: z.string().min(1, "Informe a data do evento"),
  quantidade_cabecas: z
    .string()
    .refine(isOptionalPositiveInteger, "Informe um número inteiro positivo"),
  peso_total_kg: z
    .string()
    .refine(isOptionalNonNegativeNumber, "Peso inválido"),
  custo_total: z
    .string()
    .refine(isOptionalNonNegativeNumber, "Custo inválido"),
  valor_venda: z
    .string()
    .refine(isOptionalNonNegativeNumber, "Valor de venda inválido"),
  observacoes: z.string().max(1000, "Máximo de 1000 caracteres"),
});

type ManejoFormValues = z.infer<typeof manejoFormSchema>;

function parseOptionalFloat(raw: string): number | undefined {
  if (!raw.trim()) return undefined;
  const parsed = Number(raw.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseOptionalInt(raw: string): number | undefined {
  if (!raw.trim()) return undefined;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function formatDateBr(value: string | null | undefined): string {
  if (!value) return "—";
  const datePart = value.slice(0, 10);
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(datePart)
    ? new Date(`${datePart}T12:00:00`)
    : new Date(value);
  if (Number.isNaN(normalized.getTime())) return value;
  return format(normalized, "dd/MM/yyyy");
}

function todayIsoDate(): string {
  return format(new Date(), "yyyy-MM-dd");
}

function getDefaultFormValues(): ManejoFormValues {
  return {
    lote_id: "",
    tipo_evento: "PESAGEM",
    data_evento: todayIsoDate(),
    quantidade_cabecas: "",
    peso_total_kg: "",
    custo_total: "",
    valor_venda: "",
    observacoes: "",
  };
}

export function ManejoClient() {
  const queryClient = useQueryClient();
  const activeFazendaId = useAppStore((s) => s.activeFazendaId);
  const isVisaoGrupo = useAppStore((s) => s.isVisaoGrupo);
  const hasHydrated = useAppStore((s) => s._hasHydrated);

  const [tipoFiltro, setTipoFiltro] = useState<string>("TODOS");
  const [modalOpen, setModalOpen] = useState(false);

  const fazendaFilter = isVisaoGrupo ? null : activeFazendaId;

  const {
    data: lotes = [],
    isLoading: loadingLotes,
  } = useQuery<LoteBovino[]>({
    queryKey: ["pecuaria-lotes", fazendaFilter],
    queryFn: () => fetchLotes(fazendaFilter),
    enabled: hasHydrated,
  });

  const {
    data: manejos = [],
    isLoading: loadingManejos,
    isFetching: fetchingManejos,
  } = useQuery<ManejoLote[]>({
    queryKey: ["pecuaria-manejos", fazendaFilter],
    queryFn: () => apiFetch<ManejoLote[]>("/pecuaria/manejos/"),
    enabled: hasHydrated,
  });

  const lotesMap = useMemo(() => {
    const map = new Map<string, LoteBovino>();
    for (const lote of lotes) {
      map.set(lote.id, lote);
    }
    return map;
  }, [lotes]);

  const manejosFiltrados = useMemo(() => {
    if (tipoFiltro === "TODOS") return manejos;
    return manejos.filter((m) => m.tipo_evento === tipoFiltro);
  }, [manejos, tipoFiltro]);

  const resumo = useMemo(() => {
    let custoAcumulado = 0;
    let receitaVendas = 0;
    let sanidadeEPesagem = 0;

    for (const item of manejos) {
      custoAcumulado += Number(item.custo_total ?? 0);
      receitaVendas += Number(item.valor_venda ?? 0);
      if (
        item.tipo_evento === "PESAGEM" ||
        item.tipo_evento === "VACINACAO" ||
        item.tipo_evento === "MEDICACAO"
      ) {
        sanidadeEPesagem += 1;
      }
    }

    return {
      totalEventos: manejos.length,
      sanidadeEPesagem,
      custoAcumulado,
      receitaVendas,
    };
  }, [manejos]);

  const form = useForm<ManejoFormValues>({
    resolver: zodResolver(manejoFormSchema),
    defaultValues: getDefaultFormValues(),
  });

  const selectedLoteId = useWatch({ control: form.control, name: "lote_id" });
  const selectedTipoEvento = useWatch({
    control: form.control,
    name: "tipo_evento",
  });

  const loteSelecionado = selectedLoteId
    ? lotesMap.get(selectedLoteId)
    : undefined;

  const criarManejoMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch<ManejoLote>("/pecuaria/manejos/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      toast.success("Evento de manejo registrado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["pecuaria-manejos"] });
      queryClient.invalidateQueries({ queryKey: ["pecuaria-lotes"] });
      queryClient.invalidateQueries({ queryKey: ["lote-indicadores"] });
      setModalOpen(false);
      form.reset(getDefaultFormValues());
    },
    onError: (err: unknown) => {
      toast.error(
        err instanceof Error ? err.message : "Erro ao registrar evento de manejo",
      );
    },
  });

  const handleOpenModal = () => {
    form.reset(getDefaultFormValues());
    setModalOpen(true);
  };

  const handleSubmitForm = form.handleSubmit((values) => {
    const payload: Record<string, unknown> = {
      lote_id: values.lote_id,
      tipo_evento: values.tipo_evento,
      data_evento: values.data_evento,
    };

    const qtd = parseOptionalInt(values.quantidade_cabecas);
    const peso = parseOptionalFloat(values.peso_total_kg);
    const custo = parseOptionalFloat(values.custo_total);
    const venda = parseOptionalFloat(values.valor_venda);
    const obs = values.observacoes.trim();

    if (qtd !== undefined) payload.quantidade_cabecas = qtd;
    if (peso !== undefined) payload.peso_total_kg = peso;
    if (custo !== undefined) payload.custo_total = custo;
    if (venda !== undefined) payload.valor_venda = venda;
    if (obs) payload.observacoes = obs;

    criarManejoMutation.mutate(payload);
  });

  const columns: ColumnDef<ManejoLote>[] = useMemo(
    () => [
      {
        id: "data_evento",
        header: "Data",
        accessorKey: "data_evento",
        sortable: true,
        filterable: false,
        cell: (_value, row) => (
          <div className="flex items-center gap-1.5 text-sm font-medium">
            <CalendarDays size={14} className="text-muted-foreground" />
            <span>{formatDateBr(row.data_evento)}</span>
          </div>
        ),
        exportFormat: (_value, row) => formatDateBr(row.data_evento),
      },
      {
        id: "tipo_evento",
        header: "Tipo de Evento",
        accessorKey: "tipo_evento",
        sortable: true,
        filterable: true,
        filterPlaceholder: "Filtrar evento...",
        cell: (_value, row) => {
          const meta = EVENTO_META[row.tipo_evento] ?? {
            label: row.tipo_evento,
            badgeClass: "",
          };
          return (
            <Badge
              variant="outline"
              className={`rounded-sm font-medium ${meta.badgeClass}`}
            >
              {meta.label}
            </Badge>
          );
        },
        exportFormat: (_value, row) =>
          EVENTO_META[row.tipo_evento]?.label ?? row.tipo_evento,
      },
      {
        id: "lote",
        header: "Lote",
        accessorFn: (row) =>
          lotesMap.get(row.lote_id)?.identificacao ?? row.lote_id,
        sortable: true,
        filterable: true,
        filterPlaceholder: "Filtrar lote...",
        cell: (_value, row) => {
          const lote = lotesMap.get(row.lote_id);
          if (!lote) {
            return (
              <span className="text-xs text-muted-foreground font-mono">
                {row.lote_id.slice(0, 8)}...
              </span>
            );
          }
          return (
            <div className="flex flex-col">
              <span className="font-medium text-foreground">
                {lote.identificacao}
              </span>
              <span className="text-xs text-muted-foreground">
                {lote.modo_gestao === "POR_LOTE" ? "Coletivo" : "Individual"} ·{" "}
                {lote.categoria}
              </span>
            </div>
          );
        },
      },
      {
        id: "quantidade_cabecas",
        header: "Cabeças",
        accessorKey: "quantidade_cabecas",
        sortable: true,
        filterable: false,
        cell: (_value, row) =>
          row.quantidade_cabecas != null ? (
            <span className="font-mono text-sm">
              {row.quantidade_cabecas} cab.
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
        exportFormat: (_value, row) =>
          row.quantidade_cabecas != null ? String(row.quantidade_cabecas) : "",
      },
      {
        id: "peso_total_kg",
        header: "Peso Total",
        accessorKey: "peso_total_kg",
        sortable: true,
        filterable: false,
        cell: (_value, row) =>
          row.peso_total_kg != null ? (
            <span className="font-mono text-sm">
              {Number(row.peso_total_kg).toLocaleString("pt-BR", {
                maximumFractionDigits: 2,
              })}{" "}
              kg
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
        exportFormat: (_value, row) =>
          row.peso_total_kg != null ? String(row.peso_total_kg) : "",
      },
      {
        id: "custo_total",
        header: "Custo",
        accessorKey: "custo_total",
        sortable: true,
        filterable: false,
        cell: (_value, row) =>
          row.custo_total != null && Number(row.custo_total) > 0 ? (
            <span className="font-mono text-sm text-amber-700 dark:text-amber-300">
              {formatCurrency(Number(row.custo_total))}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
        exportFormat: (_value, row) =>
          row.custo_total != null ? formatCurrency(Number(row.custo_total)) : "",
      },
      {
        id: "valor_venda",
        header: "Receita",
        accessorKey: "valor_venda",
        sortable: true,
        filterable: false,
        cell: (_value, row) =>
          row.valor_venda != null && Number(row.valor_venda) > 0 ? (
            <span className="font-mono text-sm text-emerald-700 dark:text-emerald-300">
              {formatCurrency(Number(row.valor_venda))}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
        exportFormat: (_value, row) =>
          row.valor_venda != null ? formatCurrency(Number(row.valor_venda)) : "",
      },
      {
        id: "observacoes",
        header: "Observações",
        accessorKey: "observacoes",
        sortable: false,
        filterable: true,
        filterPlaceholder: "Filtrar notas...",
        cell: (_value, row) => (
          <span
            className="block max-w-[260px] truncate text-xs text-muted-foreground"
            title={row.observacoes ?? undefined}
          >
            {row.observacoes || "—"}
          </span>
        ),
      },
    ],
    [lotesMap],
  );

  const isLoading = loadingManejos || loadingLotes;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Manejo do Rebanho"
        description="Registro e histórico de pesagens, vacinações, nascimentos, baixas e movimentações dos lotes"
        icon={<ClipboardList size={22} className="text-primary" />}
        breadcrumbs={[
          { label: "Pecuária", href: "/dashboard/pecuaria/rebanho" },
          { label: "Manejo" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ["pecuaria-manejos"] })
              }
              disabled={fetchingManejos}
            >
              <RefreshCcw
                size={14}
                className={fetchingManejos ? "animate-spin" : ""}
              />
              Atualizar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={handleOpenModal}
            >
              <Plus size={14} />
              Registrar Manejo
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5 text-xs">
              <Activity size={14} className="text-primary" />
              Total de Eventos
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {resumo.totalEventos}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5 text-xs">
              <Syringe size={14} className="text-indigo-600 dark:text-indigo-400" />
              Pesagens e Sanidade
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {resumo.sanidadeEPesagem}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5 text-xs">
              <Scale size={14} className="text-amber-600 dark:text-amber-400" />
              Custo Acumulado
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {formatCurrency(resumo.custoAcumulado)}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5 text-xs">
              <DollarSign size={14} className="text-emerald-600 dark:text-emerald-400" />
              Receita de Vendas
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {formatCurrency(resumo.receitaVendas)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base">Histórico de Manejos</CardTitle>
            <CardDescription>
              Pesquise, filtre por tipo de evento ou exporte para Excel/PDF
            </CardDescription>
          </div>
          <div className="w-full sm:w-56">
            <Select value={tipoFiltro} onValueChange={setTipoFiltro}>
              <SelectTrigger className="h-8 rounded-sm">
                <SelectValue placeholder="Filtrar tipo..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="TODOS">Todos os eventos</SelectItem>
                {TIPOS_EVENTO.map((tipo) => (
                  <SelectItem key={tipo} value={tipo}>
                    {EVENTO_META[tipo].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-9 w-full rounded-sm" />
              <Skeleton className="h-56 w-full rounded-sm" />
            </div>
          ) : (
            <DataTable
              data={manejosFiltrados}
              columns={columns}
              searchable={true}
              searchPlaceholder="Buscar por lote, evento ou observações..."
              exportable={true}
              exportFileName="manejos-pecuarios"
              emptyMessage="Nenhum evento de manejo encontrado."
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg rounded-sm">
          <form
            onSubmit={handleSubmitForm}
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <DialogHeader>
              <DialogTitle>Registrar Evento de Manejo</DialogTitle>
              <DialogDescription>
                Lance um evento diretamente para atualização do lote e indicadores
              </DialogDescription>
            </DialogHeader>

            <DialogBody className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="lote_id">Lote *</Label>
                <Controller
                  control={form.control}
                  name="lote_id"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={(value) => {
                        field.onChange(value);
                        const lote = lotesMap.get(value);
                        if (
                          lote &&
                          !form.getValues("quantidade_cabecas") &&
                          lote.quantidade_cabecas > 0
                        ) {
                          form.setValue(
                            "quantidade_cabecas",
                            String(lote.quantidade_cabecas),
                          );
                        }
                      }}
                    >
                      <SelectTrigger id="lote_id" className="h-8 rounded-sm">
                        <SelectValue placeholder="Selecione o lote..." />
                      </SelectTrigger>
                      <SelectContent>
                        {lotes.map((lote) => (
                          <SelectItem key={lote.id} value={lote.id}>
                            {lote.identificacao} ({lote.quantidade_cabecas} cab.)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {form.formState.errors.lote_id && (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.lote_id.message}
                  </p>
                )}
                {loteSelecionado && (
                  <div className="flex items-center gap-2 rounded-sm border border-border/60 bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground">
                    <Users size={13} className="text-primary" />
                    <span>
                      Gestão:{" "}
                      <strong>
                        {loteSelecionado.modo_gestao === "POR_LOTE"
                          ? "Por Lote (Coletivo)"
                          : "Individual"}
                      </strong>{" "}
                      · {loteSelecionado.quantidade_cabecas} cabeças ·{" "}
                      {loteSelecionado.categoria}
                    </span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="tipo_evento">Tipo de Evento *</Label>
                  <Controller
                    control={form.control}
                    name="tipo_evento"
                    render={({ field }) => (
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger
                          id="tipo_evento"
                          className="h-8 rounded-sm"
                        >
                          <SelectValue placeholder="Selecione o evento..." />
                        </SelectTrigger>
                        <SelectContent>
                          {TIPOS_EVENTO.map((tipo) => (
                            <SelectItem key={tipo} value={tipo}>
                              {EVENTO_META[tipo].label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="data_evento">Data do Evento *</Label>
                  <Input
                    id="data_evento"
                    type="date"
                    className="h-8 rounded-sm"
                    {...form.register("data_evento")}
                  />
                  {form.formState.errors.data_evento && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.data_evento.message}
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="quantidade_cabecas">
                    Quantidade (cabeças)
                  </Label>
                  <Input
                    id="quantidade_cabecas"
                    type="number"
                    min={1}
                    step={1}
                    placeholder="Ex: 50"
                    className="h-8 rounded-sm"
                    {...form.register("quantidade_cabecas")}
                  />
                  {form.formState.errors.quantidade_cabecas && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.quantidade_cabecas.message}
                    </p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="peso_total_kg">Peso Total (kg)</Label>
                  <Input
                    id="peso_total_kg"
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Ex: 16500"
                    className="h-8 rounded-sm"
                    {...form.register("peso_total_kg")}
                  />
                  {form.formState.errors.peso_total_kg && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.peso_total_kg.message}
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="custo_total">Custo Total (R$)</Label>
                  <Input
                    id="custo_total"
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="0,00"
                    className="h-8 rounded-sm"
                    {...form.register("custo_total")}
                  />
                  {form.formState.errors.custo_total && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.custo_total.message}
                    </p>
                  )}
                </div>

                {(selectedTipoEvento === "VENDA" ||
                  selectedTipoEvento === "ABATE") && (
                  <div className="space-y-1.5">
                    <Label htmlFor="valor_venda">Valor da Venda (R$)</Label>
                    <Input
                      id="valor_venda"
                      type="number"
                      min={0}
                      step="0.01"
                      placeholder="0,00"
                      className="h-8 rounded-sm"
                      {...form.register("valor_venda")}
                    />
                    {form.formState.errors.valor_venda && (
                      <p className="text-xs text-destructive">
                        {form.formState.errors.valor_venda.message}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="observacoes">Observações</Label>
                <Textarea
                  id="observacoes"
                  rows={3}
                  placeholder="Detalhes operacionais, protocolo sanitário, destino..."
                  className="rounded-sm"
                  {...form.register("observacoes")}
                />
                {form.formState.errors.observacoes && (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.observacoes.message}
                  </p>
                )}
              </div>
            </DialogBody>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="rounded-sm"
                onClick={() => setModalOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="outline"
                size="sm"
                className="rounded-sm"
                disabled={criarManejoMutation.isPending}
              >
                {criarManejoMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Plus size={14} />
                )}
                {criarManejoMutation.isPending
                  ? "Salvando..."
                  : "Salvar Manejo"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
