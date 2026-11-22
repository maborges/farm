"use client";

import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Layers, Loader2, MapPin, Pencil, RotateCcw, Save, TrendingDown, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
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
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

type OrigemCotacao = "FAZENDA" | "TENANT" | "OFICIAL_UF" | "PARCEIRO_UF" | "DERAL" | "INDISPONIVEL";
type EscopoRegional = "FAZENDA" | "TENANT";
type ModoConsolidacao = "FONTE_SELECIONADA" | "MEDIA_FONTES";

interface PracaDeralResumoItem {
  praca: string;
  valor: number;
  registro_original: string;
}

type EscopoComparativoFonte =
  | "FAZENDA"
  | "TENANT"
  | "OFICIAL_UF"
  | "PARCEIRO_UF"
  | "DERAL_NUCLEO"
  | "DERAL_MEDIA";

interface FonteComparadaRegionalItem {
  escopo: EscopoComparativoFonte;
  fonte: string;
  praca: string;
  valor: number;
  data_referencia?: string | null;
  diferenca_para_media_pct?: number | null;
}

interface CotacaoRegionalHistoricoItem {
  valor: number;
  data_referencia: string;
  praca: string;
  fonte: string;
  escopo: EscopoRegional;
  registrado_em: string;
}

interface CotacaoRegionalItem {
  codigo: string;
  commodity_id_publico: string;
  nome: string;
  unidade: string;
  origem_efetiva: OrigemCotacao;
  modo_consolidacao?: ModoConsolidacao;
  valor_efetivo: number | null;
  data_referencia_efetiva: string | null;
  praca_efetiva: string | null;
  fonte_efetiva: string | null;
  valor_fazenda: number | null;
  data_fazenda: string | null;
  praca_fazenda: string | null;
  fonte_fazenda: string | null;
  valor_tenant: number | null;
  data_tenant: string | null;
  praca_tenant: string | null;
  fonte_tenant: string | null;
  valor_deral: number | null;
  data_deral: string | null;
  praca_deral: string | null;
  variacao_semanal_deral_pct?: number | null;
  diferenca_deral_brl?: number | null;
  diferenca_deral_pct?: number | null;
  valor_minimo_regional_deral?: number | null;
  praca_minimo_regional_deral?: string | null;
  valor_maximo_regional_deral?: number | null;
  praca_maximo_regional_deral?: string | null;
  total_fontes_ativas?: number;
  valor_minimo_fontes?: number | null;
  valor_medio_fontes?: number | null;
  valor_maximo_fontes?: number | null;
  dispersao_fontes_pct?: number | null;
  fontes_comparadas?: FonteComparadaRegionalItem[];
  pracas_deral_disponiveis?: PracaDeralResumoItem[];
  historico_recente?: CotacaoRegionalHistoricoItem[];
}

const cotacaoRegionalSchema = z.object({
  valor: z.number({ error: "Informe um valor válido" }).positive("Preço deve ser maior que zero"),
  data_referencia: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Use o formato YYYY-MM-DD"),
  praca: z.string().trim().min(2, "Informe a praça regional").max(120, "Máximo de 120 caracteres"),
  fonte: z.string().trim().max(120, "Máximo de 120 caracteres").optional(),
  escopo: z.enum(["FAZENDA", "TENANT"]),
  modo_consolidacao: z.enum(["FONTE_SELECIONADA", "MEDIA_FONTES"]),
  observacoes: z.string().trim().max(300, "Máximo de 300 caracteres").optional(),
});

type CotacaoRegionalFormValues = z.infer<typeof cotacaoRegionalSchema>;

const ORIGEM_STYLES: Record<OrigemCotacao, string> = {
  FAZENDA:
    "bg-emerald-500/10 text-emerald-700 border-emerald-500/25 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-400/30",
  TENANT:
    "bg-amber-500/10 text-amber-700 border-amber-500/25 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-400/30",
  OFICIAL_UF:
    "bg-sky-500/10 text-sky-700 border-sky-500/25 dark:bg-sky-500/20 dark:text-sky-300 dark:border-sky-400/30",
  PARCEIRO_UF:
    "bg-teal-500/10 text-teal-700 border-teal-500/25 dark:bg-teal-500/20 dark:text-teal-300 dark:border-teal-400/30",
  DERAL: "bg-muted text-muted-foreground border-border dark:bg-zinc-800/80 dark:text-zinc-300 dark:border-zinc-700",
  INDISPONIVEL:
    "bg-destructive/10 text-destructive border-destructive/25 dark:bg-red-500/20 dark:text-red-300 dark:border-red-400/30",
};

