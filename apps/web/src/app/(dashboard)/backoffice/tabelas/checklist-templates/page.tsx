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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/status-badge";

const CONTEXTOS = ["OPERACAO_AGRICOLA", "FROTA_PRE_USO", "FROTA_POS_USO", "COLHEITA", "PLANTIO", "PULVERIZACAO", "OUTRO"];

interface ChecklistTemplate {
  id: string;
  nome: string;
  contexto: string;
  descricao?: string;
  is_system: boolean;
  ativo: boolean;
}

type FormState = Partial<ChecklistTemplate>;
const EMPTY: FormState = { nome: "", contexto: "OPERACAO_AGRICOLA", is_system: true, ativo: true };

export default function BackofficeChecklistTemplatesPage() {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; item?: ChecklistTemplate }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const { data = [] } = useQuery<ChecklistTemplate[]>({
    queryKey: ["bo-checklist-templates"],
    queryFn: () => apiFetch("/backoffice/tabelas/checklist-templates"),
  });

  const save = useMutation({
    mutationFn: (f: FormState) =>
      dialog.item
        ? apiFetch(`/backoffice/tabelas/checklist-templates/${dialog.item.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch("/backoffice/tabelas/checklist-templates", { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bo-checklist-templates"] }); setDialog({ open: false }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/tabelas/checklist-templates/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bo-checklist-templates"] }),
    onError: (e: any) => alert(e?.message ?? "Erro ao excluir"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: ChecklistTemplate) { setForm(item); setDialog({ open: true, item }); }

  const columns: ColumnDef<ChecklistTemplate>[] = [
    { id: "nome", header: "Nome", accessorKey: "nome", cell: (v) => <span className="font-medium">{v}</span> },
    { id: "contexto", header: "Contexto", accessorKey: "contexto", cell: (v) => <Badge variant="outline">{v}</Badge> },
    { id: "descricao", header: "Descrição", accessorKey: "descricao", cell: (v) => v ?? "—" },
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
            <h1 className="text-xl font-semibold">Templates de Checklist</h1>
            <p className="text-sm text-muted-foreground">Modelos globais disponíveis a todos os tenants</p>
          </div>
        </div>
        <Button size="sm" onClick={openNew}><Plus className="size-4 mr-1" />Novo Template</Button>
      </div>

      <DataTable data={data} columns={columns} searchPlaceholder="Buscar templates..." exportFileName="checklist-templates-sistema" emptyMessage="Nenhum template cadastrado" />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{dialog.item ? "Editar Template" : "Novo Template do Sistema"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Nome *</Label>
              <Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} placeholder="Ex: Pré-operação Pulverizador" />
            </div>
            <div className="space-y-1.5">
              <Label>Contexto</Label>
              <Select value={form.contexto ?? "OPERACAO_AGRICOLA"} onValueChange={(v) => set({ contexto: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{CONTEXTOS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Descrição</Label>
              <Input value={form.descricao ?? ""} onChange={(e) => set({ descricao: e.target.value })} />
            </div>
            <div className="flex items-center gap-2">
              <Switch id="ativo" checked={form.ativo ?? true} onCheckedChange={(v) => set({ ativo: v })} />
              <Label htmlFor="ativo">Ativo</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false })}>Cancelar</Button>
            <Button onClick={() => save.mutate(form)} disabled={!form.nome || save.isPending}>
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
