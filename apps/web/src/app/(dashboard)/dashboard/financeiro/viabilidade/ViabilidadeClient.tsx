"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Award,
  Calculator,
  CheckCircle2,
  Eye,
  MinusCircle,
  Percent,
  Plus,
  PlusCircle,
  Sparkles,
  Trash2,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { PrecoEquilibrioTmaCard } from "@/components/financeiro/preco-equilibrio-tma-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

import { apiFetch } from "@/lib/api";

export type CategoriaProjeto =
  | "IRRIGACAO"
  | "ARMAZENAGEM"
  | "MAQUINARIO"
  | "EXPANSAO_AREA"
  | "PECUARIA"
  | "OUTROS";

export interface TmaCalculoInput {
  percentual_capital_proprio: number;
  custo_oportunidade_proprio_aa: number;
  percentual_financiamento: number;
  taxa_financiamento_aa: number;
  premio_risco_agro_aa: number;
}

export interface TmaCalculoOutput {
  tma_calculada_aa: number;
  custo_ponderado_capital_aa: number;
  premio_risco_agro_aa: number;
  detalhamento: string;
}

export interface ProjetoInvestimentoInput {
  id: string;
  nome: string;
  categoria: CategoriaProjeto;
  investimento_inicial: number;
  tma_aa: number;
  prazo_maximo_aceitavel_anos: number;
  fluxos_caixa_anuais: number[];
  valor_residual_final: number;
}

export interface FluxoAnoDetalheOutput {
  ano: number;
  fluxo_nominal: number;
  fator_desconto: number;
  fluxo_descontado: number;
  saldo_acumulado_simples: number;
  saldo_acumulado_descontado: number;
}

export interface ProjetoViabilidadeOutput {
  id: string;
  nome: string;
  categoria: string;
  investimento_inicial: number;
  tma_aa: number;
  prazo_maximo_aceitavel_anos: number;
  vpl: number;
  tir_aa: number | null;
  tirm_aa: number | null;
  margem_seguranca_tir_pp: number | null;
  payback_simples_anos: number | null;
  payback_descontado_anos: number | null;
  indice_lucratividade: number;
  fluxo_nao_convencional: boolean;
  decisao_vpl: "ACEITAR" | "REJEITAR" | "INDIFERENTE";
  decisao_tir: "ACEITAR" | "REJEITAR" | "INDIFERENTE" | "INCONCLUSIVO";
  decisao_payback: "ACEITAR" | "REJEITAR";
  veredito_final: "VIAVEL" | "INVIAVEL" | "ATENCAO_LIQUIDEZ";
  resumo_executivo: string;
  evolucao_anual: FluxoAnoDetalheOutput[];
}

export interface ComparativoViabilidadeOutput {
  tma_calculada: TmaCalculoOutput | null;
  resultados: ProjetoViabilidadeOutput[];
  projeto_recomendado_id: string | null;
  justificativa_comparativa: string;
}

export interface TemplateProjetoAgro {
  id: string;
  nome: string;
  categoria: CategoriaProjeto;
  descricao: string;
  investimento_inicial: number;
  tma_sugerida_aa: number;
  prazo_maximo_aceitavel_anos: number;
  fluxos_caixa_anuais: number[];
  valor_residual_final: number;
}

const CATEGORIA_LABELS: Record<CategoriaProjeto, string> = {
  IRRIGACAO: "Irrigação / Pivô",
  ARMAZENAGEM: "Silo / Armazenagem",
  MAQUINARIO: "Maquinário Agrícola",
  EXPANSAO_AREA: "Expansão de Área",
  PECUARIA: "Infraestrutura Pecuária",
  OUTROS: "Outros Projetos",
};

const DEFAULT_TEMPLATES_FALLBACK: TemplateProjetoAgro[] = [
  {
    id: "tpl-pivo",
    nome: "Novo Pivô Central (100 ha)",
    categoria: "IRRIGACAO",
    descricao: "Implantação de pivô para ganho de produtividade e 3ª safra irrigada.",
    investimento_inicial: 1150000,
    tma_sugerida_aa: 11.5,
    prazo_maximo_aceitavel_anos: 4.5,
    fluxos_caixa_anuais: [340000, 380000, 410000, 430000, 450000],
    valor_residual_final: 220000,
  },
  {
    id: "tpl-silo",
    nome: "Expansão de Silo / Armazenagem Própria",
    categoria: "ARMAZENAGEM",
    descricao: "Redução de fretes no pico de safra e captura de prêmio na entressafra.",
    investimento_inicial: 1800000,
    tma_sugerida_aa: 11.5,
    prazo_maximo_aceitavel_anos: 5.0,
    fluxos_caixa_anuais: [420000, 480000, 520000, 560000, 600000],
    valor_residual_final: 550000,
  },
];

