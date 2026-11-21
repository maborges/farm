"use client";

import { useState } from "react";
import Link from "next/link";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Beef, ClipboardList, Pencil, Plus, Save, Upload, XCircle } from "lucide-react";
import { toast } from "sonner";

import { LoteIndicadoresDrawer } from "@/components/pecuaria/lote-indicadores-drawer";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  createLote,
  fetchLotes,
  fetchPiquetesAtivos,
  type LoteBovino,
  type LoteBovinoCreate,
  type LoteBovinoUpdate,
  type ModoGestaoLote,
  updateLote,
} from "@/lib/pecuaria/lotes-api";
import { useAppStore } from "@/lib/stores/app-store";

const CATEGORIAS = [
  "Bezerros",
  "Bezerras",
  "Novilhas",
  "Novilhos",
  "Vacas",
  "Touros",
  "Matrizes",
  "Recria",
] as const;

const RACAS = [
  "Nelore",
  "Angus",
  "Brahman",
  "Gir",
  "Girolando",
  "Simental",
  "Brangus",
  "Mestiço",
  "Outros",
] as const;

type LoteFormState = {
  identificacao: string;
  modo_gestao: ModoGestaoLote;
  piquete_id: string;
  categoria: string;
  raca: string;
  quantidade_cabecas: string;
  peso_medio_kg: string;
  peso_inicial_medio_kg: string;
  rendimento_carcaca_pct: string;
  valor_aquisicao_total: string;
  cotacao_arroba_override: string;
  data_formacao: string;
};

function parseOptionalNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildInitialState(editingLote: LoteBovino | null): LoteFormState {
  if (!editingLote) {
    return {
      identificacao: "",
      modo_gestao: "POR_LOTE",
      piquete_id: "NONE",
      categoria: "",
      raca: "",
      quantidade_cabecas: "1",
      peso_medio_kg: "0",
      peso_inicial_medio_kg: "",
      rendimento_carcaca_pct: "50",
      valor_aquisicao_total: "",
      cotacao_arroba_override: "",
      data_formacao: new Date().toISOString().split("T")[0],
    };
  }
  return {
    identificacao: editingLote.identificacao,
    modo_gestao: (editingLote.modo_gestao === "INDIVIDUAL" ? "INDIVIDUAL" : "POR_LOTE"),
    piquete_id: editingLote.piquete_id ?? "NONE",
    categoria: editingLote.categoria ?? "",
    raca: editingLote.raca ?? "",
    quantidade_cabecas: String(editingLote.quantidade_cabecas ?? 0),
    peso_medio_kg: String(editingLote.peso_medio_kg ?? 0),
    peso_inicial_medio_kg:
      editingLote.peso_inicial_medio_kg != null ? String(editingLote.peso_inicial_medio_kg) : "",
    rendimento_carcaca_pct: String(editingLote.rendimento_carcaca_pct ?? 50),
    valor_aquisicao_total:
      editingLote.valor_aquisicao_total != null ? String(editingLote.valor_aquisicao_total) : "",
    cotacao_arroba_override:
      editingLote.cotacao_arroba_override != null
        ? String(editingLote.cotacao_arroba_override)
        : "",
    data_formacao: editingLote.data_formacao,
  };
}

function calcularArrobasEstimadas(lote: LoteBovino): number {
  const pesoTotal = (lote.quantidade_cabecas ?? 0) * (lote.peso_medio_kg ?? 0);
  const rendimento = lote.rendimento_carcaca_pct > 0 ? lote.rendimento_carcaca_pct : 50;
  return (pesoTotal * (rendimento / 100)) / 15;
}

