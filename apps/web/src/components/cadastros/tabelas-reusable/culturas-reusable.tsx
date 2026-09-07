"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Plus,
  Pencil,
  Trash2,
  Lock,
  Save,
  FlaskConical,
  Sprout,
  Search,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { ParametrosSoloSheet } from "./parametros-solo-sheet";
import { StatusBadge } from "@/components/ui/status-badge";

interface Cultura {
  id: string;
  tenant_id: string | null;
  sistema: boolean;
  nome: string;
  nome_cientifico?: string;
  grupo?: string;
  ciclo_dias_min?: number;
  ciclo_dias_max?: number;
  espacamento_cm?: number;
  populacao_plantas_ha?: number;
  produtividade_media_sc_ha?: number;
  ativa: boolean;
}

interface CulturasReusableProps {
  mode: "subscriber" | "backoffice";
}

type FormState = Partial<Cultura>;
const EMPTY: FormState = {
  nome: "",
  nome_cientifico: "",
  grupo: "",
  ciclo_dias_min: undefined,
  ciclo_dias_max: undefined,
  ativa: true,
};

const GRUPOS = [
  { value: "GRAOS", label: "Grãos" },
  { value: "FIBRAS", label: "Fibras" },
  { value: "FRUTAS", label: "Frutas" },
  { value: "HORTALICAS", label: "Hortaliças" },
  { value: "PASTAGEM", label: "Pastagem" },
  { value: "OUTRO", label: "Outro" },
];

export function CulturasReusable({ mode }: CulturasReusableProps) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; item?: Cultura }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [soloSheetItem, setSoloSheetItem] = useState<Cultura | null>(null);
  const [culturaToDelete, setCulturaToDelete] = useState<Cultura | null>(null);

  const baseUrl = mode === "backoffice" 
    ? "/backoffice/tabelas/culturas" 
    : "/cadastros/culturas";
  
  const queryKey = [mode === "backoffice" ? "bo-tabelas-culturas" : "culturas"];

  const { data: cultures = [], isLoading } = useQuery<Cultura[]>({
    queryKey,
    queryFn: () => apiFetch(baseUrl),
  });

  const save = useMutation({
    mutationFn: (payload: FormState) =>
      dialog.item
        ? apiFetch(`${baseUrl}/${dialog.item.id}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          })
        : apiFetch(baseUrl, {
            method: "POST",
            body: JSON.stringify(payload),
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      setDialog({ open: false });
      toast.success(dialog.item ? "Cultura atualizada" : "Cultura cadastrada");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`${baseUrl}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Cultura removida");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao excluir"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: Cultura) { setForm(item); setDialog({ open: true, item }); }
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const columns: ColumnDef<Cultura>[] = [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (_, row) => (
        <div className="flex flex-col">
          <span className="font-medium text-foreground">{row.nome}</span>
          {row.nome_cientifico && (
            <span className="text-[10px] text-muted-foreground italic">{row.nome_cientifico}</span>
          )}
        </div>
      ),
      sortable: true,
      filterable: true,
    },
    {
      id: "grupo",
      header: "Grupo",
      accessorKey: "grupo",
      cell: (v) => (
        <Badge variant="metadata" className="rounded-md">
          {GRUPOS.find(g => g.value === v)?.label || v || "—"}
        </Badge>
      ),
      sortable: true,
      filterable: true,
    },
    {
      id: "ciclo",
      header: "Ciclo (Dias)",
      accessorKey: "ciclo_dias_min",
      cell: (_, row) => (
        <span className="font-mono text-xs">
          {row.ciclo_dias_min && row.ciclo_dias_max 
            ? `${row.ciclo_dias_min}–${row.ciclo_dias_max}` 
            : row.ciclo_dias_min || row.ciclo_dias_max || "—"}
        </span>
      ),
    },
    {
      id: "origem",
      header: "Origem",
      accessorKey: "sistema",
      cell: (v) => v ? (
        <Badge variant="metadata" className="gap-1 rounded-md">
          <Lock className="size-2.5" /> Sistema
        </Badge>
      ) : (
        <Badge variant="metadata" className="rounded-md">Personalizada</Badge>
      ),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativa",
      cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} />,
      sortable: true,
    },
    {
      id: "actions",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => {
        const canEdit = mode === "backoffice" || !row.sistema;
        return (
          <div className="flex items-center gap-0 justify-end">
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-primary"
              title="Parâmetros de Solo"
              onClick={() => setSoloSheetItem(row)}
            >
              <FlaskConical className="size-3.5" />
            </Button>
            {canEdit && (
              <>
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 text-primary"
                  onClick={() => openEdit(row)}
                >
                  <Pencil className="size-3.5" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 text-destructive"
                  onClick={() => setCulturaToDelete(row)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Culturas e Variedades</h2>
        <Button size="sm" variant="outline" className="h-8 rounded-sm text-xs" onClick={openNew}>
          <Plus className="mr-2 size-3.5" />
          Nova Cultura
        </Button>
      </div>

      <DataTable
        data={cultures}
        columns={columns}
        isLoading={isLoading}
        searchPlaceholder="Buscar cultura ou variedade..."
        emptyMessage="Nenhuma cultura encontrada"
      />

      <ConfirmDialog
        open={!!culturaToDelete}
        title="Remover cultura?"
        description={culturaToDelete ? `A cultura "${culturaToDelete.nome}" será removida.` : undefined}
        confirmText="Remover"
        destructive
        onCancel={() => setCulturaToDelete(null)}
        onConfirm={() => {
          if (!culturaToDelete) return;
          remove.mutate(culturaToDelete.id, {
            onSettled: () => setCulturaToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => !o && setDialog({ open: false })}>
        <DialogContent className="max-w-lg p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Sprout className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Cultura" : "Nova Cultura"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome da Cultura *</Label>
              <Input 
                value={form.nome ?? ""} 
                onChange={(e) => set({ nome: e.target.value })} 
                placeholder="Ex: Soja, Milho..."
                className="h-8 text-xs rounded-sm"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Nome Científico</Label>
                <Input 
                  value={form.nome_cientifico ?? ""} 
                  onChange={(e) => set({ nome_cientifico: e.target.value })} 
                  placeholder="Ex: Glycine max"
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Grupo</Label>
                <Select value={form.grupo ?? ""} onValueChange={(v: string) => set({ grupo: v })}>
                  <SelectTrigger className="h-8 text-xs rounded-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {GRUPOS.map(g => <SelectItem key={g.value} value={g.value} className="text-xs">{g.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Ciclo Mín. (Dias)</Label>
                <Input 
                  type="number"
                  value={form.ciclo_dias_min ?? ""} 
                  onChange={(e) => set({ ciclo_dias_min: e.target.value ? +e.target.value : undefined })} 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Ciclo Máx. (Dias)</Label>
                <Input 
                  type="number"
                  value={form.ciclo_dias_max ?? ""} 
                  onChange={(e) => set({ ciclo_dias_max: e.target.value ? +e.target.value : undefined })} 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={form.ativa ?? true} onCheckedChange={(v) => set({ ativa: v })} />
              <Label className="text-xs font-medium">Ativa</Label>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="mr-1.5 size-3.5" />
              Cancelar
            </Button>
            <Button
              size="sm"
              className="rounded-sm"
              onClick={() => save.mutate(form)}
              disabled={!form.nome || save.isPending}
            >
              <Save className="mr-1.5 size-3.5" />
              {save.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ParametrosSoloSheet 
        cultura={soloSheetItem}
        open={!!soloSheetItem}
        onClose={() => setSoloSheetItem(null)}
        isBackoffice={mode === "backoffice"}
      />
    </div>
  );
}
