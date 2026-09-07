"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Plus, Pencil, Trash2, ArrowLeft, ClipboardList, ShieldCheck, Settings, ListTodo, Lock, Save } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";

interface BaseTemplate {
  id: string;
  titulo: string;
  descricao?: string;
  cultura?: string;
  fase: string;
  ativo: boolean;
}

interface PhaseTemplate extends BaseTemplate {
  checklist_items: any[];
  tasks: any[];
  gate_rules: any[];
}

interface OperationTemplate extends BaseTemplate {
  items: any[];
}

const FASE_DESCRIPTIONS: Record<string, string> = {
  PLANEJAMENTO: "Planejamento",
  PLANEJADA: "Planejada",
  PREPARO_SOLO: "Preparo de Solo",
  PLANTIO: "Plantio",
  DESENVOLVIMENTO: "Desenvolvimento Vegetativo",
  COLHEITA: "Colheita",
  POS_COLHEITA: "Pós-Colheita",
  ENCERRADA: "Encerrada",
};

type TemplateDetail = PhaseTemplate & OperationTemplate;

export default function TemplateDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const id = params.id as string;
  const type = searchParams.get("type") || "phase";
  const [activeTab, setActiveTab] = useState(type === "phase" ? "checklist" : "items");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<any>({});
  const [isEditing, setIsEditing] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ subType: string; itemId: string; titulo?: string } | null>(null);

  // --- Mutations ---
  const saveMutation = useMutation({
    mutationFn: (data: any) => {
      const url = isEditing 
        ? `/backoffice/tabelas/agro-templates/${activeTab === "items" ? "operations/items" : "phase/" + activeTab}/${data.id}`
        : `/backoffice/tabelas/agro-templates/${activeTab === "items" ? "operations" : "phase"}/${id}/${activeTab}`;
      
      return apiFetch(url, {
        method: isEditing ? "PUT" : "POST",
        body: JSON.stringify(data)
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-template-detail", id, type] });
      toast.success(isEditing ? "Item atualizado" : "Item adicionado");
      setIsDialogOpen(false);
      setFormData({});
      setIsEditing(false);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: ({ subType, itemId }: { subType: string, itemId: string }) => {
      const isPhase = ["checklist", "tasks", "gate"].includes(subType);
      const prefix = isPhase ? "phase" : "operations";
      return apiFetch(`/backoffice/tabelas/agro-templates/${prefix}/${subType}/${itemId}`, { method: "DELETE" });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-template-detail", id, type] });
      toast.success("Item removido com sucesso");
    }
  });

  const handleDeleteItem = (subType: string, itemId: string, titulo?: string) => {
    setItemToDelete({ subType, itemId, titulo });
  };

  const handleEditItem = (item: any) => {
    setFormData(item);
    setIsEditing(true);
    setIsDialogOpen(true);
  };

  // --- Columns Definitions ---
  const checklistCols: ColumnDef<any>[] = [
    { id: "titulo", header: "Título do Item", accessorKey: "titulo", cell: (v) => <span className="text-sm font-medium">{v}</span> },
    { id: "obrigatorio", header: "Obrigatório", accessorKey: "obrigatorio", cell: (v) => <Badge variant={v ? "default" : "secondary"} className="rounded-sm text-[10px]">{v ? "Sim" : "Não"}</Badge> },
    { id: "ordem", header: "Ordem", accessorKey: "ordem", cell: (v) => <span className="text-xs text-muted-foreground">{v}</span> },
    { id: "status", header: "Status", accessorKey: "ativo", cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} /> },
    { id: "acoes", header: "", cell: (_, row) => (
      <div className="flex items-center justify-end gap-1">
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleEditItem(row)}>
          <Pencil className="size-3.5 text-primary" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleDeleteItem("checklist", row.id, row.titulo)}>
          <Trash2 className="size-3.5 text-destructive" />
        </Button>
      </div>
    )},
  ];

  const taskCols: ColumnDef<any>[] = [
    { id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (v) => <Badge variant="outline" className="text-[10px] rounded-sm">{v}</Badge> },
    { id: "titulo", header: "Tarefa", accessorKey: "titulo", cell: (v) => <span className="text-sm font-medium">{v}</span> },
    { id: "criticidade", header: "Crítico", accessorKey: "criticidade", cell: (v) => <Badge variant={v === "ALTA" ? "destructive" : "secondary"} className="text-[10px] rounded-sm">{v}</Badge> },
    { id: "acoes", header: "", cell: (_, row) => (
      <div className="flex items-center justify-end gap-1">
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleEditItem(row)}>
          <Pencil className="size-3.5 text-primary" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleDeleteItem("tasks", row.id, row.titulo)}>
          <Trash2 className="size-3.5 text-destructive" />
        </Button>
      </div>
    )},
  ];

  const gateCols: ColumnDef<any>[] = [
    { id: "rule_type", header: "Regra", accessorKey: "rule_type", cell: (v) => <code className="text-xs font-bold text-primary">{v}</code> },
    { id: "status", header: "Status", accessorKey: "ativo", cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} /> },
    { id: "acoes", header: "", cell: (_, row) => (
      <div className="flex items-center justify-end gap-1">
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleEditItem(row)}>
          <Pencil className="size-3.5 text-primary" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleDeleteItem("gate", row.id, row.titulo)}>
          <Trash2 className="size-3.5 text-destructive" />
        </Button>
      </div>
    )},
  ];

  const opItemCols: ColumnDef<any>[] = [
    { id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (v) => <Badge variant="outline" className="text-[10px] rounded-sm">{v}</Badge> },
    { id: "titulo", header: "Operação/Atividade", accessorKey: "titulo", cell: (v) => <span className="text-sm font-medium">{v}</span> },
    { id: "task", header: "Gera OS", accessorKey: "can_generate_task", cell: (v) => v ? "Sim" : "Não" },
    { id: "acoes", header: "", cell: (_, row) => (
      <div className="flex items-center justify-end gap-1">
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleEditItem(row)}>
          <Pencil className="size-3.5 text-primary" />
        </Button>
        <Button variant="ghost" size="icon" className="size-7 rounded-sm" onClick={() => handleDeleteItem("items", row.id, row.titulo)}>
          <Trash2 className="size-3.5 text-destructive" />
        </Button>
      </div>
    )},
  ];

  // --- Data Fetching ---
  const { data: template, isLoading } = useQuery<TemplateDetail>({
    queryKey: ["agro-template-detail", id, type],
    queryFn: () => apiFetch(`/backoffice/tabelas/agro-templates/${type}/${id}`),
  });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="size-8 rounded-sm" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <Skeleton className="h-10 w-full rounded-sm" />
        <Skeleton className="h-[400px] w-full rounded-sm" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="p-6 text-center space-y-4">
        <p className="text-muted-foreground">Template não encontrado.</p>
        <Link href="/backoffice/tabelas/agro-templates">
          <Button variant="outline" size="sm">Voltar</Button>
        </Link>
      </div>
    );
  }


  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/backoffice/tabelas/agro-templates">
            <Button variant="outline" size="icon" className="size-8 rounded-sm">
              <ArrowLeft className="size-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-foreground/90">{template.titulo}</h1>
              <Badge variant="outline" className="rounded-sm text-[10px] uppercase">
                {type === "phase" ? "Governança" : "Operacional"}
              </Badge>
              {template.fase && (
                <Badge variant="secondary" className="rounded-sm text-[10px]">
                  {FASE_DESCRIPTIONS[template.fase] || template.fase}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{template.descricao || "Sem descrição definida"}</p>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          className="h-8 rounded-sm border-primary text-primary hover:bg-primary/5"
          onClick={() => {
            setFormData({ ativo: true, obrigatorio: false, ordem: (template.checklist_items?.length || 0) + 1 });
            setIsEditing(false);
            setIsDialogOpen(true);
          }}
        >
          <Plus className="size-3.5 mr-1.5" />
          Novo Item
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-4">
          {type === "phase" ? (
            <>
              <TabsTrigger value="checklist" className="gap-2">
                <ClipboardList className="size-4" /> Checklist
              </TabsTrigger>
              <TabsTrigger value="tasks" className="gap-2">
                <ListTodo className="size-4" /> Tarefas Padrão
              </TabsTrigger>
              <TabsTrigger value="gate" className="gap-2">
                <Lock className="size-4" /> Regras de Gate
              </TabsTrigger>
            </>
          ) : (
            <TabsTrigger value="items" className="gap-2">
              <Settings className="size-4" /> Itens da Operação
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="checklist" className="mt-0">
          <div className="rounded-sm border bg-card">
            <DataTable 
              data={template.checklist_items || []} 
              columns={checklistCols} 
              emptyMessage="Nenhum item de checklist configurado."
            />
          </div>
        </TabsContent>

        <TabsContent value="tasks" className="mt-0">
          <div className="rounded-sm border bg-card">
            <DataTable 
              data={template.tasks || []} 
              columns={taskCols} 
              emptyMessage="Nenhuma tarefa padrão configurada."
            />
          </div>
        </TabsContent>

        <TabsContent value="gate" className="mt-0">
          <div className="rounded-sm border bg-card">
            <DataTable 
              data={template.gate_rules || []} 
              columns={gateCols} 
              emptyMessage="Nenhuma regra de gate configurada."
            />
          </div>
        </TabsContent>

        <TabsContent value="items" className="mt-0">
          <div className="rounded-sm border bg-card">
            <DataTable 
              data={template.items || []} 
              columns={opItemCols} 
              emptyMessage="Nenhum item operacional configurado."
            />
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle className="text-lg">
              {isEditing ? "Editar " : "Novo "}
              {activeTab === "checklist" && "Item de Checklist"}
              {activeTab === "tasks" && "Tarefa Padrão"}
              {activeTab === "gate" && "Regra de Gate"}
              {activeTab === "items" && "Item Operacional"}
            </DialogTitle>
          </DialogHeader>

          <DialogBody className="space-y-4">
            {(activeTab === "checklist" || activeTab === "tasks" || activeTab === "items") && (
              <div className="space-y-2">
                <Label>Título</Label>
                <Input 
                  className="h-8 rounded-sm text-sm" 
                  value={formData.titulo || ""} 
                  onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                />
              </div>
            )}

            {activeTab === "gate" && (
              <div className="space-y-2">
                <Label>Tipo de Regra</Label>
                <Select value={formData.rule_type} onValueChange={(v: string) => setFormData({ ...formData, rule_type: v })}>
                  <SelectTrigger className="h-8 rounded-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MANDATORY_CHECKLIST">Checklist Obrigatório</SelectItem>
                    <SelectItem value="MIN_SOIL_ANALYSIS">Análise de Solo Mínima</SelectItem>
                    <SelectItem value="BUDGET_APPROVAL">Aprovação de Orçamento</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {(activeTab === "tasks" || activeTab === "items") && (
              <div className="space-y-2">
                <Label>Tipo de Atividade</Label>
                <Select value={formData.tipo} onValueChange={(v: string) => setFormData({ ...formData, tipo: v })}>
                  <SelectTrigger className="h-8 rounded-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PLANTIO">Plantio</SelectItem>
                    <SelectItem value="PULVERIZACAO">Pulverização</SelectItem>
                    <SelectItem value="ADUBACAO">Adubação</SelectItem>
                    <SelectItem value="COLHEITA">Colheita</SelectItem>
                    <SelectItem value="OUTROS">Outros</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {activeTab === "tasks" && (
              <div className="space-y-2">
                <Label>Criticidade</Label>
                <Select value={formData.criticidade} onValueChange={(v: string) => setFormData({ ...formData, criticidade: v })}>
                  <SelectTrigger className="h-8 rounded-sm">
                    <SelectValue placeholder="Normal" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NORMAL">Normal</SelectItem>
                    <SelectItem value="ALTA">Crítica</SelectItem>
                    <SelectItem value="OPCIONAL">Opcional</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex items-center gap-4 pt-2">
              <div className="flex items-center space-x-2">
                <Switch 
                  id="ativo" 
                  checked={formData.ativo} 
                  onCheckedChange={(v) => setFormData({ ...formData, ativo: v })} 
                />
                <Label htmlFor="ativo">Ativo</Label>
              </div>
              {activeTab === "checklist" && (
                <div className="flex items-center space-x-2">
                  <Switch 
                    id="obrigatorio" 
                    checked={formData.obrigatorio} 
                    onCheckedChange={(v) => setFormData({ ...formData, obrigatorio: v })} 
                  />
                  <Label htmlFor="obrigatorio">Obrigatório</Label>
                </div>
              )}
            </div>
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button variant="outline" size="sm" className="rounded-sm border-primary text-primary hover:bg-primary/5" onClick={() => saveMutation.mutate(formData)}>
              <Save className="size-3.5 mr-1.5" />
              Salvar Item
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!itemToDelete}
        title="Excluir item?"
        description={itemToDelete ? `${itemToDelete.titulo ? `O item "${itemToDelete.titulo}"` : "Este item"} será removido permanentemente.` : undefined}
        confirmText="Excluir"
        destructive
        onCancel={() => setItemToDelete(null)}
        onConfirm={() => {
          if (!itemToDelete) return;
          deleteMutation.mutate(
            { subType: itemToDelete.subType, itemId: itemToDelete.itemId },
            { onSettled: () => setItemToDelete(null) }
          );
        }}
      />
    </div>
  );
}