const getCategoriaStyle = (categoria: string | null | undefined) => {
  switch ((categoria ?? "").toLowerCase()) {
    case "bezerros":
    case "bezerras":
      return "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400 border-blue-200 dark:border-blue-900/50";
    case "vacas":
    case "matrizes":
      return "bg-pink-50 text-pink-700 dark:bg-pink-950/50 dark:text-pink-400 border-pink-200 dark:border-pink-900/50";
    case "touros":
      return "bg-orange-50 text-orange-700 dark:bg-orange-950/50 dark:text-orange-400 border-orange-200 dark:border-orange-900/50";
    case "novilhas":
    case "novilhos":
    case "recria":
      return "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-400 border-purple-200 dark:border-purple-900/50";
    default:
      return "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700";
  }
};

function LoteFormModal({
  open,
  fazendaId,
  editingLote,
  onOpenChange,
}: {
  open: boolean;
  fazendaId: string;
  editingLote: LoteBovino | null;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<LoteFormState>(() => buildInitialState(editingLote));
  const unidadeQueryId = editingLote?.unidade_produtiva_id ?? fazendaId;

  const { data: piquetes = [] } = useQuery({
    queryKey: ["piquetes-ativos", unidadeQueryId],
    queryFn: () => fetchPiquetesAtivos(unidadeQueryId),
    enabled: open && Boolean(unidadeQueryId),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const piqueteId = form.piquete_id !== "NONE" ? form.piquete_id : null;
      const rendimento = Number(form.rendimento_carcaca_pct || 50);
      const qtd = Number(form.quantidade_cabecas || 0);
      const pesoMedio = Number(form.peso_medio_kg || 0);
      const pesoInicial = parseOptionalNumber(form.peso_inicial_medio_kg);
      const valorAquisicao = parseOptionalNumber(form.valor_aquisicao_total);
      const cotacaoOverride = parseOptionalNumber(form.cotacao_arroba_override);

      if (editingLote) {
        const payload: LoteBovinoUpdate = {
          identificacao: form.identificacao.trim(),
          modo_gestao: form.modo_gestao,
          piquete_id: piqueteId,
          categoria: form.categoria,
          raca: form.raca,
          quantidade_cabecas: qtd,
          peso_medio_kg: pesoMedio,
          peso_inicial_medio_kg: pesoInicial,
          rendimento_carcaca_pct: rendimento,
          valor_aquisicao_total: valorAquisicao,
          cotacao_arroba_override: cotacaoOverride,
        };
        return updateLote(editingLote.id, payload);
      }

      const payload: LoteBovinoCreate = {
        unidade_produtiva_id: fazendaId,
        piquete_id: piqueteId,
        identificacao: form.identificacao.trim(),
        modo_gestao: form.modo_gestao,
        categoria: form.categoria,
        raca: form.raca,
        quantidade_cabecas: qtd,
        peso_medio_kg: pesoMedio,
        peso_inicial_medio_kg: pesoInicial,
        rendimento_carcaca_pct: rendimento,
        valor_aquisicao_total: valorAquisicao,
        cotacao_arroba_override: cotacaoOverride,
        data_formacao: form.data_formacao,
      };
      return createLote(payload);
    },
    onSuccess: () => {
      toast.success(editingLote ? "Lote atualizado com sucesso!" : "Lote criado com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["lotes"] });
      queryClient.invalidateQueries({ queryKey: ["pecuaria"] });
      queryClient.invalidateQueries({ queryKey: ["pecuaria-resumo-economico"] });
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : "Erro ao salvar lote.";
      toast.error(message);
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!editingLote && !fazendaId) {
      toast.error("Selecione uma fazenda primeiro.");
      return;
    }
    if (!form.categoria || !form.raca) {
      toast.error("Informe categoria e raça do lote.");
      return;
    }
    saveMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl rounded-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <Beef className="size-4" />
            </div>
            {editingLote ? "Editar Lote Pecuário" : "Novo Lote Pecuário"}
          </DialogTitle>
          <DialogDescription>
            Configure o modo de controle (coletivo por lote ou individual), piquete e premissas da arroba.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <DialogBody className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="lote-ident" className="text-xs font-semibold text-muted-foreground uppercase">
                  Identificação do Lote *
                </label>
                <Input
                  id="lote-ident"
                  required
                  value={form.identificacao}
                  onChange={(e) => setForm((prev) => ({ ...prev, identificacao: e.target.value }))}
                  placeholder="Ex: Lote Engorda 01"
                  className="h-8 rounded-sm text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">
                  Modo de Gestão *
                </label>
                <Select
                  value={form.modo_gestao}
                  onValueChange={(value) =>
                    setForm((prev) => ({
                      ...prev,
                      modo_gestao: value === "INDIVIDUAL" ? "INDIVIDUAL" : "POR_LOTE",
                    }))
                  }
                >
                  <SelectTrigger className="h-8 rounded-sm text-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="POR_LOTE">Por Lote (Coletivo)</SelectItem>
                    <SelectItem value="INDIVIDUAL">Individual (Brincado)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">
                  Categoria *
                </label>
                <Select
                  value={form.categoria}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, categoria: value }))}
                >
                  <SelectTrigger className="h-8 rounded-sm text-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIAS.map((cat) => (
                      <SelectItem key={cat} value={cat}>
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">
                  Raça Principal *
                </label>
                <Select
                  value={form.raca}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, raca: value }))}
                >
                  <SelectTrigger className="h-8 rounded-sm text-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {RACAS.map((raca) => (
                      <SelectItem key={raca} value={raca}>
                        {raca}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">
                  Piquete / Pasto
                </label>
                <Select
                  value={form.piquete_id}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, piquete_id: value }))}
                >
                  <SelectTrigger className="h-8 rounded-sm text-sm">
                    <SelectValue placeholder="Nenhum piquete" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NONE">Sem piquete vinculado</SelectItem>
                    {piquetes.map((piq) => (
                      <SelectItem key={piq.id} value={piq.id}>
                        {piq.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="lote-cabecas" className="text-xs font-semibold text-muted-foreground uppercase">
                  Qtd. Cabeças *
                </label>
                <Input
                  id="lote-cabecas"
                  type="number"
                  required
                  min={form.modo_gestao === "POR_LOTE" ? 1 : 0}
                  value={form.quantidade_cabecas}
                  onChange={(e) => setForm((prev) => ({ ...prev, quantidade_cabecas: e.target.value }))}
                  className="h-8 rounded-sm text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="lote-peso" className="text-xs font-semibold text-muted-foreground uppercase">
                  Peso Médio Atual (kg)
                </label>
                <Input
                  id="lote-peso"
                  type="number"
                  min={0}
                  step="0.1"
                  value={form.peso_medio_kg}
                  onChange={(e) => setForm((prev) => ({ ...prev, peso_medio_kg: e.target.value }))}
                  className="h-8 rounded-sm text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="lote-peso-inicial" className="text-xs font-semibold text-muted-foreground uppercase">
                  Peso Inicial Médio (kg)
                </label>
                <Input
                  id="lote-peso-inicial"
                  type="number"
                  min={0}
                  step="0.1"
                  placeholder="Igual ao inicial"
                  value={form.peso_inicial_medio_kg}
                  onChange={(e) => setForm((prev) => ({ ...prev, peso_inicial_medio_kg: e.target.value }))}
                  className="h-8 rounded-sm text-sm"
                />
              </div>
            </div>

            <div className="border rounded-sm p-3 space-y-3 bg-muted/20">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Parâmetros Econômicos da Arroba
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label htmlFor="lote-rend" className="text-xs font-medium text-foreground">
                    Rendimento Carcaça (%)
                  </label>
                  <Input
                    id="lote-rend"
                    type="number"
                    min={30}
                    max={70}
                    step="0.5"
                    value={form.rendimento_carcaca_pct}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, rendimento_carcaca_pct: e.target.value }))
                    }
                    className="h-8 rounded-sm text-sm"
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="lote-aquisicao" className="text-xs font-medium text-foreground">
                    Valor Aquisição Total (R$)
                  </label>
                  <Input
                    id="lote-aquisicao"
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Opcional"
                    value={form.valor_aquisicao_total}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, valor_aquisicao_total: e.target.value }))
                    }
                    className="h-8 rounded-sm text-sm"
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="lote-cotacao" className="text-xs font-medium text-foreground">
                    Cotação Manual (R$/@)
                  </label>
                  <Input
                    id="lote-cotacao"
                    type="number"
                    min={0.01}
                    step="0.01"
                    placeholder="Padrão DERAL/SEAB"
                    value={form.cotacao_arroba_override}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, cotacao_arroba_override: e.target.value }))
                    }
                    className="h-8 rounded-sm text-sm"
                  />
                </div>
              </div>
            </div>

            {!editingLote && (
              <div className="space-y-1.5 max-w-xs">
                <label htmlFor="lote-data" className="text-xs font-semibold text-muted-foreground uppercase">
                  Data de Formação
                </label>
                <Input
                  id="lote-data"
                  type="date"
                  value={form.data_formacao}
                  onChange={(e) => setForm((prev) => ({ ...prev, data_formacao: e.target.value }))}
                  className="h-8 rounded-sm text-sm"
                />
              </div>
            )}
          </DialogBody>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => onOpenChange(false)}
            >
              <XCircle className="size-4 mr-1.5" />
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="outline"
              size="sm"
              className="rounded-sm"
              disabled={saveMutation.isPending}
            >
              <Save className="size-4 mr-1.5" />
              {saveMutation.isPending ? "Salvando..." : editingLote ? "Salvar Alterações" : "Criar Lote"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function LotesBovinosPage() {
  const { activeFazendaId, isVisaoGrupo } = useAppStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingLote, setEditingLote] = useState<LoteBovino | null>(null);
  const [selectedLoteIndicadores, setSelectedLoteIndicadores] = useState<LoteBovino | null>(null);

  const { data: lotes = [] } = useQuery({
    queryKey: ["lotes", activeFazendaId, isVisaoGrupo],
    queryFn: () => fetchLotes(isVisaoGrupo ? null : activeFazendaId),
    enabled: isVisaoGrupo || !!activeFazendaId,
  });

  const columns: ColumnDef<LoteBovino>[] = [
    {
      id: "categoria",
      header: "Categoria",
      accessorKey: "categoria",
      cell: (value) => (
        <Badge className={`inline-flex items-center shadow-sm rounded-sm ${getCategoriaStyle(value)}`} variant="outline">
          {value || "Sem categoria"}
        </Badge>
      ),
      sortable: true,
      filterable: true,
      filterPlaceholder: "Filtrar categoria...",
      exportFormat: (value) => value || "",
    },
    {
      id: "identificacao",
      header: "Identificação",
      accessorKey: "identificacao",
      cell: (value, row) => (
        <div>
          <p className="font-semibold text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground mt-0.5">Raça: {row.raca || "—"}</p>
        </div>
      ),
      sortable: true,
      filterable: true,
      filterPlaceholder: "Filtrar identificação...",
      exportFormat: (value, row) => `${value} (${row.raca || ""})`,
    },
    {
      id: "modo_gestao",
      header: "Modo",
      accessorKey: "modo_gestao",
      cell: (value) => (
        <Badge variant={value === "INDIVIDUAL" ? "default" : "secondary"} className="rounded-sm">
          {value === "INDIVIDUAL" ? "Individual" : "Por Lote"}
        </Badge>
      ),
      sortable: true,
      exportFormat: (value) => (value === "INDIVIDUAL" ? "Individual" : "Por Lote"),
    },
    {
      id: "quantidade_cabecas",
      header: "Cabeças",
      accessorKey: "quantidade_cabecas",
      cell: (value) => <span className="font-bold text-foreground text-right block tabular-nums">{value}</span>,
      sortable: true,
      exportFormat: (value) => value?.toString() || "0",
    },
    {
      id: "peso_medio_kg",
      header: "Peso Médio",
      accessorKey: "peso_medio_kg",
      cell: (value) => (
        <span className="text-muted-foreground text-right block tabular-nums">
          {Number(value ?? 0).toFixed(1)} kg
        </span>
      ),
      sortable: true,
      exportFormat: (value) => (value ? `${Number(value).toFixed(1)} kg` : "-"),
    },
    {
      id: "arrobas_estimadas",
      header: "@ Estimadas",
      accessorFn: (row) => calcularArrobasEstimadas(row),
      cell: (_, row) => (
        <span className="text-foreground font-medium text-right block tabular-nums">
          {calcularArrobasEstimadas(row).toFixed(1)} @
        </span>
      ),
      sortable: true,
      exportFormat: (_, row) => `${calcularArrobasEstimadas(row).toFixed(1)} @`,
    },
    {
      id: "data_formacao",
      header: "Fundação",
      accessorKey: "data_formacao",
      cell: (value) => (
        <span className="text-muted-foreground text-right block tabular-nums">
          {new Date(value).toLocaleDateString("pt-BR")}
        </span>
      ),
      sortable: true,
      exportFormat: (value) => new Date(value).toLocaleDateString("pt-BR"),
    },
    {
      id: "acoes",
      header: "",
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-sm text-primary hover:text-primary hover:bg-primary/10"
            title="Editar lote"
            onClick={(event) => {
              event.stopPropagation();
              setEditingLote(row);
              setModalOpen(true);
            }}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/40"
            title="Indicadores do lote"
            onClick={(event) => {
              event.stopPropagation();
              setSelectedLoteIndicadores(row);
            }}
          >
            <BarChart3 className="size-3.5" />
          </Button>
        </div>
      ),
      sortable: false,
      filterable: false,
      exportable: false,
      isActionColumn: true,
    },
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-200">
      <PageHeader
        title="Lotes"
        description="Gerencie rebanhos por saldo coletivo ou controle individual, rendimentos e custo por arroba."
        icon={<ClipboardList size={22} className="text-primary" />}
        breadcrumbs={[
          { label: "Pecuária", href: "/dashboard/pecuaria" },
          { label: "Lotes" },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild size="sm" variant="outline" className="rounded-sm">
              <Link href="/dashboard/pecuaria/importar?tipo=LOTES">
                <Upload className="size-3.5 mr-1.5" />
                Importar Planilha
              </Link>
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="rounded-sm"
              onClick={() => {
                if (!activeFazendaId) {
                  toast.error("Selecione uma fazenda para adicionar lotes.");
                  return;
                }
                setEditingLote(null);
                setModalOpen(true);
              }}
            >
              <Plus className="size-3.5 mr-1.5" />
              Novo Lote
            </Button>
          </div>
        }
      />

      <Card className="shadow-sm rounded-sm">
        <CardHeader className="border-b">
          <CardTitle>Lista de Lotes</CardTitle>
          <CardDescription>
            Consulte, edite e acompanhe o desempenho zootécnico e econômico dos lotes.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <DataTable
            data={lotes}
            columns={columns}
            searchable
            searchPlaceholder="Buscar por identificação, raça ou categoria..."
            exportable
            exportFileName="lotes-bovinos"
            emptyMessage="Nenhum lote registrado nesta fazenda."
          />
        </CardContent>
      </Card>

      {modalOpen && (activeFazendaId || editingLote) && (
        <LoteFormModal
          key={editingLote?.id ?? "novo"}
          open={modalOpen}
          fazendaId={activeFazendaId ?? editingLote?.unidade_produtiva_id ?? ""}
          editingLote={editingLote}
          onOpenChange={(open) => {
            setModalOpen(open);
            if (!open) setEditingLote(null);
          }}
        />
      )}

      <LoteIndicadoresDrawer
        open={Boolean(selectedLoteIndicadores)}
        loteId={selectedLoteIndicadores?.id ?? null}
        loteNome={selectedLoteIndicadores?.identificacao ?? null}
        onOpenChange={(open) => {
          if (!open) setSelectedLoteIndicadores(null);
        }}
      />
    </div>
  );
}
