"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowLeft, CheckSquare, Pencil, Plus, Save, Trash2, XCircle } from "lucide-react";
import Link from "next/link";

import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const FASES = [
  { key: "PLANEJADA", label: "Planejamento" },
  { key: "PREPARO_SOLO", label: "Preparo Solo" },
  { key: "PLANTIO", label: "Plantio" },
  { key: "DESENVOLVIMENTO", label: "Desenvolvimento" },
  { key: "COLHEITA", label: "Colheita" },
  { key: "POS_COLHEITA", label: "Pós-Colheita" },
  { key: "ENCERRADA", label: "Encerrada" },
] as const;

export interface TipoOperacao {
  id: string;
  tipo_operacao: string;
  fases_permitidas: string[];
  descricao?: string | null;
  created_at: string;
}

type FormState = {
  tipo_operacao: string;
  fases_permitidas: string[];
  descricao: string;
};

const EMPTY: FormState = {
  tipo_operacao: "",
  fases_permitidas: ["PLANTIO"],
  descricao: "",
};

export function TiposOperacaoClient({ initialData }: { initialData: TipoOperacao[] }) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; item?: TipoOperacao }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);

  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));
  const toggleFase = (fase: string, checked: boolean) => {
    set({
      fases_permitidas: checked
        ? Array.from(new Set([...form.fases_permitidas, fase]))
        : form.fases_permitidas.filter((item) => item !== fase),
    });
  };

  const { data = [] } = useQuery<TipoOperacao[]>({
    queryKey: ["bo-operacoes-tipos"],
    queryFn: () => apiFetch("/operacoes/tipos"),
    initialData,
  });

  const save = useMutation({
    mutationFn: (payload: FormState) =>
      dialog.item
        ? apiFetch(`/operacoes/tipos/${dialog.item.id}`, { method: "PATCH", body: JSON.stringify(payload) })
        : apiFetch("/operacoes/tipos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bo-operacoes-tipos"] });
      qc.invalidateQueries({ queryKey: ["operacoes-tipos"] });
      setDialog({ open: false });
      setForm(EMPTY);
      toast.success(dialog.item ? "Tipo de operação atualizado." : "Tipo de operação criado.");
    },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`/operacoes/tipos/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bo-operacoes-tipos"] });
      qc.invalidateQueries({ queryKey: ["operacoes-tipos"] });
      toast.success("Tipo de operação excluído.");
    },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao excluir"),
  });

  function openNew() {
    setForm(EMPTY);
    setDialog({ open: true });
  }

  function openEdit(item: TipoOperacao) {
    setForm({
      tipo_operacao: item.tipo_operacao,
      fases_permitidas: item.fases_permitidas,
      descricao: item.descricao ?? "",
    });
    setDialog({ open: true, item });
  }

  const columns: ColumnDef<TipoOperacao>[] = [
    {
      id: "tipo",
      header: "Tipo",
      accessorKey: "tipo_operacao",
      cell: (v) => <span className="font-semibold">{v}</span>,
    },
    {
      id: "fases",
      header: "Fases Permitidas",
      cell: (_: unknown, row: TipoOperacao) => (
        <div className="flex flex-wrap gap-1">
          {row.fases_permitidas.map((fase) => (
            <Badge key={fase} variant="outline" className="text-[10px]">
              {fase}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      id: "descricao",
      header: "Descrição",
      accessorKey: "descricao",
      cell: (v: string | null) => v || "—",
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_: unknown, row: TipoOperacao) => (
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
        title="Tipos de Operação"
        description="Cadastro global dos tipos de operação agrícola e suas fases permitidas."
        breadcrumbs={[
          { label: "Backoffice", href: "/backoffice" },
          { label: "Tabelas", href: "/backoffice/tabelas" },
          { label: "Tipos de Operação" },
        ]}
        icon={<CheckSquare className="text-primary" size={22} />}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/backoffice/tabelas">
                <ArrowLeft className="size-3.5 mr-1.5" />
                Voltar
              </Link>
            </Button>
            <Button size="sm" variant="outline" onClick={openNew}>
              <Plus className="size-3.5 mr-1.5" />
              Novo Tipo
            </Button>
          </div>
        }
      />

      <DataTable
        data={data}
        columns={columns}
        searchPlaceholder="Buscar tipos de operação..."
        exportFileName="tipos-operacao"
        emptyMessage="Nenhum tipo de operação cadastrado"
      />

      <Dialog open={dialog.open} onOpenChange={(open) => setDialog({ open })}>
        <DialogContent className="max-w-xl p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Activity className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Tipo de Operação" : "Novo Tipo de Operação"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Código / Nome *</Label>
                <Input
                  value={form.tipo_operacao}
                  onChange={(e) => set({ tipo_operacao: e.target.value.toUpperCase() })}
                  placeholder="Ex: PULVERIZAÇÃO"
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Descrição</Label>
                <Input
                  value={form.descricao}
                  onChange={(e) => set({ descricao: e.target.value })}
                  placeholder="Resumo de uso do tipo"
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">Fases Permitidas *</Label>
              <div className="grid grid-cols-2 gap-3 rounded-sm border p-3">
                {FASES.map((fase) => (
                  <label key={fase.key} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={form.fases_permitidas.includes(fase.key)}
                      onCheckedChange={(checked) => toggleFase(fase.key, checked === true)}
                    />
                    <span>{fase.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </DialogBody>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" type="button" onClick={() => setDialog({ open: false })}>
              <XCircle className="size-3.5 mr-1.5" />
              Cancelar
            </Button>
            <Button
              size="sm"
              variant="outline"
              type="button"
              disabled={!form.tipo_operacao.trim() || form.fases_permitidas.length === 0 || save.isPending}
              onClick={() => save.mutate(form)}
            >
              <Save className="size-3.5 mr-1.5" />
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
