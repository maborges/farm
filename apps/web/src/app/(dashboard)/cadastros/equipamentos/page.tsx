"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { Tractor, Plus, Pencil, PowerOff, FileText, Loader2, Power } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import { XCircle, Save, CheckCircle2 } from "lucide-react";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const TIPOS = [
  { value: "TRATOR",      label: "Trator" },
  { value: "COLHEDORA",   label: "Colhedora" },
  { value: "VEICULO",     label: "Veículo" },
  { value: "IMPLEMENTO",  label: "Implemento" },
  { value: "PULVERIZADOR",label: "Pulverizador" },
  { value: "IRRIGACAO",   label: "Sistema de Irrigação" },
  { value: "OUTRO",       label: "Outros" },
];

const TIPO_COLOR: Record<string, string> = {
  TRATOR:        "bg-lime-100 text-lime-700",
  COLHEDORA:     "bg-amber-100 text-amber-700",
  VEICULO:       "bg-blue-100 text-blue-700",
  IMPLEMENTO:    "bg-slate-100 text-slate-700",
  PULVERIZADOR:  "bg-teal-100 text-teal-700",
  IRRIGACAO:     "bg-cyan-100 text-cyan-700",
  OUTRO:         "bg-gray-100 text-gray-600",
};

const CATEGORIAS_PATRIMONIAIS = [
  { value: "ATIVO_DEPRECIAVEL",      label: "Ativo patrimonial depreciável" },
  { value: "FERRAMENTA_BAIXO_VALOR", label: "Ferramenta de baixo valor" },
];

const COMBUSTIVEIS = [
  { value: "DIESEL",        label: "Diesel" },
  { value: "GASOLINA",      label: "Gasolina" },
  { value: "ETANOL",        label: "Etanol" },
  { value: "FLEX",          label: "Flex" },
  { value: "ELETRICO",      label: "Elétrico" },
  { value: "NAO_APLICAVEL", label: "N/A (sem motor)" },
];

// ─────────────────────────────────────────────────────────────────────────────
// Schema de Validação
// ─────────────────────────────────────────────────────────────────────────────

const equipamentoSchema = z.object({
  ativo: z.boolean(),
  tipo: z.string().min(1, "Tipo é obrigatório"),
  categoria_patrimonial: z.string().min(1, "Categoria patrimonial é obrigatória"),
  nome: z.string().min(2, "Mínimo 2 caracteres").max(200),
  marca: z.string().optional(),
  modelo: z.string().optional(),
  ano_fabricacao: z.coerce.number().optional(),
  ano_modelo: z.coerce.number().optional(),
  placa: z.string().optional(),
  chassi: z.string().optional(),
  numero_serie: z.string().optional(),
  patrimonio: z.string().optional(),
  potencia_cv: z.coerce.number().optional(),
  capacidade_tanque_l: z.coerce.number().optional(),
  combustivel: z.string().min(1, "Combustível é obrigatório"),
});

type EquipamentoFormValues = z.infer<typeof equipamentoSchema>;

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface Equipamento {
  id: string;
  tipo: string;
  nome: string;
  marca?: string;
  modelo?: string;
  ano_fabricacao?: number;
  ano_modelo?: number;
  numero_serie?: string;
  placa?: string;
  patrimonio?: string;
  combustivel?: string;
  potencia_cv?: number;
  capacidade_tanque_l?: number;
  status: string;
  categoria_patrimonial?: string;
}

interface EquipamentoAPI extends Equipamento {
  created_at?: string;
  updated_at?: string;
  unidade_produtiva_id?: string;
  status: string;
  chassi?: string;
  observacoes?: string;
  dados_extras?: Record<string, unknown>;
}

interface EquipamentoCreatePayload {
  unidade_produtiva_id: string | null;
  ativo?: boolean;
  tipo: string;
  categoria_patrimonial: string;
  nome: string;
  marca?: string;
  modelo?: string;
  combustivel: string;
  ano_fabricacao?: number;
  ano_modelo?: number;
  placa?: string;
  chassi?: string;
  numero_serie?: string;
  patrimonio?: string;
  potencia_cv?: number;
  capacidade_tanque_l?: number;
  status?: string;
}

const EMPTY_FORM: EquipamentoFormValues = {
  ativo: true,
  tipo: "TRATOR",
  categoria_patrimonial: "ATIVO_DEPRECIAVEL",
  nome: "",
  marca: "",
  modelo: "",
  ano_fabricacao: undefined,
  ano_modelo: undefined,
  placa: "",
  chassi: "",
  numero_serie: "",
  patrimonio: "",
  potencia_cv: undefined,
  capacidade_tanque_l: undefined,
  combustivel: "DIESEL",
};