const ORIGEM_LABELS: Record<OrigemCotacao, string> = {
  FAZENDA: "Fazenda Ativa",
  TENANT: "Grupo/Tenant",
  OFICIAL_UF: "Órgão Estadual UF",
  PARCEIRO_UF: "Parceiro Autorizado",
  DERAL: "DERAL/SEAB-PR",
  INDISPONIVEL: "Indisponível",
};

function formatarMoeda(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarPercentual(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  const sinal = valor > 0 ? "+" : "";
  return `${sinal}${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

export function CotacoesRegionaisSection() {
  const queryClient = useQueryClient();
  const activeFazendaId = useAppStore((s) => s.activeFazendaId);
  const isVisaoGrupo = useAppStore((s) => s.isVisaoGrupo);
  const unidades = useAppStore((s) => s.unidadesProdutivasAutorizadas);

  const fazendaAtiva = useMemo(
    () => unidades.find((u) => u.id === activeFazendaId) ?? null,
    [unidades, activeFazendaId]
  );

  const podeEditarFazenda = Boolean(activeFazendaId && !isVisaoGrupo);

  const [filtroFonte, setFiltroFonte] = useState<string>("TODAS");
  const [filtroPracaDeral, setFiltroPracaDeral] = useState<string>("PADRAO");
  const [editingItem, setEditingItem] = useState<CotacaoRegionalItem | null>(null);
  const [confirmRestore, setConfirmRestore] = useState<{
    item: CotacaoRegionalItem;
    escopo: EscopoRegional;
  } | null>(null);

  const { data: referencias, isLoading } = useQuery<CotacaoRegionalItem[]>({
    queryKey: ["cadastros-cotacoes-regionais", activeFazendaId, isVisaoGrupo],
    queryFn: () =>
      apiFetch<CotacaoRegionalItem[]>("/cadastros/commodities/cotacoes-regionais", {
        params: podeEditarFazenda && activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
  });

  const pracasDeralCatalogadas = useMemo(() => {
    const conjunto = new Set<string>();
    for (const item of referencias ?? []) {
      for (const p of item.pracas_deral_disponiveis ?? []) {
        if (p.praca) conjunto.add(p.praca);
      }
    }
    return Array.from(conjunto).sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [referencias]);

  const dadosFiltrados = useMemo(() => {
    const lista = referencias ?? [];
    if (filtroFonte === "TODAS") return lista;
    return lista.filter((item) => {
      if (filtroFonte === "REGIONAL_LOCAL") {
        return item.origem_efetiva === "FAZENDA" || item.origem_efetiva === "TENANT";
      }
      if (filtroFonte === "MULTI_FONTE") {
        return (item.total_fontes_ativas ?? 0) > 1;
      }
      return item.origem_efetiva === filtroFonte;
    });
  }, [referencias, filtroFonte]);

  const form = useForm<CotacaoRegionalFormValues>({
    resolver: zodResolver(cotacaoRegionalSchema),
    defaultValues: {
      valor: 0,
      data_referencia: new Date().toISOString().slice(0, 10),
      praca: "",
      fonte: "",
      escopo: podeEditarFazenda ? "FAZENDA" : "TENANT",
      modo_consolidacao: "FONTE_SELECIONADA",
      observacoes: "",
    },
  });

  const salvarMutation = useMutation({
    mutationFn: async (values: CotacaoRegionalFormValues) => {
      if (!editingItem) throw new Error("Nenhuma commodity selecionada.");
      const escopoEfetivo: EscopoRegional =
        values.escopo === "FAZENDA" && podeEditarFazenda ? "FAZENDA" : "TENANT";
      return apiFetch<CotacaoRegionalItem>(
        `/cadastros/commodities/cotacoes-regionais/${editingItem.codigo}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            valor: values.valor,
            data_referencia: values.data_referencia,
            praca: values.praca,
            fonte: values.fonte || "Cotação Regional",
            escopo: escopoEfetivo,
            modo_consolidacao: values.modo_consolidacao,
            unidade_produtiva_id: escopoEfetivo === "FAZENDA" ? activeFazendaId : null,
            observacoes: values.observacoes || null,
          }),
        }
      );
    },
    onSuccess: (res) => {
      toast.success(`Cotação regional de ${res.nome} atualizada (${res.total_fontes_ativas ?? 1} fontes comparadas).`);
      setEditingItem(null);
      queryClient.invalidateQueries({ queryKey: ["cadastros-cotacoes-regionais"] });
    },
    onError: (err: Error) => {
      toast.error(`Erro ao salvar cotação regional: ${err.message}`);
    },
  });

  const removerMutation = useMutation({
    mutationFn: async (target: { codigo: string; escopo: EscopoRegional }) => {
      return apiFetch<void>(`/cadastros/commodities/cotacoes-regionais/${target.codigo}`, {
        method: "DELETE",
        params: {
          escopo: target.escopo,
          unidade_produtiva_id: target.escopo === "FAZENDA" ? activeFazendaId : undefined,
        },
      });
    },
    onSuccess: () => {
      toast.success("Override regional removido; herança restaurada.");
      setConfirmRestore(null);
      queryClient.invalidateQueries({ queryKey: ["cadastros-cotacoes-regionais"] });
    },
    onError: (err: Error) => {
      toast.error(`Falha ao restaurar referência: ${err.message}`);
    },
  });

  const abrirEdicao = (item: CotacaoRegionalItem) => {
    const escopoInicial: EscopoRegional =
      item.valor_fazenda !== null && podeEditarFazenda
        ? "FAZENDA"
        : item.valor_tenant !== null
          ? "TENANT"
          : podeEditarFazenda
            ? "FAZENDA"
            : "TENANT";
    const nucleoFiltro =
      filtroPracaDeral !== "PADRAO"
        ? item.pracas_deral_disponiveis?.find((p) => p.praca === filtroPracaDeral)
        : null;
    form.reset({
      valor: item.valor_fazenda ?? item.valor_tenant ?? nucleoFiltro?.valor ?? item.valor_deral ?? 0,
      data_referencia:
        item.data_fazenda ?? item.data_tenant ?? item.data_deral ?? new Date().toISOString().slice(0, 10),
      praca:
        item.praca_fazenda ??
        item.praca_tenant ??
        (nucleoFiltro ? `${nucleoFiltro.praca}/PR` : fazendaAtiva?.municipio ?? ""),
      fonte:
        item.fonte_fazenda ??
        item.fonte_tenant ??
        (nucleoFiltro ? `DERAL/SEAB-PR (${nucleoFiltro.registro_original})` : "Cooperativa / Praça Local"),
      escopo: escopoInicial,
      modo_consolidacao: item.modo_consolidacao ?? "FONTE_SELECIONADA",
      observacoes: "",
    });
    setEditingItem(item);
  };

  const aplicarNucleoDeral = (pracaNome: string) => {
    const nucleo = editingItem?.pracas_deral_disponiveis?.find((p) => p.praca === pracaNome);
    if (!nucleo) return;
    form.setValue("valor", nucleo.valor, { shouldValidate: true });
    form.setValue("praca", `${nucleo.praca}/PR`, { shouldValidate: true });
    form.setValue("fonte", `DERAL/SEAB-PR (${nucleo.registro_original})`, { shouldValidate: true });
    if (editingItem?.data_deral) {
      form.setValue("data_referencia", editingItem.data_deral, { shouldValidate: true });
    }
    toast.info(`Valores do Núcleo Regional ${nucleo.praca} aplicados ao formulário.`);
  };

  const columns: ColumnDef<CotacaoRegionalItem>[] = [
    {
      id: "commodity",
      header: "Commodity",
      accessorKey: "nome",
      sortable: true,
      cell: (_value, row) => (
        <div>
          <p className="font-medium text-sm">{row.nome}</p>
          <p className="text-xs text-muted-foreground font-mono">{row.codigo}</p>
        </div>
      ),
    },
    {
      id: "unidade",
      header: "Unidade",
      accessorKey: "unidade",
      sortable: true,
    },
    {
      id: "origem",
      header: "Origem Ativa",
      accessorKey: "origem_efetiva",
      sortable: true,
      filterable: true,
      cell: (_value, row) => (
        <div className="space-y-0.5">
          <Badge variant="outline" className={cn("rounded-sm text-xs", ORIGEM_STYLES[row.origem_efetiva])}>
            {ORIGEM_LABELS[row.origem_efetiva]}
          </Badge>
          {row.modo_consolidacao === "MEDIA_FONTES" && (
            <p className="text-[10px] text-emerald-700 dark:text-emerald-300 font-medium">
              Média entre fontes
            </p>
          )}
        </div>
      ),
    },
    {
      id: "valor_efetivo",
      header: "Preço Efetivo",
      accessorKey: "valor_efetivo",
      sortable: true,
      cell: (_value, row) => {
        const nucleoSimulado =
          filtroPracaDeral !== "PADRAO" && row.origem_efetiva === "DERAL"
            ? row.pracas_deral_disponiveis?.find((p) => p.praca === filtroPracaDeral)
            : null;
        const val = nucleoSimulado ? nucleoSimulado.valor : row.valor_efetivo;
        return (
          <div>
            <span className="font-semibold tabular-nums">{formatarMoeda(val)}</span>
            {nucleoSimulado && (
              <p className="text-[10px] text-emerald-700 dark:text-emerald-300">
                Núcleo {nucleoSimulado.praca}
              </p>
            )}
          </div>
        );
      },
      exportFormat: (value) => formatarMoeda(typeof value === "number" ? value : null),
    },
    {
      id: "painel_fontes",
      header: "Fontes & Faixa Regional (Mín / Média / Máx)",
      accessorFn: (row) =>
        `${row.total_fontes_ativas ?? 0} fontes · Mín ${formatarMoeda(row.valor_minimo_fontes)} · Média ${formatarMoeda(row.valor_medio_fontes)} · Máx ${formatarMoeda(row.valor_maximo_fontes)}`,
      cell: (_value, row) => {
        const qtd = row.total_fontes_ativas ?? row.fontes_comparadas?.length ?? 0;
        if (qtd === 0) return <span className="text-xs text-muted-foreground">—</span>;
        return (
          <div className="text-xs space-y-0.5">
            <div className="flex flex-wrap items-center gap-1">
              <Badge variant="outline" className="rounded-sm text-[10px] px-1.5 py-0">
                {qtd} {qtd === 1 ? "fonte" : "fontes"}
              </Badge>
              <span className="tabular-nums text-[11px] text-foreground">
                Média: <strong>{formatarMoeda(row.valor_medio_fontes)}</strong>
              </span>
              {typeof row.dispersao_fontes_pct === "number" && row.dispersao_fontes_pct > 0 && (
                <span className="text-[10px] text-muted-foreground">
                  (Δ {row.dispersao_fontes_pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%)
                </span>
              )}
            </div>
            {row.valor_minimo_fontes !== null && row.valor_maximo_fontes !== null && qtd > 1 && (
              <p className="text-[10px] text-muted-foreground tabular-nums">
                Mín: {formatarMoeda(row.valor_minimo_fontes)} · Máx: {formatarMoeda(row.valor_maximo_fontes)}
              </p>
            )}
          </div>
        );
      },
    },
    {
      id: "spread_deral",
      header: "Spread vs. DERAL",
      accessorKey: "diferenca_deral_pct",
      sortable: true,
      cell: (_value, row) => {
        if (row.diferenca_deral_pct === null || row.diferenca_deral_pct === undefined) {
          return <span className="text-xs text-muted-foreground">—</span>;
        }
        if (row.origem_efetiva === "DERAL" || Math.abs(row.diferenca_deral_pct) < 0.01) {
          return <span className="text-xs text-muted-foreground">Paridade DERAL (0,00%)</span>;
        }
        const positivo = row.diferenca_deral_pct > 0;
        const diffBrl = row.diferenca_deral_brl ?? 0;
        return (
          <div className="text-xs">
            <span
              className={cn(
                "inline-flex items-center gap-1 font-semibold tabular-nums",
                positivo ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"
              )}
            >
              {positivo ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
              {formatarPercentual(row.diferenca_deral_pct)}
            </span>
            <p className="text-[11px] text-muted-foreground tabular-nums">
              {diffBrl > 0 ? "+" : ""}
              {formatarMoeda(diffBrl)}
            </p>
          </div>
        );
      },
    },
    {
      id: "praca",
      header: "Praça / Fonte Principal",
      accessorFn: (row) => `${row.praca_efetiva ?? "—"} · ${row.fonte_efetiva ?? "—"}`,
      cell: (_value, row) => (
        <div className="text-xs">
          <p className="font-medium text-foreground">{row.praca_efetiva ?? "—"}</p>
          <p className="text-muted-foreground">{row.fonte_efetiva ?? "—"}</p>
        </div>
      ),
    },
    {
      id: "deral",
      header: "Ref. DERAL (Média / Faixa PR)",
      accessorFn: (row) => (row.valor_deral !== null ? `${formatarMoeda(row.valor_deral)} (${row.data_deral ?? ""})` : "—"),
      cell: (_value, row) =>
        row.valor_deral !== null ? (
          <div className="text-xs text-muted-foreground space-y-0.5">
            <div className="flex items-center gap-1.5">
              <span className="tabular-nums font-medium text-foreground">{formatarMoeda(row.valor_deral)}</span>
              {typeof row.variacao_semanal_deral_pct === "number" && (
                <span
                  className={cn(
                    "text-[10px] font-semibold px-1 rounded-sm",
                    row.variacao_semanal_deral_pct > 0
                      ? "bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300"
                      : row.variacao_semanal_deral_pct < 0
                        ? "bg-amber-500/10 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
                        : "bg-muted text-muted-foreground"
                  )}
                >
                  {formatarPercentual(row.variacao_semanal_deral_pct)} sem.
                </span>
              )}
            </div>
            {row.valor_minimo_regional_deral && row.valor_maximo_regional_deral && (
              <p className="text-[10px] tabular-nums">
                Faixa PR: {formatarMoeda(row.valor_minimo_regional_deral)} ({row.praca_minimo_regional_deral}) a{" "}
                {formatarMoeda(row.valor_maximo_regional_deral)} ({row.praca_maximo_regional_deral})
              </p>
            )}
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      id: "acoes",
      header: "",
      accessorKey: "codigo",
      isActionColumn: true,
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_value, row) => {
        const escopoRemovivel: EscopoRegional | null =
          row.valor_fazenda !== null && podeEditarFazenda
            ? "FAZENDA"
            : row.valor_tenant !== null
              ? "TENANT"
              : null;

        return (
          <div className="flex items-center gap-0 justify-end">
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-7 border-0 text-primary hover:text-primary"
              title="Gerenciar fontes e cotações da região"
              aria-label={`Editar cotação regional de ${row.nome}`}
              onClick={() => abrirEdicao(row)}
            >
              <Pencil className="size-3.5" />
            </Button>
            {escopoRemovivel && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-7 border-0 text-amber-600 hover:text-amber-700 dark:text-amber-400"
                title="Restaurar referência herdada"
                aria-label={`Restaurar herança de ${row.nome}`}
                onClick={() => setConfirmRestore({ item: row, escopo: escopoRemovivel })}
              >
                <RotateCcw className="size-3.5" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <Card className="rounded-sm">
      <CardHeader className="pb-3 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <MapPin className="size-4 text-emerald-600 dark:text-emerald-400" />
              Cotações por Região e Múltiplas Fontes (Praça Local, Cooperativas &amp; DERAL)
            </CardTitle>
            <CardDescription className="text-xs">
              Cadastre múltiplas fontes na sua região (Cooperativas, Frigoríficos, Corretoras e Núcleos DERAL), compare a faixa Mín / Média / Máx e escolha usar uma fonte específica ou a média consensual das fontes.
            </CardDescription>
          </div>
          <Badge variant="outline" className="rounded-sm text-xs self-start sm:self-auto">
            {podeEditarFazenda ? `Fazenda ativa: ${fazendaAtiva?.nome ?? "Selecionada"}` : "Escopo: Grupo / Tenant"}
          </Badge>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/60">
          <div className="flex items-center gap-1.5 text-xs">
            <Layers className="size-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Fonte:</span>
            <Select value={filtroFonte} onValueChange={setFiltroFonte}>
              <SelectTrigger className="h-8 w-52 rounded-sm text-xs">
                <SelectValue placeholder="Filtrar por origem/fonte" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                <SelectItem value="TODAS">Todas as origens e fontes</SelectItem>
                <SelectItem value="REGIONAL_LOCAL">Com cotação regional (Fazenda/Grupo)</SelectItem>
                <SelectItem value="OFICIAL_UF">Órgão Estadual da UF</SelectItem>
                <SelectItem value="PARCEIRO_UF">Parceiro Autorizado da UF</SelectItem>
                <SelectItem value="MULTI_FONTE">Múltiplas fontes comparadas (2+)</SelectItem>
                <SelectItem value="DERAL">Herdando referência DERAL/SEAB-PR</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {pracasDeralCatalogadas.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs">
              <MapPin className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="text-muted-foreground">Simular Núcleo DERAL-PR:</span>
              <Select value={filtroPracaDeral} onValueChange={setFiltroPracaDeral}>
                <SelectTrigger className="h-8 w-56 rounded-sm text-xs">
                  <SelectValue placeholder="Média Estadual PR" />
                </SelectTrigger>
                <SelectContent className="rounded-sm max-h-60">
                  <SelectItem value="PADRAO">Paraná — Média Estadual (20 núcleos)</SelectItem>
                  {pracasDeralCatalogadas.map((praca) => (
                    <SelectItem key={praca} value={praca}>
                      Núcleo Regional: {praca}/PR
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full rounded-sm" />
            <Skeleton className="h-10 w-full rounded-sm" />
            <Skeleton className="h-10 w-full rounded-sm" />
          </div>
        ) : (
          <DataTable
            data={dadosFiltrados}
            columns={columns}
            searchable
            searchPlaceholder="Buscar commodity, praça ou fonte..."
            exportable
            exportFileName="cotacoes-regionais-multifonte"
            emptyMessage="Nenhuma referência regional encontrada para o filtro selecionado"
          />
        )}
      </CardContent>

      <Dialog open={Boolean(editingItem)} onOpenChange={(open) => { if (!open) setEditingItem(null); }}>
        <DialogContent className="max-w-xl rounded-sm p-0">
          <DialogHeader>
            <DialogTitle>
              Fontes e Cotações Regionais — {editingItem?.nome}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Adicione ou atualize cotações de diferentes fontes da sua região ({editingItem?.unidade}). Cada combinação de Praça + Fonte é mantida no painel comparativo abaixo.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit((vals) => salvarMutation.mutate(vals))}>
              <DialogBody className="space-y-4">
                {editingItem?.fontes_comparadas && editingItem.fontes_comparadas.length > 0 && (
                  <div className="rounded-sm border bg-muted/20 p-2.5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-foreground">
                        Comparativo de Fontes Ativas ({editingItem.fontes_comparadas.length})
                      </span>
                      <span className="text-[11px] text-muted-foreground tabular-nums">
                        Mín: <strong>{formatarMoeda(editingItem.valor_minimo_fontes)}</strong> · Média:{" "}
                        <strong>{formatarMoeda(editingItem.valor_medio_fontes)}</strong> · Máx:{" "}
                        <strong>{formatarMoeda(editingItem.valor_maximo_fontes)}</strong>
                      </span>
                    </div>
                    <div className="max-h-32 overflow-y-auto divide-y divide-border/60 text-xs">
                      {editingItem.fontes_comparadas.map((fc, idx) => (
                        <div
                          key={`${fc.escopo}-${fc.praca}-${fc.fonte}-${idx}`}
                          className="py-1.5 flex items-center justify-between gap-2"
                        >
                          <div className="truncate">
                            <span className="font-medium text-foreground">{fc.fonte}</span>
                            <span className="text-muted-foreground"> · {fc.praca}</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="font-semibold tabular-nums">{formatarMoeda(fc.valor)}</span>
                            {typeof fc.diferenca_para_media_pct === "number" && (
                              <span className="text-[10px] text-muted-foreground tabular-nums">
                                ({formatarPercentual(fc.diferenca_para_media_pct)})
                              </span>
                            )}
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-6 px-2 text-[10px] rounded-sm"
                              onClick={() => {
                                form.setValue("valor", fc.valor, { shouldValidate: true });
                                form.setValue("praca", fc.praca, { shouldValidate: true });
                                form.setValue("fonte", fc.fonte, { shouldValidate: true });
                              }}
                            >
                              Usar
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {editingItem?.pracas_deral_disponiveis && editingItem.pracas_deral_disponiveis.length > 0 && (
                  <div className="rounded-sm border bg-muted/30 p-2.5 space-y-1.5">
                    <p className="text-xs font-medium text-foreground">
                      Carregar preço oficial de Núcleo Regional DERAL-PR ({editingItem.pracas_deral_disponiveis.length} núcleos)
                    </p>
                    <Select onValueChange={aplicarNucleoDeral}>
                      <SelectTrigger className="h-8 rounded-sm text-xs">
                        <SelectValue placeholder="Escolha um núcleo regional para carregar o preço oficial..." />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm max-h-60">
                        {editingItem.pracas_deral_disponiveis.map((p) => (
                          <SelectItem key={p.praca} value={p.praca} className="text-xs">
                            {p.praca} — {formatarMoeda(p.valor)} ({p.registro_original})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <FormField
                    control={form.control}
                    name="valor"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Valor da Fonte (R$)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.01"
                            min="0.01"
                            className="h-8 rounded-sm"
                            value={Number.isFinite(field.value) ? field.value : ""}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="data_referencia"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Data Referência</FormLabel>
                        <FormControl>
                          <Input {...field} type="date" className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <FormField
                    control={form.control}
                    name="praca"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Região / Praça</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Ex: Cascavel/PR, Sorriso/MT, Rio Verde/GO" className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="fonte"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Fonte de Dados / Cooperativa</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Ex: Coamo, C.Vale, IMEA, CEPEA, Frigorífico" className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <FormField
                    control={form.control}
                    name="escopo"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Escopo de Aplicação</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder="Selecione o escopo" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            {podeEditarFazenda && (
                              <SelectItem value="FAZENDA">
                                Fazenda Ativa ({fazendaAtiva?.nome ?? "Selecionada"})
                              </SelectItem>
                            )}
                            <SelectItem value="TENANT">
                              Grupo / Tenant (todas as fazendas)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="modo_consolidacao"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Cálculo do Preço Efetivo</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder="Modo de consolidação" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            <SelectItem value="FONTE_SELECIONADA">
                              Usar esta fonte como referência principal
                            </SelectItem>
                            <SelectItem value="MEDIA_FONTES">
                              Média consensual de todas as fontes cadastradas
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="observacoes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Observações (opcional)</FormLabel>
                      <FormControl>
                        <Textarea
                          {...field}
                          rows={2}
                          placeholder="Condição de pagamento, frete FOB/CIF, escala ou bonificação..."
                          className="rounded-sm text-xs"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {editingItem?.historico_recente && editingItem.historico_recente.length > 0 && (
                  <div className="rounded-sm border bg-muted/20 p-2.5 space-y-1.5">
                    <p className="text-xs font-medium text-foreground flex items-center gap-1.5">
                      <History className="size-3.5 text-muted-foreground" />
                      Histórico Recente de Fontes da Região
                    </p>
                    <div className="max-h-24 overflow-y-auto space-y-1 text-[11px]">
                      {editingItem.historico_recente.slice(0, 5).map((h, idx) => (
                        <div key={`${h.registrado_em}-${idx}`} className="flex items-center justify-between text-muted-foreground">
                          <span>
                            <strong className="text-foreground">{formatarMoeda(h.valor)}</strong> · {h.praca} ({h.fonte})
                          </span>
                          <span className="font-mono text-[10px]">
                            {h.data_referencia} [{h.escopo}]
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </DialogBody>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm"
                  onClick={() => setEditingItem(null)}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  className="rounded-sm border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/30"
                  disabled={salvarMutation.isPending}
                >
                  {salvarMutation.isPending ? (
                    <Loader2 className="mr-2 size-3.5 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-3.5" />
                  )}
                  Salvar Fonte na Região
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(confirmRestore)}
        title="Restaurar referência herdada?"
        description={
          confirmRestore
            ? `Remove as cotações regionais de ${confirmRestore.item.nome} no escopo ${confirmRestore.escopo === "FAZENDA" ? "Fazenda Ativa" : "Grupo/Tenant"}, voltando a herdar o valor padrão automaticamente.`
            : undefined
        }
        confirmText="Restaurar"
        onCancel={() => setConfirmRestore(null)}
        onConfirm={() => {
          if (confirmRestore) {
            removerMutation.mutate({
              codigo: confirmRestore.item.codigo,
              escopo: confirmRestore.escopo,
            });
          }
        }}
      />
    </Card>
  );
}
