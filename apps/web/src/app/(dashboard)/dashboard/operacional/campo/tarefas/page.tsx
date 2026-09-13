"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { TarefaDrawer, type TarefaProgramada } from "@/components/campo/tarefa-drawer";
import { Plus, Eye, Pencil, Ban, ClipboardList, XCircle } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MultiSelectFilter } from "@/components/shared/multi-select-filter";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const STATUS_EXECUCAO_LABEL: Record<string, string> = {
  PENDENTE: "Pendente",
  EM_EXECUCAO: "Em Execução",
  CONCLUIDA: "Concluída",
  CANCELADA: "Cancelada",
  INVALIDADA: "Invalidada",
};

const FASE_LABEL: Record<string, string> = {
  PLANEJADA: "Planejamento",
  PREPARO_SOLO: "Preparo do Solo",
  PLANTIO: "Plantio",
  DESENVOLVIMENTO: "Desenvolvimento",
  COLHEITA: "Colheita",
  POS_COLHEITA: "Pós-Colheita",
  ENCERRADA: "Encerrada",
};

interface Safra {
  id: string;
  ano_safra: string;
  cultura: string | null;
}

interface AreaRural {
  id: string;
  nome: string;
}

const PRIORIDADE_STYLES: Record<string, string> = {
  URGENTE: "bg-red-500/10 text-red-600 border-red-500/20",
  ALTA: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  NORMAL: "bg-slate-500/10 text-slate-600 border-slate-500/20",
  BAIXA: "bg-slate-100 text-slate-400 border-slate-200",
};

const TIPO_LABEL: Record<string, string> = {
  APLICACAO_DEFENSIVO: "Aplicação de Defensivo",
  APLICACAO_FERTILIZANTE: "Aplicação de Fertilizante",
  COLHEITA_REGISTRO: "Colheita",
  PLANTIO_REGISTRO: "Plantio",
  IRRIGACAO_EVENTO: "Irrigação",
  MONITORAMENTO_PRAGA: "Monitoramento de Praga",
  AMOSTRAGEM_SOLO: "Amostragem de Solo",
  PREPARO_SOLO: "Preparo de Solo",
  OPERACAO_MECANIZADA: "Operação Mecanizada",
  OUTROS_AGRICOLA: "Outros",
  PESAGEM_ANIMAL: "Pesagem de Animal",
  VACINACAO_LOTE: "Vacinação de Lote",
  MEDICACAO_ANIMAL: "Medicação Animal",
  MOVIMENTACAO_LOTE: "Movimentação de Lote",
  PARTO_REGISTRO: "Registro de Parto",
  INSEMINACAO: "Inseminação",
};

