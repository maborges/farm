"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, ArrowLeft, Package, XCircle, Save } from "lucide-react";
import Link from "next/link";

const TIPOS = [
  { value: "AGRICOLA", label: "Agrícola" },
  { value: "PECUARIA", label: "Pecuária" },
  { value: "FLORESTAL", label: "Florestal" },
];

const UNIDADES = [
  { value: "SACA_60KG", label: "Saca (60 kg)" },
  { value: "TONELADA", label: "Tonelada (t)" },
  { value: "KG", label: "Quilograma (kg)" },
  { value: "ARROBA", label: "Arroba (@)" },
  { value: "CABECA", label: "Cabeça" },
  { value: "LITRO", label: "Litro (L)" },
  { value: "M3", label: "Metro Cúbico (m³)" },
  { value: "UNIDADE", label: "Unidade (un)" },
];

export interface Commodity {
  id: string;
  codigo: string;
  nome: string;
  tipo: string;
  unidade_padrao: string;
  peso_unidade: number | null;
  possui_cotacao: boolean;
  bolsa_referencia: string | null;
  codigo_bolsa: string | null;
  sistema: boolean;
  ativo: boolean;
}

type FormState = Partial<Commodity>;
const EMPTY: FormState = {
  codigo: "", nome: "", tipo: "AGRICOLA", unidade_padrao: "SACA_60KG",
  peso_unidade: null, possui_cotacao: false, bolsa_referencia: "", codigo_bolsa: "",
  sistema: true, ativo: true
};

