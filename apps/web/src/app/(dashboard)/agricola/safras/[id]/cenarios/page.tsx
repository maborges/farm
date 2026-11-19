"use client";

import React, { use, useState, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Plus, Copy, Trash2, RefreshCw, BarChart2, TrendingUp, TrendingDown,
  DollarSign, Wheat, AlertCircle, Eye, X, Sparkles
} from "lucide-react";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { KPICard, moeda, num } from "@/components/shared/kpi-card";
import { useHasTier } from "@/hooks/use-has-tier";
import { getSafraLabel } from "@/lib/safra-label";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CenarioUnidade {
  id: string;
  production_unit_id: string;
  cultivo_nome: string | null;
  area_nome: string | null;
  area_ha: number;
  percentual_participacao: number;
  unidade_medida_id: string | null;
  produtividade_simulada: number | null;
  preco_simulado: number | null;
  custo_total_simulado_ha: number | null;
  depreciacao_ha: number | null;
  custo_base_fonte: string | null;
  produtividade_efetiva: number | null;
  preco_efetivo: number | null;
  custo_ha_efetivo: number | null;
  producao_total: number | null;
  receita_bruta: number | null;
  custo_total: number | null;
  margem_contribuicao: number | null;
  margem_pct: number | null;
  depreciacao_total: number | null;
  ir_valor: number | null;
  resultado_liquido: number | null;
  ponto_equilibrio: number | null;
}

interface Cenario {
  id: string;
  safra_id: string;
  nome: string;
  descricao: string | null;
  tipo: string;
  eh_base: boolean;
  status: string;
  unidade_medida_id: string | null;
  produtividade_default: number | null;
  preco_default: number | null;
  custo_ha_default: number | null;
  fator_custo_pct: number | null;
  ir_aliquota_pct: number | null;
  area_total_ha: number | null;
  receita_bruta_total: number | null;
  custo_total: number | null;
  margem_contribuicao_total: number | null;
  depreciacao_total: number | null;
  ir_valor_total: number | null;
  resultado_liquido_total: number | null;
  ponto_equilibrio_sc_ha: number | null;
  calculado_em: string | null;
  unidades: CenarioUnidade[];
}

