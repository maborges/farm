"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Edit2, Trash2, GripVertical, Palette } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { StatusBadge } from "@/components/ui/status-badge";

interface Estagio {
  id: string;
  nome: string;
  cor: string;
  ordem: number;
  ativo: boolean;
  leads_count?: number;
}

interface EstagioCreate {
  nome: string;
  cor: string;
  ordem: number;
}

const CORES_SUGERIDAS = [
  "#3b82f6", // Blue
  "#8b5cf6", // Purple
  "#f59e0b", // Amber
  "#ec4899", // Pink
  "#10b981", // Green
  "#06b6d4", // Cyan
  "#f87171", // Red
  "#6366f1", // Indigo
];

export default function PipelinePage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [dialog, setDialog] = useState<{ open: boolean; estagio?: Estagio }>({
    open: false,
  });
  const [form, setForm] = useState<EstagioCreate>({
    nome: "",
    cor: "#3b82f6",
    ordem: 0,
  });

  // Fetch estágios
  const { data: estagios = [], isLoading } = useQuery<Estagio[]>({
    queryKey: ["pipeline-estagios"],
    queryFn: () => apiFetch("/backoffice/crm/pipeline"),
  });

  // Create estagio
  const create = useMutation({
    mutationFn: (data: EstagioCreate) =>
      apiFetch("/backoffice/crm/pipeline", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline-estagios"] });
      setDialog({ open: false });
      setForm({ nome: "", cor: "#3b82f6", ordem: 0 });
      toast({ title: "Estágio criado com sucesso" });
    },
    onError: () => toast({ title: "Erro ao criar estágio", variant: "destructive" }),
  });

  // Update estagio
  const update = useMutation({
    mutationFn: (data: Estagio) =>
      apiFetch(`/backoffice/crm/pipeline/${data.id}`, { method: "PUT", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline-estagios"] });
      setDialog({ open: false });
      toast({ title: "Estágio atualizado com sucesso" });
    },
    onError: () => toast({ title: "Erro ao atualizar estágio", variant: "destructive" }),
  });

  // Delete estagio
  const remove = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/backoffice/crm/pipeline/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline-estagios"] });
      toast({ title: "Estágio deletado com sucesso" });
    },
    onError: () => toast({ title: "Erro ao deletar estágio", variant: "destructive" }),
  });

  function openNew() {
    setForm({ nome: "", cor: "#3b82f6", ordem: (estagios?.length || 0) + 1 });
    setDialog({ open: true });
  }

  function openEdit(e: Estagio) {
    setForm({ nome: e.nome, cor: e.cor, ordem: e.ordem });
    setDialog({ open: true, estagio: e });
  }

  function handleSubmit() {
    if (!form.nome.trim()) {
      toast({ title: "Nome do estágio é obrigatório", variant: "destructive" });
      return;
    }

    if (dialog.estagio) {
      update.mutate({ ...dialog.estagio, ...form });
    } else {
      create.mutate(form);
    }
  }

  const totalLeads = (estagios || []).reduce((sum, e) => sum + (e.leads_count || 0), 0);
  const activeCount = (estagios || []).filter((e) => e.ativo).length;

  return (
    <div className="space-y-6">
      {/* Header com título e botão */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Pipeline de Vendas</h1>
        <Button onClick={openNew} className="gap-2">
          <Plus size={16} />
          Novo Estágio
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={GripVertical}
          label="Total de Estágios"
          value={estagios?.length || 0}
          color="primary"
        />
        <StatCard
          icon={Badge}
          label="Estágios Ativos"
          value={activeCount}
          color="success"
        />
        <StatCard
          icon={Palette}
          label="Total de Leads"
          value={totalLeads}
          color="backoffice"
        />
        <StatCard
          icon={GripVertical}
          label="Leads / Estágio"
          value={estagios?.length ? Math.round(totalLeads / estagios.length) : 0}
          color="warning"
        />
      </div>

      {/* Estágios Cards - Layout em Colunas Horizontal */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Carregando estágios...</div>
      ) : estagios?.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Nenhum estágio criado. Comece adicionando um novo!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {estagios
            ?.sort((a, b) => a.ordem - b.ordem)
            .map((estagio) => (
              <Card key={estagio.id} className="hover:shadow-md transition-shadow flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="w-6 h-6 rounded-full border-2 border-gray-300 flex-shrink-0"
                      style={{ backgroundColor: estagio.cor }}
                      title={estagio.cor}
                    />
                    <CardTitle className="text-base">{estagio.nome}</CardTitle>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Posição: {estagio.ordem}</span>
                    <span className="font-semibold">{estagio.leads_count || 0} leads</span>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col justify-between pt-2">
                  <div>
                    {estagio.ativo ? (
                      <StatusBadge status="ativo" />
                    ) : (
                      <StatusBadge status="inativo" />
                    )}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEdit(estagio)}
                      className="gap-1 flex-1 text-xs h-8"
                    >
                      <Edit2 size={12} />
                      Editar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => remove.mutate(estagio.id)}
                      className="gap-1 text-red-600 hover:text-red-700 text-xs h-8"
                    >
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
        </div>
      )}

      {/* Dialog para criar/editar */}
      <Dialog open={dialog.open} onOpenChange={(open) => setDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialog.estagio ? "Editar Estágio" : "Novo Estágio"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Nome */}
            <div className="grid gap-2">
              <Label htmlFor="nome">Nome do Estágio *</Label>
              <Input
                id="nome"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                placeholder="Ex: Prospecção, Qualificação, Proposta..."
              />
            </div>

            {/* Cor */}
            <div className="grid gap-2">
              <Label htmlFor="cor">Cor</Label>
              <div className="flex gap-2 flex-wrap">
                {CORES_SUGERIDAS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setForm({ ...form, cor: c })}
                    className={`w-10 h-10 rounded-lg border-2 transition-all ${
                      form.cor === c ? "border-gray-800" : "border-gray-200"
                    }`}
                    style={{ backgroundColor: c }}
                    title={c}
                  />
                ))}
              </div>
              <div className="flex gap-2 items-center">
                <div
                  className="w-8 h-8 rounded border-2 border-gray-300"
                  style={{ backgroundColor: form.cor }}
                />
                <Input
                  type="text"
                  value={form.cor}
                  onChange={(e) => setForm({ ...form, cor: e.target.value })}
                  placeholder="#3b82f6"
                  className="font-mono text-sm"
                />
              </div>
            </div>

            {/* Ordem */}
            <div className="grid gap-2">
              <Label htmlFor="ordem">Posição na Fila</Label>
              <Input
                id="ordem"
                type="number"
                value={form.ordem}
                onChange={(e) => setForm({ ...form, ordem: parseInt(e.target.value) })}
                min="1"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false })}>
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={create.isPending || update.isPending}
            >
              {dialog.estagio ? "Atualizar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