export default function TarefasCampoPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"create" | "edit" | "view">("create");
  const [selectedTask, setSelectedTask] = useState<TarefaProgramada | null>(null);
  const [taskToCancel, setTaskToCancel] = useState<TarefaProgramada | null>(null);
  const [taskToInvalidate, setTaskToInvalidate] = useState<TarefaProgramada | null>(null);
  const [motivoInvalidacao, setMotivoInvalidacao] = useState("");
  const [safraId, setSafraId] = useState<string>("");
  const [talhaoFilter, setTalhaoFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [faseFilter, setFaseFilter] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const { data: safras = [] } = useQuery<Safra[]>({
    queryKey: ["safras"],
    queryFn: () => apiFetch("/safras"),
  });

  const { data: areas = [] } = useQuery<AreaRural[]>({
    queryKey: ["areas-rurais-talhoes"],
    queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
  });
  const nomeTalhao = (id: string | null) => areas.find((a) => a.id === id)?.nome;

  const { data: tarefas = [], isLoading } = useQuery<TarefaProgramada[]>({
    queryKey: ["campo-tarefas", safraId],
    queryFn: () =>
      apiFetch(`/campo/tarefas?limit=500${safraId ? `&safra_id=${safraId}` : ""}`),
  });

  const tarefasFiltradas = tarefas.filter((t) => {
    const matchTalhao = talhaoFilter.length === 0 || (t.area_rural_id && talhaoFilter.includes(t.area_rural_id));
    const matchStatus = statusFilter.length === 0 || statusFilter.includes(t.status_execucao);
    const matchFase = faseFilter.length === 0 || (t.fase && faseFilter.includes(t.fase));
    return matchTalhao && matchStatus && matchFase;
  });

  const hoje = new Date().toISOString().slice(0, 10);

  const cancelMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/campo/tarefas/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campo-tarefas"] });
      setTaskToCancel(null);
      toast.success("Tarefa cancelada.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const invalidateMut = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiFetch(`/campo/tarefas/${id}/invalidar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campo-tarefas"] });
      setTaskToInvalidate(null);
      setMotivoInvalidacao("");
      toast.success("Tarefa invalidada com histórico preservado.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const columns: ColumnDef<TarefaProgramada>[] = [
    {
      id: "titulo",
      header: "Atividade",
      accessorFn: (row) => row.titulo ?? TIPO_LABEL[row.type] ?? row.type,
      cell: (value, row) => {
        const talhao = nomeTalhao(row.area_rural_id);
        return (
          <div className="flex flex-col">
            <span className="font-medium text-sm">{value}</span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              {row.module === "agricola" ? "Agrícola" : "Pecuária"}
              {talhao && (
                <>
                  <span className="text-muted-foreground/50">·</span>
                  <span className="normal-case">{talhao}</span>
                </>
              )}
              {row.fase && (
                <>
                  <span className="text-muted-foreground/50">·</span>
                  <span className="normal-case">{FASE_LABEL[row.fase] ?? row.fase}</span>
                </>
              )}
            </span>
          </div>
        );
      },
    },
    {
      id: "data_programada",
      header: "Data Programada",
      accessorKey: "data_programada",
      cell: (value, row) => {
        if (!value) return <span className="text-muted-foreground">Sem data</span>;
        const isAtrasada = value < hoje && row.status_execucao === "PENDENTE";
        return (
          <span className={cn(
            "text-sm",
            isAtrasada ? "text-orange-600 font-semibold" : "text-foreground"
          )}>
            {new Date(value + "T00:00:00").toLocaleDateString("pt-BR")}
            {isAtrasada && " (Atrasada)"}
          </span>
        );
      },
    },
    {
      id: "prioridade",
      header: "Prioridade",
      accessorKey: "prioridade",
      cell: (value) => (
        <Badge variant="outline" className={cn("rounded-sm font-medium", PRIORIDADE_STYLES[value] ?? "")}>
          {value}
        </Badge>
      ),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status_execucao",
      cell: (value) => <WorkflowStatusBadge status={value} />,
    },
    {
      id: "observacoes",
      header: "Observações",
      accessorFn: (row) =>
        String(row.dados?.obs_execucao ?? row.dados?.obs ?? row.dados?.observacao ?? ""),
      cell: (value) =>
        value ? (
          <span className="line-clamp-2 max-w-[280px] text-xs text-muted-foreground">{value}</span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      id: "imagens",
      header: "Imagens",
      accessorFn: (row) => row.fotos ?? [],
      sortable: false,
      cell: (value: string[]) =>
        value.length > 0 ? (
          <div className="flex items-center gap-2">
            {value.slice(0, 2).map((foto, index) => (
              <img
                key={`thumb-${index}`}
                src={foto}
                alt={`Imagem ${index + 1}`}
                className="h-10 w-10 rounded-sm border object-cover"
              />
            ))}
            <span className="text-xs text-muted-foreground">{value.length} foto(s)</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => {
        const canCancel = row.status_execucao === "PENDENTE" || row.status_execucao === "EM_EXECUCAO";
        const canInvalidate = row.status_execucao === "CONCLUIDA";

        return (
        <div className="flex items-center gap-0 justify-end">
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-10 rounded-sm text-muted-foreground hover:text-primary active:scale-[0.98] transition-transform"
            title="Visualizar"
            onClick={() => {
              setSelectedTask(row);
              setDrawerMode("view");
              setDrawerOpen(true);
            }}
          >
            <Eye className="size-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-10 rounded-sm text-muted-foreground hover:text-primary active:scale-[0.98] transition-transform"
            title="Editar"
            disabled={row.status_execucao !== "PENDENTE"}
            onClick={() => {
              setSelectedTask(row);
              setDrawerMode("edit");
              setDrawerOpen(true);
            }}
            >
              <Pencil className="size-4" />
            </Button>
          {canCancel && (
              <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-10 rounded-sm text-muted-foreground hover:text-destructive active:scale-[0.98] transition-transform"
              title="Cancelar"
              disabled={cancelMut.isPending}
              onClick={() => {
                setTaskToCancel(row);
              }}
            >
              <Ban className="size-4" />
            </Button>
          )}
          {canInvalidate && (
              <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-10 rounded-sm text-muted-foreground hover:text-violet-700 active:scale-[0.98] transition-transform"
              title="Invalidar"
              disabled={invalidateMut.isPending}
              onClick={() => setTaskToInvalidate(row)}
            >
              <XCircle className="size-4" />
            </Button>
          )}
        </div>
        );
      },
    },
  ];

  return (
    <div className="p-4 md:p-8 space-y-6">
      <PageHeader
        title="Tarefas de Campo"
        description="Planeje e acompanhe as atividades dos operadores"
        icon={<ClipboardList className="size-5 text-primary" />}
        breadcrumbs={[
          { label: "Operacional", href: "/dashboard/operacional" },
          { label: "Campo", href: "/dashboard/operacional/campo/tarefas" },
          { label: "Tarefas" },
        ]}
        actions={
          <div className="flex w-full flex-wrap items-center gap-2">
            <Select value={safraId || "all"} onValueChange={(v) => setSafraId(v === "all" ? "" : v)}>
              <SelectTrigger className="h-9 w-full sm:w-[200px]">
                <SelectValue placeholder="Todas as safras" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as safras</SelectItem>
                {safras.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.ano_safra}
                    {s.cultura ? ` · ${s.cultura}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <MultiSelectFilter
              label="Talhão"
              options={areas.map((a) => ({ value: a.id, label: a.nome }))}
              selected={talhaoFilter}
              onChange={setTalhaoFilter}
            />
            <MultiSelectFilter
              label="Status"
              options={Object.entries(STATUS_EXECUCAO_LABEL).map(([value, label]) => ({ value, label }))}
              selected={statusFilter}
              onChange={setStatusFilter}
            />
            <MultiSelectFilter
              label="Fase"
              options={Object.entries(FASE_LABEL).map(([value, label]) => ({ value, label }))}
              selected={faseFilter}
              onChange={setFaseFilter}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedTask(null);
                setDrawerMode("create");
                setDrawerOpen(true);
              }}
              className="w-full gap-2 rounded-sm sm:w-auto"
            >
              <Plus className="size-4" />
              Nova Tarefa
            </Button>
          </div>
        }
      />

      <div className="overflow-hidden rounded-sm border border-border/50 bg-card shadow-premium">
        <DataTable
          data={tarefasFiltradas}
          columns={columns}
          isLoading={isLoading}
          exportFileName="tarefas-campo"
          searchPlaceholder="Buscar atividade..."
        />
      </div>

      <TarefaDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        mode={drawerMode}
        tarefa={selectedTask}
      />

      <AlertDialog open={!!taskToCancel} onOpenChange={(open) => !open && setTaskToCancel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar tarefa</AlertDialogTitle>
            <AlertDialogDescription>
              Informe apenas se a tarefa ainda não gerou fato operacional e precisa ser cancelada.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setTaskToCancel(null)}>
              Voltar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!taskToCancel) return;
                cancelMut.mutate(taskToCancel.id);
                setTaskToCancel(null);
              }}
              disabled={!taskToCancel || taskToCancel.status_execucao === "CONCLUIDA" || taskToCancel.status_execucao === "CANCELADA"}
            >
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!taskToInvalidate} onOpenChange={(open) => !open && setTaskToInvalidate(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Invalidar tarefa</AlertDialogTitle>
            <AlertDialogDescription>
              Esta tarefa já integra o histórico operacional da safra. Correções devem ocorrer por invalidação, retificação ou reprocessamento.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="motivo-invalidacao">
              Motivo *
            </label>
            <Textarea
              id="motivo-invalidacao"
              value={motivoInvalidacao}
              onChange={(event) => setMotivoInvalidacao(event.target.value)}
              placeholder="Aplicação registrada incorretamente..."
              rows={3}
              className="resize-none"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setTaskToInvalidate(null);
                setMotivoInvalidacao("");
              }}
            >
              Voltar
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={!motivoInvalidacao.trim() || invalidateMut.isPending}
              onClick={() => {
                if (!taskToInvalidate) return;
                invalidateMut.mutate({ id: taskToInvalidate.id, motivo: motivoInvalidacao });
              }}
            >
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