export default function EquipamentosPage() {
  const { activeFazendaId } = useAppStore();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [tipoFilter, setTipoFilter] = useState("all");

  // React Hook Form setup
  const form = useForm<EquipamentoFormValues>({
    resolver: zodResolver(equipamentoSchema) as Resolver<EquipamentoFormValues>,
    defaultValues: EMPTY_FORM,
  });

  const resetForm = () => {
    form.reset(EMPTY_FORM);
    setEditId(null);
  };

  const { data: equipamentos = [], isLoading } = useQuery<Equipamento[]>({
    queryKey: ["equipamentos", activeFazendaId],
    queryFn: () => apiFetch<Equipamento[]>(`/cadastros/equipamentos/?${new URLSearchParams(activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : {}).toString()}`),
    enabled: !!activeFazendaId,
  });

  const createMutation = useMutation({
    mutationFn: (data: EquipamentoCreatePayload) =>
      apiFetch("/cadastros/equipamentos/", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["equipamentos", activeFazendaId] });
      toast.success("Equipamento cadastrado com sucesso");
      setOpen(false);
      resetForm();
    },
    onError: () => toast.error("Erro ao cadastrar equipamento"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EquipamentoCreatePayload }) =>
      apiFetch(`/cadastros/equipamentos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["equipamentos", activeFazendaId] });
      toast.success("Equipamento atualizado");
      setOpen(false);
      resetForm();
    },
    onError: () => toast.error("Erro ao atualizar equipamento"),
  });

  const toggleAtivoMutation = useMutation({
    mutationFn: ({ id, ativo }: { id: string; ativo: boolean }) =>
      apiFetch(`/cadastros/equipamentos/${id}`, { method: "PATCH", body: JSON.stringify({ status: ativo ? "ATIVO" : "INATIVO" }) }),
    onSuccess: (_, { ativo }) => {
      queryClient.invalidateQueries({ queryKey: ["equipamentos", activeFazendaId] });
      toast.success(ativo ? "Equipamento ativado" : "Equipamento desativado");
    },
    onError: () => toast.error("Erro ao alterar status do equipamento"),
  });

  const openEditar = (e: EquipamentoAPI) => {
    setEditId(e.id);
    form.reset({
      ativo: e.status !== "INATIVO",
      tipo: e.tipo ?? "TRATOR",
      categoria_patrimonial: e.categoria_patrimonial ?? "ATIVO_DEPRECIAVEL",
      nome: e.nome ?? "",
      marca: e.marca ?? "",
      modelo: e.modelo ?? "",
      ano_fabricacao: e.ano_fabricacao ?? 0,
      ano_modelo: e.ano_modelo ?? 0,
      placa: e.placa ?? "",
      chassi: e.chassi ?? "",
      numero_serie: e.numero_serie ?? "",
      patrimonio: e.patrimonio ?? "",
      potencia_cv: e.potencia_cv ?? 0,
      capacidade_tanque_l: e.capacidade_tanque_l ?? 0,
      combustivel: e.combustivel ?? "DIESEL",
    });
    setOpen(true);
  };

  const handleSave = (data: EquipamentoFormValues) => {
    const payload: EquipamentoCreatePayload = {
      unidade_produtiva_id: activeFazendaId,
      status: data.ativo ? "ATIVO" : "INATIVO",
      tipo: data.tipo,
      categoria_patrimonial: data.categoria_patrimonial,
      nome: data.nome.trim(),
      marca: data.marca || undefined,
      modelo: data.modelo || undefined,
      combustivel: data.combustivel,
      ano_fabricacao: data.ano_fabricacao || undefined,
      ano_modelo: data.ano_modelo || undefined,
      placa: data.placa || undefined,
      chassi: data.chassi || undefined,
      numero_serie: data.numero_serie || undefined,
      patrimonio: data.patrimonio || undefined,
      potencia_cv: data.potencia_cv || undefined,
      capacidade_tanque_l: data.capacidade_tanque_l || undefined,
    };
    if (editId) {
      updateMutation.mutate({ id: editId, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleNovoEquipamento = () => {
    setEditId(null);
    form.reset(EMPTY_FORM);
    setOpen(true);
  };
  const tipoFilterLabel = tipoFilter === "all"
    ? "Todos os tipos"
    : TIPOS.find((t) => t.value === tipoFilter)?.label ?? tipoFilter;

  const columns: ColumnDef<EquipamentoAPI>[] = [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value) => <span className="font-medium">{value}</span>,
    },
    {
      id: "tipo",
      header: "Tipo",
      accessorKey: "tipo",
      cell: (value) => (
        <Badge variant="outline" className={cn("text-xs", TIPO_COLOR[value] ?? TIPO_COLOR.OUTRO)}>
          {TIPOS.find((t) => t.value === value)?.label ?? value}
        </Badge>
      ),
      exportFormat: (value) => TIPOS.find((t) => t.value === value)?.label ?? value,
    },
    {
      id: "marca_modelo",
      header: "Marca / Modelo",
      accessorFn: (row) => [row.marca, row.modelo].filter(Boolean).join(" / ") || "—",
      cell: (value) => <span className="text-muted-foreground truncate">{value}</span>,
    },
    {
      id: "ano",
      header: "Ano",
      accessorKey: "ano_fabricacao",
      cell: (value) => <span className="text-muted-foreground">{value ?? "—"}</span>,
    },
    {
      id: "placa_patrimonio",
      header: "Placa / Patrimônio",
      accessorFn: (row) => row.placa ?? row.patrimonio ?? row.numero_serie ?? "—",
      cell: (value) => <span className="text-muted-foreground text-xs">{value}</span>,
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: (value) => (
        <StatusBadge status={value === "ATIVO" ? "ativo" : "inativo"} />
      ),
      exportFormat: (value) => (value === "ATIVO" ? "Ativo" : "Inativo"),
    },
    {
      id: "acoes",
      header: "",
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={`Editar ${row.nome}`}
            title="Editar"
            onClick={() => openEditar(row)}
          >
            <Pencil />
          </Button>
          <Button
            asChild
            size="icon-sm"
            variant="ghost"
            aria-label={`Documentos de ${row.nome}`}
            title="Documentos"
          >
            <Link href={`/cadastros/equipamentos/${row.id}/documentos`}>
              <FileText />
            </Link>
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={row.status === "ATIVO" ? `Desativar ${row.nome}` : `Ativar ${row.nome}`}
            title={row.status === "ATIVO" ? "Desativar" : "Ativar"}
            onClick={() => toggleAtivoMutation.mutate({ id: row.id, ativo: row.status !== "ATIVO" })}
            disabled={toggleAtivoMutation.isPending}
            className={row.status === "ATIVO" ? "text-destructive hover:text-destructive" : "text-emerald-600 hover:text-emerald-600"}
          >
            {row.status === "ATIVO" ? <PowerOff /> : <Power />}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Equipamentos & Frota"
        description="Tratores, colhedoras, veículos e implementos — cadastro unificado para manutenção e operações."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Cadastros", href: "/cadastros" }, { label: "Equipamentos & Frota" }]}
        actions={
          <Button size="sm" variant="outline" className="rounded-sm border-primary/50 text-primary hover:bg-primary/5" onClick={handleNovoEquipamento}>
            <Plus className="size-4 mr-2" />
            Novo Equipamento
          </Button>
        }
      />

      {/* Filtro de Tipo */}
      <div className="flex gap-3">
        <Select value={tipoFilter} onValueChange={setTipoFilter}>
          <SelectTrigger className="w-44 h-8 rounded-sm text-xs">
            <span className="truncate">{tipoFilterLabel}</span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os tipos</SelectItem>
            {TIPOS.map((t) => (
              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Carregando...</div>
      ) : (
        <DataTable
          data={equipamentos.filter((e) => tipoFilter === "all" || e.tipo === tipoFilter)}
          columns={columns}
          searchPlaceholder="Buscar por nome, marca ou modelo..."
          exportFileName="equipamentos-frota"
          emptyMessage="Nenhum equipamento cadastrado"
        />
      )}

      {/* Dialog — Novo/Editar Equipamento */}
      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-6xl gap-0 overflow-y-auto p-0 lg:overflow-hidden">
          <DialogHeader className="border-b px-4 py-3 pr-12 sm:px-6">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Tractor className="size-4 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5">
                <DialogTitle>{editId ? "Editar Equipamento" : "Novo Equipamento"}</DialogTitle>
                <DialogDescription>
                  Dados cadastrais, técnicos e de identificação. Documentos regulatórios são gerenciados em Frota › Documentos.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSave)} className="flex flex-col lg:max-h-none">
              <DialogBody className="overflow-y-auto px-4 py-3 sm:px-6 lg:overflow-visible">
                <div className="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2 lg:grid-cols-4">
                  <p className="col-span-full text-xs font-semibold uppercase tracking-wide text-muted-foreground">Identificação</p>
                  <FormField
                    control={form.control}
                    name="nome"
                    render={({ field }) => (
                      <FormItem className="min-w-0 sm:col-span-2">
                        <FormLabel>Nome / Descrição *</FormLabel>
                        <FormControl>
                          <Input {...field} className="h-8 rounded-sm text-xs" placeholder="Ex: Trator John Deere 8R 310 — Frota 03" disabled={createMutation.isPending || updateMutation.isPending} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField control={form.control} name="tipo" render={({ field }) => (
                    <FormItem className="min-w-0">
                      <FormLabel>Tipo *</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value} disabled={createMutation.isPending || updateMutation.isPending}>
                        <FormControl><SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger></FormControl>
                        <SelectContent><SelectGroup>{TIPOS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectGroup></SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="categoria_patrimonial" render={({ field }) => (
                    <FormItem className="min-w-0">
                      <FormLabel>Categoria patrimonial *</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value} disabled={createMutation.isPending || updateMutation.isPending}>
                        <FormControl><SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger></FormControl>
                        <SelectContent><SelectGroup>{CATEGORIAS_PATRIMONIAIS.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectGroup></SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="combustivel" render={({ field }) => (
                    <FormItem className="min-w-0">
                      <FormLabel>Combustível</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value} disabled={createMutation.isPending || updateMutation.isPending}>
                        <FormControl><SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger></FormControl>
                        <SelectContent><SelectGroup>{COMBUSTIVEIS.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectGroup></SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />

                  <p className="col-span-full mt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Especificações técnicas</p>
                  <FormField control={form.control} name="marca" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Marca</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="John Deere" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="modelo" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Modelo</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="8R 310" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="potencia_cv" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Potência (cv)</FormLabel><FormControl><Input type="number" min="0" {...field} className="h-8 rounded-sm text-xs" placeholder="310" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="capacidade_tanque_l" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Cap. tanque (L)</FormLabel><FormControl><Input type="number" min="0" {...field} className="h-8 rounded-sm text-xs" placeholder="1135" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />

                  <p className="col-span-full mt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Documentação e identificação</p>
                  <FormField control={form.control} name="ano_fabricacao" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Ano fabricação</FormLabel><FormControl><Input type="number" min="1900" max={new Date().getFullYear() + 1} {...field} className="h-8 rounded-sm text-xs" placeholder="2023" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="ano_modelo" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Ano modelo</FormLabel><FormControl><Input type="number" min="1900" max={new Date().getFullYear() + 1} {...field} className="h-8 rounded-sm text-xs" placeholder="2024" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="placa" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Placa</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="ABC-1D23" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="patrimonio" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Patrimônio</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="TR-001" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="chassi" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Chassi / VIN</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="9BWM..." disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="numero_serie" render={({ field }) => (
                    <FormItem className="min-w-0"><FormLabel>Número de série</FormLabel><FormControl><Input {...field} className="h-8 rounded-sm text-xs" placeholder="SN00123456" disabled={createMutation.isPending || updateMutation.isPending} /></FormControl><FormMessage /></FormItem>
                  )} />
                </div>
              </DialogBody>
 
              <DialogFooter className="shrink-0 px-4 sm:px-6">
                <FormField
                  control={form.control}
                  name="ativo"
                  render={({ field }) => (
                    <div className="flex items-center gap-2 mr-auto">
                      <Switch checked={field.value} onCheckedChange={field.onChange} disabled={createMutation.isPending || updateMutation.isPending} />
                      <span className="text-xs text-muted-foreground font-medium">Ativo</span>
                    </div>
                  )}
                />
                <Button type="button" variant="outline" size="sm" className="rounded-sm"
                  onClick={() => { setOpen(false); resetForm(); }}
                  disabled={createMutation.isPending || updateMutation.isPending}>
                  <XCircle className="size-3.5 mr-1.5" /> Cancelar
                </Button>
                <Button type="submit" size="sm" className="rounded-sm"
                  disabled={createMutation.isPending || updateMutation.isPending}>
                  {(createMutation.isPending || updateMutation.isPending)
                    ? <Loader2 className="mr-2 size-3.5 animate-spin" />
                    : <Save className="size-3.5 mr-1.5" />}
                  {createMutation.isPending || updateMutation.isPending ? "Salvando..." : editId ? "Salvar Alterações" : "Cadastrar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
