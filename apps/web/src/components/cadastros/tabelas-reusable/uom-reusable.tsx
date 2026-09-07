"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Pencil, Trash2, Lock, Save, Ruler, XCircle } from "lucide-react";
import { toast } from "sonner";
import { StatusBadge } from "@/components/ui/status-badge";
import { UnidadeConversorDialog } from "@/components/shared/unidade-conversor-dialog";

interface Uom {
  id: string;
  codigo: string;
  nome: string;
  dimensao: string;
  codigo_referencia: string;
  fator_referencia: number;
  casas_decimais: number;
  eh_unidade_base: boolean;
  sistema: boolean;
  ativo: boolean;
  tenant_id: string | null;
}

const DIMENSOES = [
  { value: "massa", label: "Massa" },
  { value: "volume", label: "Volume" },
  { value: "area", label: "Área" },
  { value: "tempo", label: "Tempo" },
  { value: "contagem", label: "Contagem" },
  { value: "moeda", label: "Moeda" },
  { value: "hora_maquina", label: "Hora-máquina" },
  { value: "hora_homem", label: "Homem-hora" },
];

type FormState = Partial<Uom>;
const EMPTY: FormState = {
  codigo: "",
  nome: "",
  dimensao: "",
  codigo_referencia: "",
  fator_referencia: 1,
  casas_decimais: 2,
  eh_unidade_base: false,
  sistema: false,
  ativo: true,
};