interface Safra {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface CenarioFormData {
  nome: string;
  descricao?: string;
  tipo: "OTIMISTA" | "PESSIMISTA" | "CUSTOM";
  produtividade_default: string;
  preco_default: string;
  custo_ha_default: string;
  fator_custo_pct: string;
  ir_aliquota_pct: string;
}

const cenarioFormSchema = z.object({
  nome: z.string().min(1, "O nome do cenário é obrigatório").max(100, "O nome deve ter no máximo 100 caracteres"),
  descricao: z.string().optional(),
  tipo: z.enum(["OTIMISTA", "PESSIMISTA", "CUSTOM"]),
  produtividade_default: z.string().min(1, "Produtividade é obrigatória").refine(v => !isNaN(parseFloat(v.replace(",", "."))), "Valor inválido"),
  preco_default: z.string().min(1, "Preço é obrigatório").refine(v => !isNaN(parseFloat(v.replace(",", "."))), "Valor inválido"),
  custo_ha_default: z.string().min(1, "Custo por hectare é obrigatório").refine(v => !isNaN(parseFloat(v.replace(",", "."))), "Valor inválido"),
  fator_custo_pct: z.string().min(1, "Fator de custo é obrigatório").refine(v => {
    const n = parseFloat(v.replace(",", "."));
    return !isNaN(n) && n > 0 && n <= 2.0;
  }, "Deve ser entre 0.01 e 2.0 (ex: 0,85 para -15%)"),
  ir_aliquota_pct: z.string().refine(v => v === "" || !isNaN(parseFloat(v.replace(",", "."))), "Valor inválido"),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TIPO_LABELS: Record<string, string> = {
  BASE: "Base", OTIMISTA: "Otimista", PESSIMISTA: "Pessimista", CUSTOM: "Personalizado",
};

const TIPO_BADGE: Record<string, string> = {
  BASE: "secondary", OTIMISTA: "default", PESSIMISTA: "destructive", CUSTOM: "outline",
};

function fmtBrl(v: number | null) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtNum(v: number | null, decimals = 2) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtPct(v: number | null) {
  if (v === null || v === undefined) return "—";
  return `${fmtNum(v, 1)}%`;
}

function parseFld(v: string): number | undefined {
  const n = parseFloat(v.replace(",", "."));
  return isNaN(n) ? undefined : n;
}


// ---------------------------------------------------------------------------
// Cenario Card
// ---------------------------------------------------------------------------

function CenarioCard({
  cenario,
  onView,
  onDuplicar,
  onDelete,
  onRecalcular,
  canManageScenarios,
}: {
  cenario: Cenario;
  onView: () => void;
  onDuplicar: () => void;
  onDelete: () => void;
  onRecalcular?: () => void;
  canManageScenarios: boolean;
}) {
  const margem = cenario.margem_contribuicao_total;
  const margemPositiva = margem !== null && margem >= 0;

  return (
    <Card className="shadow-sm rounded-sm flex flex-col h-full hover:border-emerald-500/30 transition-colors group border-l-4 border-l-emerald-500">
      <CardHeader className="px-4 pt-4 pb-2 flex flex-row items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-emerald-900 dark:text-emerald-100">{cenario.nome}</span>
            <Badge
              variant={TIPO_BADGE[cenario.tipo] as "default" | "secondary" | "destructive" | "outline"}
              className="rounded-sm font-normal text-[10px] h-4"
            >
              {TIPO_LABELS[cenario.tipo] ?? cenario.tipo}
            </Badge>
            {cenario.status === "ARQUIVADO" && (
              <Badge variant="outline" className="text-muted-foreground rounded-sm font-normal text-[10px] h-4">Arquivado</Badge>
            )}
          </div>
        </div>
        {cenario.eh_base && (
          <Badge variant="secondary" className="rounded-sm font-bold text-[10px] h-4 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
            BASE
          </Badge>
        )}
      </CardHeader>

      <CardContent className="flex-1 pb-4">
        <div className="grid grid-cols-2 gap-y-3 gap-x-4">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Receita Bruta</p>
            <p className="text-sm font-semibold">{fmtBrl(cenario.receita_bruta_total)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Custo Total</p>
            <p className="text-sm font-semibold">{fmtBrl(cenario.custo_total)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Margem Contrib.</p>
            <p className={`text-sm font-bold ${margemPositiva ? "text-emerald-600" : "text-destructive"}`}>
              {fmtBrl(margem)}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Resultado Líquido</p>
            <p className={`text-sm font-bold ${cenario.resultado_liquido_total !== null && cenario.resultado_liquido_total >= 0 ? "text-emerald-600" : "text-destructive"}`}>
              {fmtBrl(cenario.resultado_liquido_total)}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Ponto Equilíbrio</p>
            <p className="text-sm font-semibold">
              {cenario.ponto_equilibrio_sc_ha ? `${fmtNum(cenario.ponto_equilibrio_sc_ha, 1)} sc/ha` : "—"}
            </p>
          </div>
          {cenario.ir_aliquota_pct && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">IR ({fmtNum(cenario.ir_aliquota_pct, 1)}%)</p>
              <p className="text-sm font-semibold text-destructive">{fmtBrl(cenario.ir_valor_total)}</p>
            </div>
          )}
        </div>
      </CardContent>

      <div className="border-t px-4 py-2 bg-slate-50/50 dark:bg-slate-900/50 flex justify-between items-center rounded-b-sm mt-auto">
        <div className="flex flex-col">
          {cenario.calculado_em ? (
            <span className="text-[10px] text-muted-foreground">
              Calculado em {format(new Date(cenario.calculado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })}
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground italic">Não calculado</span>
          )}
        </div>

        <TooltipProvider>
          <div className="flex gap-0 items-center -mr-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="icon" variant="ghost" className="size-7 text-muted-foreground hover:text-emerald-600 rounded-sm" onClick={onView}>
                  <Eye className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent className="rounded-sm text-[10px]">Ver detalhes</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 text-muted-foreground hover:text-emerald-600 rounded-sm"
                  onClick={onDuplicar}
                  disabled={!canManageScenarios}
                >
                  <Copy className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent className="rounded-sm text-[10px]">
                {canManageScenarios ? "Duplicar" : "Disponível no plano Profissional"}
              </TooltipContent>
            </Tooltip>

            {cenario.eh_base && onRecalcular && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="ghost" className="size-7 text-muted-foreground hover:text-emerald-600 rounded-sm" onClick={onRecalcular}>
                    <RefreshCw className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="rounded-sm text-[10px]">Recalcular base</TooltipContent>
              </Tooltip>
            )}

            {!cenario.eh_base && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="ghost" className="size-7 text-muted-foreground hover:text-destructive rounded-sm" onClick={onDelete}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="rounded-sm text-[10px]">Excluir</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TooltipProvider>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Cenario Detail Dialog
// ---------------------------------------------------------------------------

function CenarioDetailDialog({
  cenario,
  open,
  onClose,
}: {
  cenario: Cenario | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!cenario) return null;

  const colunas: ColumnDef<CenarioUnidade>[] = [
    { id: "cultivo", header: "Cultivo", cell: (_, r) => r.cultivo_nome ?? "—" },
    { id: "area", header: "Talhão", cell: (_, r) => r.area_nome ?? "—" },
    { id: "area_ha", header: "Área (ha)", cell: (_, r) => fmtNum(r.area_ha) },
    { id: "produtividade", header: "Produtiv.", cell: (_, r) => r.produtividade_efetiva ? `${fmtNum(r.produtividade_efetiva, 1)} sc/ha` : "—" },
    { id: "preco", header: "Preço/sc", cell: (_, r) => fmtBrl(r.preco_efetivo) },
    { id: "custo_ha", header: "Custo/ha", cell: (_, r) => fmtBrl(r.custo_ha_efetivo) },
    { id: "receita", header: "Receita", cell: (_, r) => fmtBrl(r.receita_bruta) },
    { id: "custo", header: "Custo", cell: (_, r) => fmtBrl(r.custo_total) },
    {
      id: "margem_pct", header: "Margem %",
      cell: (_, r) => (
        <span className={r.margem_pct !== null && r.margem_pct >= 0 ? "text-green-600 font-medium" : "text-destructive font-medium"}>
          {fmtPct(r.margem_pct)}
        </span>
      ),
    },
    { id: "depreciacao", header: "Deprec.", cell: (_, r) => fmtBrl(r.depreciacao_total) },
    { id: "ir_valor", header: "IR", cell: (_, r) => fmtBrl(r.ir_valor) },
    {
      id: "resultado_liq", header: "Resultado Líq.",
      cell: (_, r) => (
        <span className={r.resultado_liquido !== null && r.resultado_liquido >= 0 ? "text-emerald-600 font-medium" : "text-destructive font-medium"}>
          {fmtBrl(r.resultado_liquido)}
        </span>
      ),
    },
    {
      id: "fonte",
      header: "Fonte Custo",
      exportable: false,
      sortable: false,
      cell: (_, r) => r.custo_base_fonte ? (
        <Badge variant="outline" className="text-[10px] rounded-sm font-normal">{r.custo_base_fonte}</Badge>
      ) : null,
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-5xl">
        <DialogHeader>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
                <Eye className="size-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <DialogTitle className="text-base leading-tight dark:text-emerald-300">
                  {cenario.nome}
                </DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Detalhamento técnico das unidades produtivas
                </p>
              </div>
            </div>
            <Badge variant={TIPO_BADGE[cenario.tipo] as "default" | "secondary" | "destructive" | "outline"} className="rounded-sm font-normal text-[10px] mr-8">
              {TIPO_LABELS[cenario.tipo]}
            </Badge>
          </div>
        </DialogHeader>

        <DialogBody className="space-y-6 overflow-y-auto max-h-[70vh]">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KPICard
              label="Receita Bruta"
              value={fmtBrl(cenario.receita_bruta_total)}
              subtitle={`${fmtNum(cenario.area_total_ha)} ha`}
              icon={DollarSign}
              tone="success"
              valueSize="base"
            />
            <KPICard
              label="Custo Total"
              value={fmtBrl(cenario.custo_total)}
              icon={TrendingDown}
              tone="warning"
              valueSize="base"
            />
            <KPICard
              label="Margem de Contribuição"
              value={fmtBrl(cenario.margem_contribuicao_total)}
              subtitle={cenario.receita_bruta_total && cenario.margem_contribuicao_total
                ? fmtPct((cenario.margem_contribuicao_total / cenario.receita_bruta_total) * 100)
                : undefined}
              icon={TrendingUp}
              tone="info"
              valueSize="base"
            />
            <KPICard
              label="Resultado Líquido"
              value={fmtBrl(cenario.resultado_liquido_total)}
              subtitle={cenario.ir_aliquota_pct ? `IR ${fmtNum(cenario.ir_aliquota_pct, 1)}%` : undefined}
              icon={TrendingUp}
              tone="success"
              valueSize="base"
            />
            <KPICard
              label="Ponto de Equilíbrio"
              value={cenario.ponto_equilibrio_sc_ha ? `${fmtNum(cenario.ponto_equilibrio_sc_ha, 1)} sc/ha` : "—"}
              icon={Wheat}
              tone="default"
              valueSize="base"
            />
          </div>

          <div className="rounded-sm border overflow-hidden bg-background">
            <DataTable
              columns={colunas}
              data={cenario.unidades}
              searchable={true}
              searchPlaceholder="Buscar por cultivo ou talhão..."
              exportable={true}
              exportFileName={`cenario-${cenario.nome.toLowerCase().replace(/\s+/g, "-")}`}
            />
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} className="rounded-sm">
            <X className="size-3 mr-2" />
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Cenario Form Dialog
// ---------------------------------------------------------------------------

function CenarioFormDialog({
  open,
  onClose,
  onSave,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (data: CenarioFormData) => void;
  loading: boolean;
}) {
  const form = useForm<CenarioFormData>({
    resolver: zodResolver(cenarioFormSchema),
    defaultValues: {
      nome: "",
      descricao: "",
      tipo: "CUSTOM",
      produtividade_default: "",
      preco_default: "",
      custo_ha_default: "",
      fator_custo_pct: "",
      ir_aliquota_pct: "",
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        nome: "",
        descricao: "",
        tipo: "CUSTOM",
        produtividade_default: "",
        preco_default: "",
        custo_ha_default: "",
        fator_custo_pct: "",
        ir_aliquota_pct: "",
      });
    }
  }, [open, form]);

  function onSubmit(data: CenarioFormData) {
    onSave(data);
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
              <TrendingUp className="size-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <DialogTitle className="text-base leading-tight dark:text-emerald-300">
                Novo Cenário Econômico
              </DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Simule variações de produtividade, preço e custos
              </p>
            </div>
          </div>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogBody className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="nome"
                  render={({ field }) => (
                    <FormItem className="col-span-2 space-y-1">
                      <FormLabel className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Nome do Cenário *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Ex: Projeção de Safra Otimista"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="tipo"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Tipo de Cenário *</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder={field.value ? TIPO_LABELS[field.value] : "Selecione..."} />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="OTIMISTA">Otimista</SelectItem>
                          <SelectItem value="PESSIMISTA">Pessimista</SelectItem>
                          <SelectItem value="CUSTOM">Personalizado</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="fator_custo_pct"
                  render={({ field }) => (
                    <FormItem className="space-y-1">
                      <FormLabel className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Fator de Custo (%) *</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Ex: 0,85 = −15%"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="ir_aliquota_pct"
                render={({ field }) => (
                  <FormItem className="space-y-1">
                    <FormLabel className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Alíquota IR %</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Ex: 15,0 (Lucro Presumido)" />
                    </FormControl>
                    <FormDescription className="text-[10px]">Opcional — deixe em branco para não aplicar IR</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="space-y-3 p-3 bg-emerald-50/30 dark:bg-emerald-900/10 rounded-sm border border-emerald-100/30 dark:border-emerald-800/30">
                <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">Valores Padrão para Simulação</p>
                <div className="grid grid-cols-3 gap-3">
                  <FormField
                    control={form.control}
                    name="produtividade_default"
                    render={({ field }) => (
                      <FormItem className="space-y-1">
                        <FormLabel className="text-[10px] font-medium">Produtiv. *</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="55,0" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="preco_default"
                    render={({ field }) => (
                      <FormItem className="space-y-1">
                        <FormLabel className="text-[10px] font-medium">Preço *</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="130,00" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="custo_ha_default"
                    render={({ field }) => (
                      <FormItem className="space-y-1">
                        <FormLabel className="text-[10px] font-medium">Custo/ha *</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="4500,00" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              <FormField
                control={form.control}
                name="descricao"
                render={({ field }) => (
                  <FormItem className="space-y-1">
                    <FormLabel className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Descrição</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        className="min-h-[70px] resize-none"
                        placeholder="Descreva as premissas deste cenário..."
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </DialogBody>

            <DialogFooter className="mt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="outline"
                size="sm"
                disabled={loading}
              >
                {loading ? (
                  <RefreshCw className="size-3 mr-2 animate-spin" />
                ) : (
                  <Plus className="size-3 mr-2" />
                )}
                {loading ? "Salvando..." : "Criar Cenário"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Comparativo Dialog
// ---------------------------------------------------------------------------

function ComparativoDialog({
  cenarios,
  open,
  onClose,
}: {
  cenarios: Cenario[];
  open: boolean;
  onClose: () => void;
}) {
  if (cenarios.length < 2) return null;

  const melhorMargem = Math.max(...cenarios.map(c => c.margem_contribuicao_total ?? -Infinity));
  const piorMargem = Math.min(...cenarios.map(c => c.margem_contribuicao_total ?? Infinity));

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
              <BarChart2 className="size-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <DialogTitle className="text-base leading-tight text-emerald-800 dark:text-emerald-300">
                Comparativo de Cenários
              </DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Análise lado a lado de margem e rentabilidade
              </p>
            </div>
          </div>
        </DialogHeader>

        <DialogBody className="space-y-4">
          <div className="overflow-x-auto rounded-sm border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="text-left py-3 px-4 text-[11px] uppercase tracking-wider text-muted-foreground font-bold">Métrica</th>
                  {cenarios.map(c => (
                    <th key={c.id} className="text-right py-3 px-4 font-semibold min-w-[140px]">
                      <div className="flex flex-col items-end gap-1">
                        <span className="text-foreground text-sm">{c.nome}</span>
                        <Badge variant={TIPO_BADGE[c.tipo] as "default" | "secondary" | "destructive" | "outline"} className="text-[10px] h-4 px-1 rounded-sm font-normal">
                          {TIPO_LABELS[c.tipo]}
                        </Badge>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label: "Área Total (ha)", fn: (c: Cenario) => fmtNum(c.area_total_ha) },
                  { label: "Receita Bruta", fn: (c: Cenario) => fmtBrl(c.receita_bruta_total) },
                  { label: "Custo Total", fn: (c: Cenario) => fmtBrl(c.custo_total) },
                  {
                    label: "Margem de Contribuição",
                    fn: (c: Cenario) => (
                      <span className={
                        c.margem_contribuicao_total === melhorMargem && cenarios.length > 1
                          ? "text-emerald-600 font-bold"
                          : c.margem_contribuicao_total === piorMargem && cenarios.length > 1
                            ? "text-destructive font-bold"
                            : "font-medium"
                      }>
                        {fmtBrl(c.margem_contribuicao_total)}
                      </span>
                    ),
                  },
                  {
                    label: "Margem %",
                    fn: (c: Cenario) => c.receita_bruta_total && c.margem_contribuicao_total !== null
                      ? <span className="font-medium">{fmtPct((c.margem_contribuicao_total / c.receita_bruta_total) * 100)}</span>
                      : "—",
                  },
                  { label: "Depreciação", fn: (c: Cenario) => fmtBrl(c.depreciacao_total) },
                  { label: "IR", fn: (c: Cenario) => fmtBrl(c.ir_valor_total) },
                  {
                    label: "Resultado Líquido",
                    fn: (c: Cenario) => (
                      <span className={c.resultado_liquido_total !== null && c.resultado_liquido_total >= 0 ? "text-emerald-600 font-bold" : "text-destructive font-bold"}>
                        {fmtBrl(c.resultado_liquido_total)}
                      </span>
                    ),
                  },
                  { label: "Ponto de Equilíbrio", fn: (c: Cenario) => c.ponto_equilibrio_sc_ha ? `${fmtNum(c.ponto_equilibrio_sc_ha, 1)} sc/ha` : "—" },
                ].map(({ label, fn }, idx) => (
                  <tr key={label} className={`border-b last:border-0 hover:bg-muted/30 ${idx % 2 === 0 ? "bg-background" : "bg-muted/10"}`}>
                    <td className="py-2.5 px-4 text-muted-foreground font-medium">{label}</td>
                    {cenarios.map(c => (
                      <td key={c.id} className="py-2.5 px-4 text-right tabular-nums">{fn(c)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} className="rounded-sm">
            <X className="size-3 mr-2" />
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CenariosPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: safraId } = use(params);
  const qc = useQueryClient();

  const [formOpen, setFormOpen] = useState(false);
  const searchParams = useSearchParams();
  const [detailCenario, setDetailCenario] = useState<Cenario | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Cenario | null>(null);
  const [duplicarTarget, setDuplicarTarget] = useState<Cenario | null>(null);
  const [duplicarNome, setDuplicarNome] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparativoOpen, setComparativoOpen] = useState(false);
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const { data: safra } = useQuery<Safra>({
    queryKey: ["safra", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}`),
  });
  const safraLabel = safra ? getSafraLabel(safra) : "Safra";

  const { data: cenarios = [], isLoading } = useQuery<Cenario[]>({
    queryKey: ["cenarios", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/cenarios`),
  });

  useEffect(() => {
    const ajusteSugerido = searchParams.get("ajuste_sugerido");
    const cenarioId = searchParams.get("cenario_id");
    const actionId = searchParams.get("action_id");

    if (ajusteSugerido === "true" && cenarioId && cenarios.length > 0) {
      const cenario = cenarios.find(c => c.id === cenarioId);
      if (cenario) {
        setDetailCenario(cenario);
        
        // Step 201: Concluir ação assistida se houver
        if (actionId) {
          apiFetch(`/ia/acoes-assistidas/${actionId}/concluir`, { method: "PATCH" }).catch(() => {});
        }

        toast("Copiloto: Analisando Ajuste Sugerido", {
          description: `Abrindo detalhes do cenário "${cenario.nome}" para sua conferência.`,
          icon: <Sparkles className="size-4 text-emerald-600" />,
        });
      }
    }
  }, [searchParams, cenarios]);

  const createMut = useMutation({
    mutationFn: (body: object) =>
      apiFetch<Cenario>(`/safras/${safraId}/cenarios`, { method: "POST", body }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cenarios", safraId] }); toast.success("Cenário criado!"); setFormOpen(false); },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/safras/${safraId}/cenarios/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cenarios", safraId] }); toast.success("Cenário excluído."); setDeleteTarget(null); },
    onError: (e: Error) => toast.error(e.message),
  });

  const duplicarMut = useMutation({
    mutationFn: ({ id, nome }: { id: string; nome: string }) =>
      apiFetch<Cenario>(`/safras/${safraId}/cenarios/${id}/duplicar`, { method: "POST", body: { nome } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cenarios", safraId] }); toast.success("Cenário duplicado!"); setDuplicarTarget(null); },
    onError: (e: Error) => toast.error(e.message),
  });

  const recalcularMut = useMutation({
    mutationFn: () =>
      apiFetch<Cenario>(`/safras/${safraId}/cenarios/base/recalcular`, { method: "POST" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cenarios", safraId] }); toast.success("Base recalculada com dados atuais."); },
    onError: (e: Error) => toast.error(e.message),
  });

  function handleCreate(data: CenarioFormData) {
    createMut.mutate({
      nome: data.nome,
      descricao: data.descricao || null,
      tipo: data.tipo,
      produtividade_default: parseFld(data.produtividade_default) ?? null,
      preco_default: parseFld(data.preco_default) ?? null,
      custo_ha_default: parseFld(data.custo_ha_default) ?? null,
      fator_custo_pct: parseFld(data.fator_custo_pct) ?? null,
      ir_aliquota_pct: data.ir_aliquota_pct ? (parseFld(data.ir_aliquota_pct) ?? null) : null,
    });
  }

  const cenariosSelecionados = cenarios.filter(c => selectedIds.includes(c.id));

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full" />)}
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title={safra ? `Cenários Econômicos — ${safraLabel}` : "Cenários Econômicos"}
        description="Simule hipóteses de produtividade, preço e custo para esta safra"
        icon={<BarChart2 className="text-emerald-600" size={22} />}
        actions={
          <div className="flex gap-2">
            {hasProfessionalTier && selectedIds.length >= 2 && (
              <Button variant="outline" size="sm" asChild className="rounded-sm">
                <Link href={`/agricola/safras/${safraId}/cenarios/comparativo`}>
                  <BarChart2 className="size-3.5 mr-1.5" />
                  Comparar ({selectedIds.length})
                </Link>
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFormOpen(true)}
              disabled={!hasProfessionalTier}
              title={hasProfessionalTier ? undefined : "Disponível no plano Profissional"}
              className="rounded-sm"
            >
              <Plus className="size-3.5 mr-1.5" />
              Novo Cenário
            </Button>
          </div>
        }
      />

      {cenarios.length === 0 ? (
        <Card className="shadow-sm rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
            <Wheat className="size-8" />
            <p className="text-sm">Nenhum cenário encontrado para esta safra.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {cenarios.map(cenario => (
            <div key={cenario.id} className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-4 accent-primary"
                checked={selectedIds.includes(cenario.id)}
                onChange={e => setSelectedIds(prev =>
                  e.target.checked ? [...prev, cenario.id] : prev.filter(i => i !== cenario.id)
                )}
              />
              <div className="flex-1">
                <CenarioCard
                  cenario={cenario}
                  onView={() => setDetailCenario(cenario)}
                  onDuplicar={() => {
                    if (!hasProfessionalTier) return;
                    setDuplicarTarget(cenario);
                    setDuplicarNome(`${cenario.nome} (cópia)`);
                  }}
                  onDelete={() => setDeleteTarget(cenario)}
                  onRecalcular={cenario.eh_base ? () => recalcularMut.mutate() : undefined}
                  canManageScenarios={hasProfessionalTier}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form de criação */}
      <CenarioFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSave={handleCreate}
        loading={createMut.isPending}
      />

      {/* Detalhe do cenário */}
      <CenarioDetailDialog
        cenario={detailCenario}
        open={!!detailCenario}
        onClose={() => setDetailCenario(null)}
      />

      {/* Comparativo */}
      <ComparativoDialog
        cenarios={cenariosSelecionados}
        open={comparativoOpen}
        onClose={() => setComparativoOpen(false)}
      />

      {/* Confirmar exclusão */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Excluir Cenário?"
        description={`O cenário "${deleteTarget?.nome}" será removido permanentemente. Esta ação não pode ser desfeita.`}
        destructive
        confirmText="Excluir"
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Duplicar */}
      <Dialog open={!!duplicarTarget} onOpenChange={() => setDuplicarTarget(null)}>
        <DialogContent className="max-w-sm rounded-sm border-l-4 border-l-emerald-500">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300">
              <div className="bg-emerald-100 dark:bg-emerald-900/40 p-1.5 rounded-sm">
                <Copy className="size-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              <span>Duplicar Cenário</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Nome do novo cenário</Label>
            <Input
              value={duplicarNome}
              onChange={e => setDuplicarNome(e.target.value)}
              placeholder="Digite o nome do novo cenário..."
            />
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDuplicarTarget(null)} className="rounded-sm">
              <X className="size-3 mr-2" />
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!duplicarNome.trim() || duplicarMut.isPending}
              onClick={() => duplicarTarget && duplicarMut.mutate({ id: duplicarTarget.id, nome: duplicarNome })}
              className="rounded-sm border-emerald-600/50 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 hover:border-emerald-600 transition-all"
            >
              {duplicarMut.isPending ? (
                <RefreshCw className="size-3 mr-2 animate-spin" />
              ) : (
                <Copy className="size-3 mr-2" />
              )}
              {duplicarMut.isPending ? "Duplicando..." : "Duplicar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
