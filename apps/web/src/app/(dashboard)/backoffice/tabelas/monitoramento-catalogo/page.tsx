"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, ArrowLeft, Activity, Save, XCircle, Bug } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

const TIPOS = ["PRAGA", "DOENCA", "PLANTA_DANINHA", "OUTRO"];

const TIPO_BADGE: Record<string, string> = {
  PRAGA: "destructive",
  DOENCA: "secondary",
  PLANTA_DANINHA: "outline",
  OUTRO: "outline",
};

interface CatalogoItem {
  id: string;
  tipo: string;
  nome_popular: string;
  nome_cientifico?: string;
  cultura?: string;
  nde_padrao?: number;
  unidade_medida?: string;
  is_system: boolean;
  ativo: boolean;
}

type FormState = Partial<CatalogoItem>;
const EMPTY: FormState = { tipo: "PRAGA", nome_popular: "", is_system: true, ativo: true };

export default function BackofficeMonitoramentoCatalogoPage() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; item?: CatalogoItem }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const { data = [] } = useQuery<CatalogoItem[]>({
    queryKey: ["bo-monitoramento-catalogo"],
    queryFn: () => apiFetch("/backoffice/tabelas/monitoramento-catalogo"),
  });

  const save = useMutation({
    mutationFn: (f: FormState) =>
      dialog.item
        ? apiFetch(`/backoffice/tabelas/monitoramento-catalogo/${dialog.item.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch("/backoffice/tabelas/monitoramento-catalogo", { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-monitoramento-catalogo"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/monitoramento-catalogo/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-monitoramento-catalogo"] }),
    onError: (e: any) => alert(e?.message ?? "Erro ao excluir"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: CatalogoItem) { setForm(item); setDialog({ open: true, item }); }

  const columns: ColumnDef<CatalogoItem>[] = [
    {
      id: "tipo", header: "Tipo", accessorKey: "tipo",
      cell: (v) => <Badge variant={(TIPO_BADGE[v] ?? "outline") as any}>{v}</Badge>,
    },
    { id: "nome", header: "Nome Popular", accessorKey: "nome_popular", cell: (v) => <span className="font-medium">{v}</span> },
    { id: "cientifico", header: "Nome Científico", accessorKey: "nome_cientifico", cell: (v) => v ? <span className="italic text-muted-foreground">{v}</span> : "—" },
    { id: "cultura", header: "Cultura", accessorKey: "cultura", cell: (v) => v ?? <span className="text-muted-foreground">Todas</span> },
    { id: "nde", header: "NDE padrão", accessorKey: "nde_padrao", cell: (v) => v != null ? v : "—" },
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
    <div className="p-6 space-y-6">
      <PageHeader
        title="Catálogo de Monitoramento"
        description="Pragas, doenças e plantas daninhas com NDE padrão por cultura"
        breadcrumbs={[
          { label: "Backoffice", href: "/backoffice" },
          { label: "Tabelas", href: "/backoffice/tabelas" },
          { label: "Catálogo de Monitoramento" }
        ]}
        icon={<Bug className="text-primary" size={22} />}
      />

      <DataTable data={data} columns={columns} searchPlaceholder="Buscar pragas, doenças..." exportFileName="monitoramento-catalogo-sistema" emptyMessage="Nenhum item cadastrado" />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-lg p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Activity className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Item" : "Novo Item do Catálogo"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Tipo</Label>
                <Select value={form.tipo ?? "PRAGA"} onValueChange={(v) => set({ tipo: v })}>
                  <SelectTrigger className="h-8 text-xs rounded-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {TIPOS.map((t) => <SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Cultura (opcional)</Label>
                <Input 
                  value={form.cultura ?? ""} 
                  onChange={(e) => set({ cultura: e.target.value || undefined })} 
                  placeholder="Todas" 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome Popular *</Label>
              <Input 
                value={form.nome_popular ?? ""} 
                onChange={(e) => set({ nome_popular: e.target.value })} 
                placeholder="Ex: Lagarta-do-cartucho" 
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome Científico</Label>
              <Input 
                value={form.nome_cientifico ?? ""} 
                onChange={(e) => set({ nome_cientifico: e.target.value || undefined })} 
                placeholder="Ex: Spodoptera frugiperda" 
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">NDE padrão</Label>
                <Input 
                  type="number" 
                  step="0.01" 
                  value={form.nde_padrao ?? ""} 
                  onChange={(e) => set({ nde_padrao: e.target.value ? +e.target.value : undefined })} 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Unidade de medida</Label>
                <Input 
                  value={form.unidade_medida ?? ""} 
                  onChange={(e) => set({ unidade_medida: e.target.value || undefined })} 
                  placeholder="lagartas/planta" 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Switch id="ativo" checked={form.ativo ?? true} onCheckedChange={(v) => set({ ativo: v })} />
              <Label htmlFor="ativo" className="text-xs font-medium">Ativo</Label>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="mr-1.5 size-3.5" />
              Cancelar
            </Button>
            <Button 
              size="sm" 
              variant="outline" 
              className="rounded-sm border-primary/50 text-primary hover:bg-primary/5"
              onClick={() => save.mutate(form)} 
              disabled={!form.nome_popular || !form.tipo || save.isPending}
            >
              <Save className="mr-1.5 size-3.5" />
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