export function UomReusable() {
  const qc = useQueryClient();
  const canWrite = usePermission("backoffice:uom:create");
  const [dialog, setDialog] = useState<{ open: boolean; item?: Uom }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [itemToDelete, setItemToDelete] = useState<Uom | null>(null);

  const queryKey = ["bo-uom"];

  const { data: uoms = [], isLoading } = useQuery<Uom[]>({
    queryKey,
    queryFn: () => apiFetch("/backoffice/uom/"),
  });

  const save = useMutation({
    mutationFn: (payload: FormState) =>
      dialog.item
        ? apiFetch(`/backoffice/uom/${dialog.item.id}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          })
        : apiFetch("/backoffice/uom/", {
            method: "POST",
            body: JSON.stringify(payload),
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      setDialog({ open: false });
      toast.success(dialog.item ? "Unidade atualizada" : "Unidade cadastrada");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/backoffice/uom/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Unidade desativada");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao desativar"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: Uom) { setForm(item); setDialog({ open: true, item }); }
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const columns: ColumnDef<Uom>[] = [
    {
      id: "codigo",
      header: "Código",
      accessorKey: "codigo",
      cell: (v) => <span className="font-mono font-semibold text-sm">{v}</span>,
      sortable: true,
      filterable: true,
    },
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (_, row) => (
        <div className="flex flex-col">
          <span className="font-medium text-foreground">{row.nome}</span>
          {row.eh_unidade_base && (
            <span className="text-[10px] text-muted-foreground">unidade-base</span>
          )}
        </div>
      ),
      sortable: true,
      filterable: true,
    },
    {
      id: "dimensao",
      header: "Dimensão",
      accessorKey: "dimensao",
      cell: (v) => (
        <Badge variant="outline" className="text-[10px] font-normal uppercase tracking-wider">
          {DIMENSOES.find((d) => d.value === v)?.label || v || "—"}
        </Badge>
      ),
      sortable: true,
      filterable: true,
    },
    {
      id: "unidade_base",
      header: "Unidade-base / Fator",
      accessorKey: "codigo_referencia",
      cell: (_, row) => (
        <span className="font-mono text-xs text-muted-foreground">
          {row.eh_unidade_base ? "—" : `${row.fator_referencia} ${row.codigo_referencia}`}
        </span>
      ),
    },
    {
      id: "casas",
      header: "Dec.",
      accessorKey: "casas_decimais",
      cell: (v) => <span className="font-mono text-xs">{v}</span>,
    },
    {
      id: "origem",
      header: "Origem",
      accessorKey: "sistema",
      cell: (v) =>
        v ? (
          <Badge variant="secondary" className="gap-1 text-[10px] h-5 rounded-sm">
            <Lock className="size-2.5" /> Sistema
          </Badge>
        ) : (
          <Badge variant="outline" className="text-[10px] h-5 rounded-sm">
            Personalizada
          </Badge>
        ),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativo",
      cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} />,
      sortable: true,
    },
    {
      id: "actions",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          {canWrite && (
            <>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 text-primary"
                onClick={() => openEdit(row)}
              >
                <Pencil className="size-3.5" />
              </Button>
              {!row.sistema && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 text-destructive"
                  onClick={() => setItemToDelete(row)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              )}
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Unidades de Medida</h2>
        <div className="flex items-center gap-2">
          <UnidadeConversorDialog />
          {canWrite && (
            <Button size="sm" variant="outline" className="h-8 rounded-sm text-xs" onClick={openNew}>
              <Plus className="mr-2 size-3.5" />
              Nova Unidade
            </Button>
          )}
        </div>
      </div>

      <DataTable
        data={uoms}
        columns={columns}
        isLoading={isLoading}
        searchPlaceholder="Buscar por código ou nome..."
        emptyMessage="Nenhuma unidade de medida encontrada"
      />

      <ConfirmDialog
        open={!!itemToDelete}
        title="Desativar unidade?"
        description={itemToDelete ? `A unidade "${itemToDelete.codigo}" será desativada.` : undefined}
        confirmText="Desativar"
        destructive
        onCancel={() => setItemToDelete(null)}
        onConfirm={() => {
          if (!itemToDelete) return;
          remove.mutate(itemToDelete.id, {
            onSettled: () => setItemToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => !o && setDialog({ open: false })}>
        <DialogContent className="max-w-lg p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Ruler className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Unidade" : "Nova Unidade de Medida"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Código *</Label>
                <Input
                  value={form.codigo ?? ""}
                  onChange={(e) => set({ codigo: e.target.value })}
                  placeholder="Ex: KG"
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Nome *</Label>
                <Input
                  value={form.nome ?? ""}
                  onChange={(e) => set({ nome: e.target.value })}
                  placeholder="Ex: Quilograma"
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Dimensão *</Label>
              <Select value={form.dimensao ?? ""} onValueChange={(v: string) => set({ dimensao: v })}>
                <SelectTrigger className="h-8 text-xs rounded-sm">
                  <SelectValue placeholder="Selecione..." />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  {DIMENSOES.map((d: { value: string; label: string }) => (
                    <SelectItem key={d.value} value={d.value} className="text-xs">
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Código de Referência *</Label>
                <Input
                  value={form.codigo_referencia ?? ""}
                  onChange={(e) => set({ codigo_referencia: e.target.value })}
                  placeholder="Ex: KG"
                  disabled={form.eh_unidade_base}
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Fator de Referência *</Label>
                <Input
                  type="number"
                  step="any"
                  value={form.fator_referencia ?? ""}
                  onChange={(e) => set({ fator_referencia: e.target.value ? +e.target.value : undefined })}
                  disabled={form.eh_unidade_base}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Casas Decimais</Label>
              <Input
                type="number"
                min={0}
                max={6}
                value={form.casas_decimais ?? 2}
                onChange={(e) => set({ casas_decimais: e.target.value ? +e.target.value : 2 })}
                className="h-8 text-xs rounded-sm w-24"
              />
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <Switch
                  checked={form.eh_unidade_base ?? false}
                  onCheckedChange={(v) =>
                    set({ eh_unidade_base: v, ...(v ? { fator_referencia: 1 } : {}) })
                  }
                />
                <Label>É a unidade-base da dimensão</Label>
              </div>
              {dialog.item && (
                <div className="flex items-center gap-2">
                  <Switch checked={form.ativo ?? true} onCheckedChange={(v) => set({ ativo: v })} />
                  <Label>Ativo</Label>
                </div>
              )}
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="size-3.5 mr-1.5" />
              Cancelar
            </Button>
            <Button
              size="sm"
              variant="default"
              className="rounded-sm"
              onClick={() => save.mutate(form)}
              disabled={!form.codigo || !form.nome || !form.dimensao || save.isPending}
            >
              <Save className="mr-2 size-3.5" />
              {save.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