export function CommoditiesClient({ initialData }: { initialData: Commodity[] }) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; item?: Commodity }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const { data = [] } = useQuery<Commodity[]>({
    queryKey: ["bo-tabelas-commodities"],
    queryFn: () => apiFetch("/backoffice/tabelas/commodities"),
    initialData: initialData,
  });

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const payload = {
        ...f,
        peso_unidade: f.peso_unidade ? Number(f.peso_unidade) : null,
      };

      return dialog.item
        ? apiFetch(`/backoffice/tabelas/commodities/${dialog.item.id}`, { method: "PATCH", body: JSON.stringify(payload) })
        : apiFetch("/backoffice/tabelas/commodities", { method: "POST", body: JSON.stringify(payload) })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-tabelas-commodities"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/commodities/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-tabelas-commodities"] }),
    onError: (e: any) => alert(e?.message ?? "Erro ao excluir"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: Commodity) { setForm(item); setDialog({ open: true, item }); }

  const columns: ColumnDef<Commodity>[] = [
    { id: "codigo", header: "Código", accessorKey: "codigo", cell: (v) => v || "—" },
    { id: "nome", header: "Nome", accessorKey: "nome", cell: (v) => <span className="font-medium">{v}</span> },
    {
      id: "tipo", header: "Tipo", accessorKey: "tipo",
      cell: (v) => <Badge variant="outline">{TIPOS.find(t => t.value === v)?.label ?? v}</Badge>
    },
    {
      id: "unidade", header: "Unidade", accessorKey: "unidade_padrao",
      cell: (v) => UNIDADES.find(u => u.value === v)?.label ?? v
    },
    {
      id: "cotacao", header: "Cotação", accessorKey: "possui_cotacao",
      cell: (v, row) => v ? `${row.bolsa_referencia} (${row.codigo_bolsa})` : "—"
    },
    {
      id: "status", header: "Status", accessorKey: "ativo",
      cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} />,
    },
    {
      id: "acoes", header: "", exportable: false, sortable: false, filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" onClick={() => openEdit(row)}>
            <Pencil className="size-3.5" />
          </Button>
          <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" onClick={() => remove.mutate(row.id)}>
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/backoffice/tabelas"><Button variant="ghost" size="icon" className="size-8"><ArrowLeft className="size-4" /></Button></Link>
          <div>
            <h1 className="text-xl font-semibold">Commodities do Sistema</h1>
            <p className="text-sm text-muted-foreground">Produtos base de mercado sem parâmetros de qualidade locais</p>
          </div>
        </div>
        <Button size="sm" onClick={openNew}><Plus className="size-4 mr-1" />Nova Commodity</Button>
      </div>

      <DataTable data={data} columns={columns} searchPlaceholder="Buscar commodities..." exportFileName="commodities-sistema" emptyMessage="Nenhuma commodity cadastrada" />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-2xl p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Package className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Commodity" : "Nova Commodity do Sistema"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5 col-span-1">
              <Label className="text-xs font-medium">Código *</Label>
              <Input value={form.codigo ?? ""} className="h-8 rounded-sm text-xs" onChange={(e) => set({ codigo: e.target.value.toUpperCase() })} placeholder="Ex: SOJ" />
            </div>

            <div className="space-y-1.5 col-span-1">
              <Label className="text-xs font-medium">Nome *</Label>
              <Input value={form.nome ?? ""} className="h-8 rounded-sm text-xs" onChange={(e) => set({ nome: e.target.value })} placeholder="Ex: Soja Convencional" />
            </div>

            <div className="space-y-1.5 col-span-1">
              <Label className="text-xs font-medium">Tipo</Label>
              <Select value={form.tipo ?? "AGRICOLA"} onValueChange={(v: string) => set({ tipo: v })}>
                <SelectTrigger className="h-8 rounded-sm text-xs">
                  <SelectValue placeholder={TIPOS.find(t => t.value === form.tipo)?.label || "Agrícola"} />
                </SelectTrigger>
                <SelectContent className="rounded-sm">{TIPOS.map((t) => <SelectItem key={t.value} value={t.value} className="text-xs">{t.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 col-span-1">
              <Label className="text-xs font-medium">Unidade Padrão</Label>
              <Select value={form.unidade_padrao ?? "SACA_60KG"} onValueChange={(v: string) => set({ unidade_padrao: v })}>
                <SelectTrigger className="h-8 rounded-sm text-xs">
                  <SelectValue placeholder={UNIDADES.find(u => u.value === form.unidade_padrao)?.label || "Saca (60 kg)"} />
                </SelectTrigger>
                <SelectContent className="rounded-sm">{UNIDADES.map((u) => <SelectItem key={u.value} value={u.value} className="text-xs">{u.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 col-span-1">
              <Label className="text-xs font-medium">Peso da Unidade (KG)</Label>
              <Input type="number" step="1" className="h-8 rounded-sm text-xs" value={form.peso_unidade ?? ""} onChange={(e) => set({ peso_unidade: e.target.value ? +e.target.value : undefined })} placeholder="Ex: 60" />
            </div>

            <div className="col-span-2 mt-2 pt-4 border-t">
              <div className="flex items-center justify-between mb-4">
                <Label className="text-sm font-semibold">Informações de Mercado</Label>
                <div className="flex items-center gap-2">
                  <Switch id="possui_cotacao" checked={form.possui_cotacao ?? false} onCheckedChange={(v) => set({ possui_cotacao: v })} />
                  <Label htmlFor="possui_cotacao" className="text-xs">Ativar Cotação</Label>
                </div>
              </div>

              {form.possui_cotacao && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Bolsa de Referência</Label>
                    <Input value={form.bolsa_referencia ?? ""} className="h-8 rounded-sm text-xs" onChange={(e) => set({ bolsa_referencia: e.target.value })} placeholder="Ex: B3, CBOT" />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Código da Bolsa (Ticker)</Label>
                    <Input value={form.codigo_bolsa ?? ""} className="h-8 rounded-sm text-xs" onChange={(e) => set({ codigo_bolsa: e.target.value.toUpperCase() })} placeholder="Ex: SJCc1" />
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 col-span-2 pt-4">
              <Switch id="ativo" checked={form.ativo ?? true} onCheckedChange={(v) => set({ ativo: v })} />
              <Label htmlFor="ativo" className="text-xs">Ativo</Label>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="size-3.5 mr-1.5" />
              Cancelar
            </Button>
            <Button 
              variant="outline"
              size="sm"
              className="rounded-sm border-primary/50 text-primary hover:bg-primary/5"
              onClick={() => save.mutate(form)} 
              disabled={!form.nome || !form.codigo || !form.tipo || save.isPending}
            >
              <Save className="size-3.5 mr-1.5" />
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