function formatBRL(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatAnos(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "Não recupera";
  return `${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} anos`;
}

function formatPercent(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "Inconclusiva";
  return `${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function templateToProject(template: TemplateProjetoAgro, suffix: string): ProjetoInvestimentoInput {
  return {
    id: `${template.id}-${suffix}`,
    nome: template.nome,
    categoria: template.categoria,
    investimento_inicial: template.investimento_inicial,
    tma_aa: template.tma_sugerida_aa,
    prazo_maximo_aceitavel_anos: template.prazo_maximo_aceitavel_anos,
    fluxos_caixa_anuais: [...template.fluxos_caixa_anuais],
    valor_residual_final: template.valor_residual_final,
  };
}

function renderVereditoBadge(veredito: ProjetoViabilidadeOutput["veredito_final"]) {
  if (veredito === "VIAVEL") {
    return (
      <Badge className="rounded-sm bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 gap-1">
        <CheckCircle2 className="size-3" /> Viável
      </Badge>
    );
  }
  if (veredito === "ATENCAO_LIQUIDEZ") {
    return (
      <Badge className="rounded-sm bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 gap-1">
        <AlertTriangle className="size-3" /> Atenção Liquidez
      </Badge>
    );
  }
  return (
    <Badge className="rounded-sm bg-destructive/15 text-destructive border-destructive/30 gap-1">
      <XCircle className="size-3" /> Inviável
    </Badge>
  );
}

export function ViabilidadeClient({ initialTemplates }: { initialTemplates: TemplateProjetoAgro[] }) {
  const { data: templates = [] } = useQuery<TemplateProjetoAgro[]>({
    queryKey: ["financeiro", "viabilidade", "templates"],
    queryFn: () => apiFetch<TemplateProjetoAgro[]>("/financeiro/viabilidade/templates"),
    initialData: initialTemplates.length > 0 ? initialTemplates : undefined,
    retry: false,
  });

  const catalog = templates.length > 0 ? templates : DEFAULT_TEMPLATES_FALLBACK;

  const [tmaInput, setTmaInput] = useState<TmaCalculoInput>({
    percentual_capital_proprio: 40,
    custo_oportunidade_proprio_aa: 12.0,
    percentual_financiamento: 60,
    taxa_financiamento_aa: 8.5,
    premio_risco_agro_aa: 2.0,
  });

  const [selectedTemplateId, setSelectedTemplateId] = useState<string>(catalog[0]?.id ?? "");
  const [projetos, setProjetos] = useState<ProjetoInvestimentoInput[]>(() =>
    catalog.slice(0, 2).map((tpl, idx) => templateToProject(tpl, String(idx + 1)))
  );
  const [simulacao, setSimulacao] = useState<ComparativoViabilidadeOutput | null>(null);
  const [selectedResultadoId, setSelectedResultadoId] = useState<string>("");

  const calcularTmaMutation = useMutation({
    mutationFn: (payload: TmaCalculoInput) =>
      apiFetch<TmaCalculoOutput>("/financeiro/viabilidade/calcular-tma", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      toast.success(`TMA calculada: ${data.tma_calculada_aa.toFixed(2)}% a.a.`);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao calcular TMA");
    },
  });

  const simularMutation = useMutation({
    mutationFn: () =>
      apiFetch<ComparativoViabilidadeOutput>("/financeiro/viabilidade/simular", {
        method: "POST",
        body: JSON.stringify({
          tma_composicao: tmaInput,
          projetos,
        }),
      }),
    onSuccess: (data) => {
      setSimulacao(data);
      const nextSelected =
        data.projeto_recomendado_id ?? data.resultados[0]?.id ?? "";
      setSelectedResultadoId(nextSelected);
      toast.success("Análise comparativa atualizada");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao simular viabilidade dos projetos");
    },
  });

  const tmaPrevia = useMemo(() => {
    const soma = tmaInput.percentual_capital_proprio + tmaInput.percentual_financiamento;
    const ponderado =
      soma > 0
        ? (tmaInput.percentual_capital_proprio * tmaInput.custo_oportunidade_proprio_aa +
            tmaInput.percentual_financiamento * tmaInput.taxa_financiamento_aa) /
          soma
        : 0;
    return Number((ponderado + tmaInput.premio_risco_agro_aa).toFixed(2));
  }, [tmaInput]);

  const applyTmaToAllProjects = () => {
    const valorTma = calcularTmaMutation.data?.tma_calculada_aa ?? tmaPrevia;
    setProjetos((prev) => prev.map((proj) => ({ ...proj, tma_aa: valorTma })));
    toast.success(`TMA de ${valorTma.toFixed(2)}% a.a. aplicada a todos os projetos`);
  };

  const addBlankProject = () => {
    const nextNumber = projetos.length + 1;
    setProjetos((prev) => [
      ...prev,
      {
        id: `proj-${Date.now()}-${nextNumber}`,
        nome: `Novo Investimento ${nextNumber}`,
        categoria: "OUTROS",
        investimento_inicial: 500000,
        tma_aa: tmaPrevia,
        prazo_maximo_aceitavel_anos: 4,
        fluxos_caixa_anuais: [160000, 180000, 200000, 210000, 220000],
        valor_residual_final: 50000,
      },
    ]);
  };

  const addFromTemplate = () => {
    const tpl = catalog.find((item) => item.id === selectedTemplateId) ?? catalog[0];
    if (!tpl) return;
    setProjetos((prev) => [
      ...prev,
      templateToProject(tpl, String(Date.now()).slice(-5)),
    ]);
    toast.success(`Template "${tpl.nome}" adicionado para comparação`);
  };

  const removeProject = (projectId: string) => {
    if (projetos.length <= 1) {
      toast.warning("Mantenha ao menos um projeto para análise");
      return;
    }
    setProjetos((prev) => prev.filter((item) => item.id !== projectId));
  };

  const updateProjectField = <K extends keyof ProjetoInvestimentoInput>(
    projectId: string,
    field: K,
    value: ProjetoInvestimentoInput[K]
  ) => {
    setProjetos((prev) =>
      prev.map((item) => (item.id === projectId ? { ...item, [field]: value } : item))
    );
  };

  const updateCashFlowYear = (projectId: string, yearIndex: number, value: number) => {
    setProjetos((prev) =>
      prev.map((item) => {
        if (item.id !== projectId) return item;
        const nextFlows = [...item.fluxos_caixa_anuais];
        nextFlows[yearIndex] = Number.isFinite(value) ? value : 0;
        return { ...item, fluxos_caixa_anuais: nextFlows };
      })
    );
  };

  const addCashFlowYear = (projectId: string) => {
    setProjetos((prev) =>
      prev.map((item) => {
        if (item.id !== projectId || item.fluxos_caixa_anuais.length >= 15) return item;
        const ultimo = item.fluxos_caixa_anuais[item.fluxos_caixa_anuais.length - 1] ?? 100000;
        return { ...item, fluxos_caixa_anuais: [...item.fluxos_caixa_anuais, ultimo] };
      })
    );
  };

  const removeCashFlowYear = (projectId: string) => {
    setProjetos((prev) =>
      prev.map((item) => {
        if (item.id !== projectId || item.fluxos_caixa_anuais.length <= 1) return item;
        return { ...item, fluxos_caixa_anuais: item.fluxos_caixa_anuais.slice(0, -1) };
      })
    );
  };

  const resultados = useMemo(() => simulacao?.resultados ?? [], [simulacao]);
  const resultadoSelecionado = useMemo(() => {
    if (resultados.length === 0) return null;
    return (
      resultados.find((r) => r.id === selectedResultadoId) ??
      resultados.find((r) => r.id === simulacao?.projeto_recomendado_id) ??
      resultados[0]
    );
  }, [resultados, selectedResultadoId, simulacao]);

  const comparativoColumns: ColumnDef<ProjetoViabilidadeOutput>[] = [
    {
      id: "nome",
      header: "Projeto",
      accessorKey: "nome",
      sortable: true,
      cell: (value, row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-xs">{String(value)}</span>
          {simulacao?.projeto_recomendado_id === row.id && (
            <Badge className="rounded-sm bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px]">
              Recomendado
            </Badge>
          )}
        </div>
      ),
    },
    {
      id: "investimento_inicial",
      header: "Investimento",
      accessorKey: "investimento_inicial",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => <span className="tabular-nums text-xs">{formatBRL(Number(v))}</span>,
    },
    {
      id: "payback_simples_anos",
      header: "Payback Simples",
      accessorKey: "payback_simples_anos",
      sortable: true,
      exportFormat: (v) => formatAnos(v as number | null),
      cell: (v) => <span className="tabular-nums text-xs">{formatAnos(v as number | null)}</span>,
    },
    {
      id: "payback_descontado_anos",
      header: "Payback Descontado",
      accessorKey: "payback_descontado_anos",
      sortable: true,
      exportFormat: (v) => formatAnos(v as number | null),
      cell: (v, row) => (
        <span
          className={`tabular-nums text-xs font-medium ${
            row.decisao_payback === "ACEITAR"
              ? "text-emerald-700 dark:text-emerald-300"
              : "text-amber-700 dark:text-amber-300"
          }`}
        >
          {formatAnos(v as number | null)}
        </span>
      ),
    },
    {
      id: "vpl",
      header: "VPL (Riqueza)",
      accessorKey: "vpl",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => {
        const num = Number(v);
        return (
          <span
            className={`tabular-nums text-xs font-semibold ${
              num > 0
                ? "text-emerald-700 dark:text-emerald-300"
                : num < 0
                  ? "text-destructive"
                  : "text-muted-foreground"
            }`}
          >
            {formatBRL(num)}
          </span>
        );
      },
    },
    {
      id: "tir_aa",
      header: "TIR (% a.a.)",
      accessorKey: "tir_aa",
      sortable: true,
      exportFormat: (v) => formatPercent(v as number | null),
      cell: (v, row) => (
        <span className="tabular-nums text-xs">
          {row.fluxo_nao_convencional ? `${formatPercent(v as number | null)} *` : formatPercent(v as number | null)}
        </span>
      ),
    },
    {
      id: "tirm_aa",
      header: "TIRM (% a.a.)",
      accessorKey: "tirm_aa",
      sortable: true,
      exportFormat: (v) => formatPercent(v as number | null),
      cell: (v) => <span className="tabular-nums text-xs">{formatPercent(v as number | null)}</span>,
    },
    {
      id: "indice_lucratividade",
      header: "IL (x)",
      accessorKey: "indice_lucratividade",
      sortable: true,
      exportFormat: (v) => `${Number(v).toFixed(2)}x`,
      cell: (v) => <span className="tabular-nums text-xs">{Number(v).toFixed(2)}x</span>,
    },
    {
      id: "veredito_final",
      header: "Veredito",
      accessorKey: "veredito_final",
      sortable: true,
      exportFormat: (v) => String(v),
      cell: (_v, row) => renderVereditoBadge(row.veredito_final),
    },
    {
      id: "actions",
      header: "",
      isActionColumn: true,
      exportable: false,
      cell: (_v, row) => (
        <div className="flex items-center justify-end gap-0">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="border-0 p-1.5 h-7 text-primary hover:text-primary"
            title="Detalhar fluxo descontado"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedResultadoId(row.id);
            }}
          >
            <Eye className="size-4" />
          </Button>
        </div>
      ),
    },
  ];

  const fluxoColumns: ColumnDef<FluxoAnoDetalheOutput>[] = [
    {
      id: "ano",
      header: "Ano",
      accessorKey: "ano",
      sortable: true,
      exportFormat: (v) => `Ano ${String(v)}`,
      cell: (v) => <span className="font-medium text-xs">Ano {String(v)}</span>,
    },
    {
      id: "fluxo_nominal",
      header: "Fluxo Nominal",
      accessorKey: "fluxo_nominal",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span className={`tabular-nums text-xs ${Number(v) < 0 ? "text-destructive" : ""}`}>
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "fator_desconto",
      header: "Fator Desconto (TMA)",
      accessorKey: "fator_desconto",
      sortable: true,
      exportFormat: (v) => Number(v).toFixed(4),
      cell: (v) => <span className="tabular-nums text-xs text-muted-foreground">{Number(v).toFixed(4)}</span>,
    },
    {
      id: "fluxo_descontado",
      header: "Fluxo Descontado (VP)",
      accessorKey: "fluxo_descontado",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span className={`tabular-nums text-xs ${Number(v) < 0 ? "text-destructive" : "text-primary font-medium"}`}>
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "saldo_acumulado_simples",
      header: "Acumulado Simples",
      accessorKey: "saldo_acumulado_simples",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span
          className={`tabular-nums text-xs ${
            Number(v) >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-muted-foreground"
          }`}
        >
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "saldo_acumulado_descontado",
      header: "Acumulado Descontado (VPL)",
      accessorKey: "saldo_acumulado_descontado",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span
          className={`tabular-nums text-xs font-semibold ${
            Number(v) >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-destructive"
          }`}
        >
          {formatBRL(Number(v))}
        </span>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Viabilidade de Investimentos (VPL, TIR e Payback)"
        description="Simule TMA, Payback Simples/Descontado, VPL e TIR para decisões estratégicas de CapEx na fazenda."
        breadcrumbs={[
          { label: "Financeiro", href: "/dashboard/financeiro" },
          { label: "Viabilidade (VPL/TIR)" },
        ]}
        icon={<TrendingUp className="text-primary" size={22} />}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={addBlankProject}
            >
              <Plus className="size-4 mr-1.5" />
              Novo Projeto
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-sm border-primary/40 text-primary hover:bg-primary/10"
              disabled={simularMutation.isPending || projetos.length === 0}
              onClick={() => simularMutation.mutate()}
            >
              <Calculator className="size-4 mr-1.5" />
              {simularMutation.isPending ? "Calculando..." : "Simular Comparativo"}
            </Button>
          </div>
        }
      />

      {/* Bloco 1: Calculadora de TMA */}
      <Card className="rounded-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Percent className="size-4 text-primary" />
                Taxa Mínima de Atratividade (TMA) — Custo de Oportunidade
              </CardTitle>
              <CardDescription className="text-xs">
                Pondere capital próprio (Selic/CDI) e crédito rural (Plano Safra) somados ao prêmio de risco da atividade.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="rounded-sm text-xs font-semibold">
                TMA Estimada: {(calcularTmaMutation.data?.tma_calculada_aa ?? tmaPrevia).toFixed(2)}% a.a.
              </Badge>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="rounded-sm"
                disabled={calcularTmaMutation.isPending}
                onClick={() => calcularTmaMutation.mutate(tmaInput)}
              >
                <Calculator className="size-3.5 mr-1.5" />
                Validar TMA
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="rounded-sm"
                onClick={applyTmaToAllProjects}
              >
                <Sparkles className="size-3.5 mr-1.5" />
                Aplicar nos Projetos
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Capital Próprio (%)</Label>
              <Input
                type="number"
                step="1"
                min="0"
                max="100"
                className="h-8 text-xs rounded-sm tabular-nums"
                value={tmaInput.percentual_capital_proprio}
                onChange={(e) =>
                  setTmaInput((prev) => ({ ...prev, percentual_capital_proprio: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Custo Próprio (% a.a.)</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                className="h-8 text-xs rounded-sm tabular-nums"
                value={tmaInput.custo_oportunidade_proprio_aa}
                onChange={(e) =>
                  setTmaInput((prev) => ({ ...prev, custo_oportunidade_proprio_aa: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Financiamento (%)</Label>
              <Input
                type="number"
                step="1"
                min="0"
                max="100"
                className="h-8 text-xs rounded-sm tabular-nums"
                value={tmaInput.percentual_financiamento}
                onChange={(e) =>
                  setTmaInput((prev) => ({ ...prev, percentual_financiamento: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Taxa Financiamento (% a.a.)</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                className="h-8 text-xs rounded-sm tabular-nums"
                value={tmaInput.taxa_financiamento_aa}
                onChange={(e) =>
                  setTmaInput((prev) => ({ ...prev, taxa_financiamento_aa: Number(e.target.value) || 0 }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Prêmio de Risco Agro (% a.a.)</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                className="h-8 text-xs rounded-sm tabular-nums"
                value={tmaInput.premio_risco_agro_aa}
                onChange={(e) =>
                  setTmaInput((prev) => ({ ...prev, premio_risco_agro_aa: Number(e.target.value) || 0 }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bloco 2: Portfólio de Projetos + Templates */}
      <Card className="rounded-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-sm font-semibold">Projetos em Comparação ({projetos.length})</CardTitle>
              <CardDescription className="text-xs">
                Carregue cenários de referência do agro ou personalize o CapEx e os fluxos anuais previstos.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="w-64">
                <Select value={selectedTemplateId} onValueChange={(v) => setSelectedTemplateId(v)}>
                  <SelectTrigger className="h-8 text-xs rounded-sm">
                    <SelectValue placeholder="Selecione um template agro..." />
                  </SelectTrigger>
                  <SelectContent>
                    {catalog.map((tpl) => (
                      <SelectItem key={tpl.id} value={tpl.id}>
                        {tpl.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={addFromTemplate}>
                <Plus className="size-3.5 mr-1.5" />
                Incluir Template
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {projetos.map((projeto) => (
            <div key={projeto.id} className="rounded-sm border bg-muted/20 p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 flex-1">
                  <div className="space-y-1">
                    <Label className="text-xs">Nome do Projeto</Label>
                    <Input
                      className="h-8 text-xs rounded-sm"
                      value={projeto.nome}
                      onChange={(e) => updateProjectField(projeto.id, "nome", e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Categoria</Label>
                    <Select
                      value={projeto.categoria}
                      onValueChange={(v) => updateProjectField(projeto.id, "categoria", v as CategoriaProjeto)}
                    >
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(CATEGORIA_LABELS) as CategoriaProjeto[]).map((cat) => (
                          <SelectItem key={cat} value={cat}>
                            {CATEGORIA_LABELS[cat]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm text-destructive hover:text-destructive mt-5"
                  onClick={() => removeProject(projeto.id)}
                  title="Remover projeto"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Invest. Inicial (R$)</Label>
                  <Input
                    type="number"
                    min="1"
                    step="1000"
                    className="h-8 text-xs rounded-sm tabular-nums"
                    value={projeto.investimento_inicial}
                    onChange={(e) =>
                      updateProjectField(projeto.id, "investimento_inicial", Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">TMA (% a.a.)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.25"
                    className="h-8 text-xs rounded-sm tabular-nums"
                    value={projeto.tma_aa}
                    onChange={(e) => updateProjectField(projeto.id, "tma_aa", Number(e.target.value) || 0)}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Payback Máx. (anos)</Label>
                  <Input
                    type="number"
                    min="0.5"
                    step="0.5"
                    className="h-8 text-xs rounded-sm tabular-nums"
                    value={projeto.prazo_maximo_aceitavel_anos}
                    onChange={(e) =>
                      updateProjectField(projeto.id, "prazo_maximo_aceitavel_anos", Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Valor Residual (R$)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="1000"
                    className="h-8 text-xs rounded-sm tabular-nums"
                    value={projeto.valor_residual_final}
                    onChange={(e) =>
                      updateProjectField(projeto.id, "valor_residual_final", Number(e.target.value) || 0)
                    }
                  />
                </div>
              </div>

              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-muted-foreground">
                    Fluxos de Caixa Anuais Líquidos ({projeto.fluxos_caixa_anuais.length} anos)
                  </Label>
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs rounded-sm"
                      disabled={projeto.fluxos_caixa_anuais.length <= 1}
                      onClick={() => removeCashFlowYear(projeto.id)}
                    >
                      <MinusCircle className="size-3.5 mr-1" />
                      Ano
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs rounded-sm"
                      disabled={projeto.fluxos_caixa_anuais.length >= 15}
                      onClick={() => addCashFlowYear(projeto.id)}
                    >
                      <PlusCircle className="size-3.5 mr-1" />
                      Ano
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {projeto.fluxos_caixa_anuais.map((fluxo, idx) => (
                    <div key={`${projeto.id}-ano-${idx + 1}`} className="space-y-1">
                      <span className="text-[10px] font-medium text-muted-foreground">Ano {idx + 1} (R$)</span>
                      <Input
                        type="number"
                        step="1000"
                        className="h-8 text-xs rounded-sm tabular-nums"
                        value={fluxo}
                        onChange={(e) => updateCashFlowYear(projeto.id, idx, Number(e.target.value))}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Bloco 3: Resultado Comparativo Lado a Lado */}
      {simulacao && (
        <div className="space-y-6">
          <Alert className="rounded-sm border-emerald-500/30 bg-emerald-500/10 text-foreground">
            <Award className="size-4 text-emerald-600 dark:text-emerald-400" />
            <AlertTitle className="text-sm font-semibold">Recomendação Executiva (Critério VPL + Liquidez)</AlertTitle>
            <AlertDescription className="text-xs text-muted-foreground">
              {simulacao.justificativa_comparativa}
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <h2 className="text-sm font-semibold">Análise Comparativa Lado a Lado (Payback, VPL e TIR)</h2>
            <DataTable
              data={resultados}
              columns={comparativoColumns}
              searchable
              searchPlaceholder="Buscar projeto na comparação..."
              exportable
              exportFileName="viabilidade-comparativo-projetos"
              onRowClick={(row) => setSelectedResultadoId(row.id)}
              rowClassName={(row) =>
                row.id === resultadoSelecionado?.id ? "bg-primary/5" : ""
              }
            />
          </div>

          {resultadoSelecionado && (
            <div className="space-y-4">
              {resultadoSelecionado.fluxo_nao_convencional && (
                <Alert className="rounded-sm border-amber-500/40 bg-amber-500/10 text-foreground">
                  <AlertTriangle className="size-4 text-amber-600 dark:text-amber-400" />
                  <AlertTitle className="text-sm font-semibold">
                    Fluxo Não Convencional Detectado em &quot;{resultadoSelecionado.nome}&quot;
                  </AlertTitle>
                  <AlertDescription className="text-xs text-muted-foreground">
                    Como há mais de uma inversão de sinal nos fluxos futuros, a TIR tradicional pode apresentar múltiplas raízes. Priorize o VPL ({formatBRL(resultadoSelecionado.vpl)}) e a TIRM ({formatPercent(resultadoSelecionado.tirm_aa)}).
                  </AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="rounded-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold">Comparação de Riqueza Gerada (VPL em R$)</CardTitle>
                    <CardDescription className="text-xs">
                      Valores positivos indicam geração de valor acima da TMA.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={resultados}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                        <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(val: number | string) => formatBRL(Number(val))} />
                        <ReferenceLine y={0} stroke="#888" />
                        <Bar dataKey="vpl" name="VPL (R$)" fill="#10b981" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card className="rounded-sm">
                  <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-sm font-semibold">
                        Curva de Recuperação do Capital — {resultadoSelecionado.nome}
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Cruzamento em zero indica Payback Simples vs. Payback Descontado pela TMA.
                      </CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={resultadoSelecionado.evolucao_anual}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                        <XAxis dataKey="ano" tick={{ fontSize: 11 }} tickFormatter={(v) => `Ano ${v}`} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(val: number | string) => formatBRL(Number(val))} />
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                        <ReferenceLine y={0} stroke="#888" strokeDasharray="3 3" />
                        <Line
                          type="monotone"
                          dataKey="saldo_acumulado_simples"
                          name="Acumulado Simples"
                          stroke="#0ea5e9"
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="saldo_acumulado_descontado"
                          name="Acumulado Descontado (VPL)"
                          stroke="#10b981"
                          strokeWidth={2.5}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold">
                    Evolução Anual dos Fluxos Descontados — {resultadoSelecionado.nome}
                  </h2>
                  <div className="w-64">
                    <Select value={resultadoSelecionado.id} onValueChange={(v) => setSelectedResultadoId(v)}>
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {resultados.map((res) => (
                          <SelectItem key={res.id} value={res.id}>
                            {res.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DataTable
                  data={resultadoSelecionado.evolucao_anual}
                  columns={fluxoColumns}
                  searchable={false}
                  exportable
                  exportFileName={`viabilidade-fluxo-${resultadoSelecionado.id}`}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bloco Complementar: Preço de Equilíbrio Econômico por TMA (Safra / Hedge) */}
      <PrecoEquilibrioTmaCard
        defaultTmaAa={calcularTmaMutation.data?.tma_calculada_aa ?? tmaPrevia}
      />
    </div>
  );
}
