"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useHasModule, useModules } from "@/hooks/use-has-module";
import { usePermission } from "@/hooks/use-permission";
import { apiFetch } from "@/lib/api";
import type { ModuleId } from "@/types/global";
import { useAppStore } from "@/lib/stores/app-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { DashboardAlertsCard, type AlertSummaryPayload } from "@/components/dashboard/dashboard-alerts-card";
import { DashboardCopilotCard } from "@/components/dashboard/dashboard-copilot-card";
import { FirstStepsCard } from "@/components/dashboard/first-steps-card";
import { DashboardActionGrid } from "@/components/dashboard/dashboard-action-grid";
import { DashboardPageSkeleton, TenantSelectionPrompt } from "@/components/dashboard/dashboard-states";
import { DomainMiniCard, MetricCard } from "@/components/dashboard/dashboard-metric-card";
import { SectionShell, SectionSkeleton } from "@/components/dashboard/dashboard-section";
import {
  ArrowRight,
  BarChart3,
  Beef,
  LayoutDashboard,
  MapPinned,
  Sprout,
  Tractor,
  TrendingUp,
  Wallet,
  Waves,
  AlertTriangle,
  CalendarDays,
  Activity,
  PlusCircle,
  Package,
  BookOpen,
  ClipboardList,
  CheckCircle2,
  RotateCcw
} from "lucide-react";

type DashboardFinanceiroResumo = {
  data_referencia: string;
  unidade_produtiva_id: string | null;
  total_recebido_mes: number;
  total_pago_mes: number;
  saldo_mes: number;
  total_a_receber: number;
  total_a_pagar: number;
  total_atrasado_receitas: number;
  total_atrasado_despesas: number;
  vencendo_7d: Array<{
    id: string;
    tipo: "RECEITA" | "DESPESA";
    descricao: string;
    valor: number;
    data_vencimento: string;
    dias_restantes: number;
    pessoa_nome: string | null;
  }>;
  vencendo_8_15d: Array<{
    id: string;
    tipo: "RECEITA" | "DESPESA";
    descricao: string;
    valor: number;
    data_vencimento: string;
    dias_restantes: number;
    pessoa_nome: string | null;
  }>;
  vencendo_16_30d: Array<{
    id: string;
    tipo: "RECEITA" | "DESPESA";
    descricao: string;
    valor: number;
    data_vencimento: string;
    dias_restantes: number;
    pessoa_nome: string | null;
  }>;
  alertas: Array<{
    tipo: string;
    nivel: "INFO" | "ALERTA" | "CRITICO";
    mensagem: string;
    valor: number;
    data_referencia: string | null;
  }>;
};

type DashboardResumoOperacionalDominio = {
  pendentes: number;
  em_execucao: number;
  atrasadas: number;
  concluidas: number;
};

type DashboardResumoOperacional = DashboardResumoOperacionalDominio & {
  agricultura: DashboardResumoOperacionalDominio;
  pecuaria: DashboardResumoOperacionalDominio;
};

type AgricolaDashboardResumo = {
  kpis: {
    total_safras_ativas: number;
    total_safras_encerradas: number;
    area_total_ha: number;
    custo_acumulado: number;
    meta_producao_sc: number;
    sacas_colhidas: number;
    receita_colheita: number;
    total_alertas: number;
  };
  safras_por_fase?: Record<string, Array<Record<string, unknown>>>;
  alertas_checklist?: Array<Record<string, unknown>>;
  alertas_nde?: Array<Record<string, unknown>>;
  fenologia_atual?: Array<Record<string, unknown>>;
};

type PecuariaDashboardResumo = {
  animais_ativos: number;
  lotes_ativos: number;
  piquetes_ativos: number;
  peso_total_kg: number;
  peso_medio_kg: number;
  manejos_pendentes: number;
  vacinacoes_pendentes: number;
  custo_sanitario_acumulado: number;
};

type DomainProfile = {
  hasAgriculture: boolean;
  hasLivestock: boolean;
  hasFinance: boolean;
  isMixed: boolean;
};

const AGRICULTURE_MODULES: ModuleId[] = ["A1_PLANEJAMENTO", "A2_CAMPO", "A3_DEFENSIVOS", "A4_PRECISAO", "A5_COLHEITA"];
const LIVESTOCK_MODULES: ModuleId[] = ["P1_REBANHO", "P2_GENETICA", "P3_CONFINAMENTO", "P4_LEITE"];
const FINANCE_MODULES: ModuleId[] = ["F1_TESOURARIA", "F2_CUSTOS_ABC", "F3_FISCAL", "F4_HEDGING"];

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatKg(value: number): string {
  return `${value.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg`;
}

function formatArea(value: number): string {
  return `${value.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ha`;
}

function formatCount(value: number): string {
  return value.toLocaleString("pt-BR");
}

function buildProfile(activeModules: ModuleId[], hasFinance: boolean): DomainProfile {
  const hasAgriculture = activeModules.some((moduleId) => AGRICULTURE_MODULES.includes(moduleId));
  const hasLivestock = activeModules.some((moduleId) => LIVESTOCK_MODULES.includes(moduleId));

  return {
    hasAgriculture,
    hasLivestock,
    hasFinance,
    isMixed: hasAgriculture && hasLivestock,
  };
}

function hasFinancialData(data: DashboardFinanceiroResumo | undefined): boolean {
  if (!data) return false;
  return Boolean(
    data.total_recebido_mes ||
      data.total_pago_mes ||
      data.saldo_mes ||
      data.total_a_receber ||
      data.total_a_pagar ||
      data.total_atrasado_receitas ||
      data.total_atrasado_despesas ||
      data.alertas.length ||
      data.vencendo_7d.length ||
      data.vencendo_8_15d.length ||
      data.vencendo_16_30d.length,
  );
}

function hasAgricolaData(data: AgricolaDashboardResumo | undefined): boolean {
  if (!data) return false;
  const { kpis } = data;
  return Boolean(
    kpis.total_safras_ativas ||
      kpis.total_safras_encerradas ||
      kpis.area_total_ha ||
      kpis.custo_acumulado ||
      kpis.meta_producao_sc ||
      kpis.sacas_colhidas ||
      kpis.receita_colheita ||
      kpis.total_alertas,
  );
}

function hasPecuariaData(data: PecuariaDashboardResumo | undefined): boolean {
  if (!data) return false;
  return Boolean(
    data.animais_ativos ||
      data.lotes_ativos ||
      data.piquetes_ativos ||
      data.peso_total_kg ||
      data.peso_medio_kg ||
      data.manejos_pendentes ||
      data.vacinacoes_pendentes ||
      data.custo_sanitario_acumulado,
  );
}

function buildCopilotSubtitle(profile: DomainProfile): string {
  if (profile.isMixed) {
    return "Posso ajudar a cruzar sinais de Agricultura, Pecuária, Operacional e Financeiro.";
  }

  if (profile.hasAgriculture) {
    return "Posso ajudar a interpretar safra, operações, custos agrícolas e alertas da fazenda.";
  }

  if (profile.hasLivestock) {
    return "Posso ajudar a interpretar lotes, pesagens, vacinação, custo sanitário e manejos pendentes.";
  }

  return "Posso ajudar a interpretar os principais indicadores da fazenda.";
}

function buildCopilotHighlights({
  profile,
  financeData,
  operationalData,
  agricolaData,
  pecuariaData,
}: {
  profile: DomainProfile;
  financeData: DashboardFinanceiroResumo | undefined;
  operationalData: DashboardResumoOperacional | undefined;
  agricolaData: AgricolaDashboardResumo | undefined;
  pecuariaData: PecuariaDashboardResumo | undefined;
}): string[] {
  const highlights = [
    financeData ? "O financeiro consolidado está disponível para interpretação." : null,
    operationalData && (operationalData.pendentes > 0 || operationalData.atrasadas > 0)
      ? "Há tarefas operacionais pendentes para priorização."
      : null,
    profile.hasAgriculture && agricolaData
      ? agricolaData.kpis.total_alertas > 0
        ? "Há alertas agrícolas e indicadores de safra para leitura."
        : "Há indicadores agrícolas consolidados para análise."
      : null,
    profile.hasLivestock && pecuariaData
      ? pecuariaData.manejos_pendentes > 0 || pecuariaData.vacinacoes_pendentes > 0
        ? "Existem manejos pecuários pendentes e rotinas sanitárias a acompanhar."
        : "Há custo sanitário e leitura zootécnica disponíveis."
      : null,
  ].filter((item): item is string => Boolean(item));

  return highlights.slice(0, 4);
}

function DashboardContent() {
  const { tenant, user, activeFazendaId, unidadesProdutivasAutorizadas, _hasHydrated, impersonation } = useAppStore();
  const activeModules = useModules();
  const hasFinance = useHasModule(FINANCE_MODULES[0]) || activeModules.some((moduleId) => FINANCE_MODULES.includes(moduleId));
  const hasAgricultureGate = useHasModule(AGRICULTURE_MODULES[0]) || activeModules.some((moduleId) => AGRICULTURE_MODULES.includes(moduleId));
  const hasLivestockGate = useHasModule(LIVESTOCK_MODULES[0]) || activeModules.some((moduleId) => LIVESTOCK_MODULES.includes(moduleId));
  const profile = buildProfile(activeModules, hasFinance);
  const fazendaAtual = unidadesProdutivasAutorizadas.find((fazenda) => fazenda.id === activeFazendaId);
  const contextoLabel = fazendaAtual?.nome ?? tenant?.nome ?? "Contexto atual";
  const isImpersonating = Boolean(impersonation?.active);
  const isReady = _hasHydrated && !!tenant && (!user?.is_superuser || isImpersonating);

  const canViewSafras = usePermission("agricola:safras:view");
  const canViewTarefas = usePermission("campo:tarefas:view");
  const canViewEstoque = usePermission("estoque:movimentacoes:view");
  const canViewFinanceiro = usePermission("financeiro:dashboard:view");
  const canViewPecuaria = usePermission("pecuaria:dashboard:view");

  const financeiroQuery = useQuery<DashboardFinanceiroResumo>({
    queryKey: ["dashboard-executivo-financeiro", activeFazendaId],
    queryFn: () => apiFetch("/relatorios/dashboard"),
    staleTime: 30_000,
    enabled: isReady && profile.hasFinance,
  });

  const operacionalQuery = useQuery<DashboardResumoOperacional>({
    queryKey: ["dashboard-executivo-operacional", activeFazendaId],
    queryFn: () => apiFetch("/operacional/dashboard/resumo-operacional"),
    staleTime: 30_000,
    enabled: isReady,
  });

  const agricolaQuery = useQuery<AgricolaDashboardResumo>({
    queryKey: ["dashboard-executivo-agricola", activeFazendaId],
    queryFn: () => apiFetch("/agricola/dashboard/"),
    staleTime: 30_000,
    enabled: isReady && hasAgricultureGate,
  });

  const pecuariaQuery = useQuery<PecuariaDashboardResumo>({
    queryKey: ["dashboard-executivo-pecuaria", activeFazendaId],
    queryFn: () => apiFetch("/pecuaria/dashboard/resumo-executivo"),
    staleTime: 30_000,
    enabled: isReady && hasLivestockGate,
  });

  const alertSummaryQuery = useQuery<AlertSummaryPayload>({
    queryKey: ["dashboard-executivo-alert-summary", activeFazendaId],
    queryFn: () => apiFetch("/alerts/summary"),
    staleTime: 30_000,
    enabled: isReady,
  });

  if (user?.is_superuser && !isImpersonating) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <EmptyState
          icon={<LayoutDashboard />}
          title="Bem-vindo, Administrador SaaS"
          description="Você está no modo de gestão global da plataforma. Selecione um cliente ou acesse o painel administrativo."
          action={{ label: "Gestão de Assinantes", href: "/dashboard/backoffice/tenants" }}
          secondaryAction={{ label: "Painel Backoffice", href: "/dashboard/backoffice/dashboard" }}
        />
      </div>
    );
  }

  const statusLabel = profile.isMixed
    ? "Fazenda mista"
    : profile.hasAgriculture
      ? "Perfil agrícola"
      : profile.hasLivestock
        ? "Perfil pecuário"
        : "Perfil operacional";

  const financeData = financeiroQuery.data;
  const operationalData = operacionalQuery.data;
  const agricolaData = agricolaQuery.data;
  const pecuariaData = pecuariaQuery.data;
  const financeValue = financeData ? financeData.total_recebido_mes - financeData.total_pago_mes : 0;
  const copilotSubtitle = buildCopilotSubtitle(profile);
  const copilotHighlights = buildCopilotHighlights({
    profile,
    financeData,
    operationalData,
    agricolaData,
    pecuariaData,
  });
  const copilotIsLoading =
    financeiroQuery.isLoading || operacionalQuery.isLoading || agricolaQuery.isLoading || pecuariaQuery.isLoading;
  const firstStepsIsLoading =
    !_hasHydrated || operacionalQuery.isLoading || (hasAgricultureGate && agricolaQuery.isLoading) || (profile.hasFinance && financeiroQuery.isLoading);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Visão do Dia"
        description={`Central operacional de ${contextoLabel}. O que precisa da sua atenção agora.`}
        icon={<LayoutDashboard className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Visão do Dia" },
        ]}
      />

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="rounded-sm">
          {statusLabel}
        </Badge>
        {profile.isMixed && <Badge className="rounded-sm bg-primary/10 text-primary border-primary/20">Ambos os domínios</Badge>}
        {!profile.hasFinance && <Badge variant="outline" className="rounded-sm">Financeiro indisponível</Badge>}
        {!profile.hasAgriculture && <Badge variant="outline" className="rounded-sm">Agricultura indisponível</Badge>}
        {!profile.hasLivestock && <Badge variant="outline" className="rounded-sm">Pecuária indisponível</Badge>}
      </div>

      {/* CENTRAL DE COMANDOS & ATALHOS OPERACIONAIS (Todos disponíveis e agrupados em formato de botão com ícone e descritivo) */}
      <DashboardActionGrid
        hasAgriculture={profile.hasAgriculture}
        hasFinance={profile.hasFinance}
        hasLivestock={profile.hasLivestock}
        canViewSafras={canViewSafras}
        canViewTarefas={canViewTarefas}
        canViewEstoque={canViewEstoque}
        canViewFinanceiro={canViewFinanceiro}
        canViewPecuaria={canViewPecuaria}
      />

      {/* PRECISA DE ATENÇÃO (Prioridade máxima de acompanhamento) */}
      <div className="flex flex-col gap-6">
        <SectionShell
          title="Precisa de atenção"
          description="Pendências críticas e alertas que exigem ação imediata."
        >
          {(() => {
            const hasOverdueTasks = operationalData && operationalData.atrasadas > 0;
            const hasOverduePayables = financeData && financeData.vencendo_7d.length > 0;
            const isAllClear = !operacionalQuery.isLoading && !financeiroQuery.isLoading && !hasOverdueTasks && !hasOverduePayables;

            return (
              <div className="space-y-4">
                {(hasOverdueTasks || hasOverduePayables) && (
                  <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
                    {hasOverdueTasks && (
                      <div className="rounded-sm border border-rose-200 bg-rose-50/50 p-4 shadow-sm dark:bg-rose-950/20 dark:border-rose-900/50 flex flex-col gap-2 relative overflow-hidden">
                        <div className="absolute right-0 top-0 opacity-5 pointer-events-none">
                          <AlertTriangle className="size-24 -mt-4 -mr-4" />
                        </div>
                        <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold text-sm z-10">
                          <AlertTriangle className="size-4" />
                          <span>Tarefas Vencidas</span>
                        </div>
                        <p className="text-3xl font-bold text-rose-700 dark:text-rose-400 z-10">{formatCount(operationalData.atrasadas)}</p>
                        <Button asChild size="sm" variant="outline" className="mt-2 w-fit bg-white/50 dark:bg-black/20 border-rose-200 hover:bg-rose-100 text-rose-700 dark:border-rose-800 dark:hover:bg-rose-900/50 dark:text-rose-300 z-10">
                          <Link href="/dashboard/operacional/campo/tarefas">Ver tarefas</Link>
                        </Button>
                      </div>
                    )}
                    
                    {hasOverduePayables && (
                      <div className="rounded-sm border border-amber-200 bg-amber-50/50 p-4 shadow-sm dark:bg-amber-950/20 dark:border-amber-900/50 flex flex-col gap-2 relative overflow-hidden">
                        <div className="absolute right-0 top-0 opacity-5 pointer-events-none">
                          <Wallet className="size-24 -mt-4 -mr-4" />
                        </div>
                        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold text-sm z-10">
                          <Wallet className="size-4" />
                          <span>Contas a Vencer (7d)</span>
                        </div>
                        <p className="text-3xl font-bold text-amber-700 dark:text-amber-400 z-10">{financeData.vencendo_7d.length}</p>
                        <Button asChild size="sm" variant="outline" className="mt-2 w-fit bg-white/50 dark:bg-black/20 border-amber-200 hover:bg-amber-100 text-amber-700 dark:border-amber-800 dark:hover:bg-amber-900/50 dark:text-amber-300 z-10">
                          <Link href="/dashboard/financeiro/contas-pagar">Ver contas</Link>
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {isAllClear && (
                  <div className="rounded-sm border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="size-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Nenhuma pendência crítica no momento</p>
                        <p className="text-xs text-muted-foreground">Não há tarefas atrasadas nem contas urgentes vencendo nos próximos 7 dias.</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-2">
                  <DashboardAlertsCard
                    summary={alertSummaryQuery.data}
                    isLoading={alertSummaryQuery.isLoading}
                    isError={alertSummaryQuery.isError}
                    onRetry={() => alertSummaryQuery.refetch()}
                  />
                </div>
              </div>
            );
          })()}
        </SectionShell>

        {/* PRÓXIMAS ATIVIDADES & COPILOT */}
        <SectionShell
          title="Próximas atividades"
          description="Tarefas e operações ativas hoje."
        >
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <MetricCard
              label="Tarefas pendentes"
              value={operacionalQuery.isLoading ? "..." : (operationalData ? formatCount(operationalData.pendentes) : "0")}
              description="Aguardando execução ou início"
              icon={<CalendarDays className="size-5 text-slate-600" />}
              tone="bg-slate-500/10"
            />
            <MetricCard
              label="Operações em andamento"
              value={operacionalQuery.isLoading ? "..." : (operationalData ? formatCount(operationalData.em_execucao) : "0")}
              description="Equipe em campo"
              icon={<Activity className="size-5 text-emerald-600" />}
              tone="bg-emerald-500/10"
            />
          </div>
        </SectionShell>

        <DashboardCopilotCard
          subtitle={copilotSubtitle}
          highlights={copilotHighlights}
          ctaLabel="Ver análises da IA"
          ctaHref="/dashboard/ia/resumo"
          isLoading={copilotIsLoading}
        />
        <Button asChild variant="link" className="w-fit px-0 text-xs text-muted-foreground"><Link href="/aprendizado"><BookOpen className="mr-1 size-3.5" aria-hidden="true" />Aprenda a usar melhor a plataforma</Link></Button>
      </div>

      {/* GUIA DE PRIMEIROS PASSOS (Apenas quando houver pendências de configuração inicial) */}
      <FirstStepsCard
        isLoading={firstStepsIsLoading}
        hasProperty={unidadesProdutivasAutorizadas.length > 0}
        hasHarvest={Boolean(agricolaData?.kpis.total_safras_ativas)}
        hasOperation={Boolean(operationalData?.concluidas)}
        hasFinance={profile.hasFinance}
        hasFinanceData={hasFinancialData(financeData)}
      />

      {/* INDICADORES RESUMIDOS */}
      <div className="mt-8 border-t pt-8 space-y-6">
        <h3 className="text-lg font-semibold tracking-tight">Indicadores Resumidos</h3>
        
        {profile.hasFinance && (
          <SectionShell
            title="Financeiro"
            description="Receitas, despesas, resultado operacional e fluxo de caixa."
          >
            {financeiroQuery.isLoading ? (
              <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
            ) : financeiroQuery.isError ? (
              <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-destructive text-sm">
                  <AlertTriangle className="size-4" />
                  <span>Não foi possível carregar os dados financeiros no momento.</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => financeiroQuery.refetch()} className="gap-1.5 h-7 text-xs rounded-sm">
                  <RotateCcw className="size-3.5" />
                  Tentar novamente
                </Button>
              </div>
            ) : financeData && hasFinancialData(financeData) ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Receitas do mês"
                  value={formatCurrency(financeData.total_recebido_mes)}
                  description={`${formatCurrency(financeData.total_a_receber)} a receber`}
                  icon={<TrendingUp className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
                <MetricCard
                  label="Despesas do mês"
                  value={formatCurrency(financeData.total_pago_mes)}
                  description={`${formatCurrency(financeData.total_a_pagar)} a pagar`}
                  icon={<Wallet className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Resultado operacional"
                  value={formatCurrency(financeValue)}
                  description={financeValue >= 0 ? "Saldo positivo (Recebido - Pago)" : "Saldo negativo (Recebido - Pago)"}
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
                <MetricCard
                  label="Saldo de caixa consolidado"
                  value={formatCurrency(financeData.saldo_mes)}
                  description={financeData.total_atrasado_despesas > 0 ? `Atraso: ${formatCurrency(financeData.total_atrasado_despesas)}` : "Sem contas em atraso"}
                  icon={<Waves className="size-5 text-primary" />}
                  tone="bg-primary/10"
                />
              </div>
            ) : (
              <div className="rounded-sm border border-border/50 bg-muted/10 p-4 text-center text-xs text-muted-foreground">
                Nenhuma movimentação financeira consolidada no período.
              </div>
            )}
          </SectionShell>
        )}

        {profile.hasAgriculture && (
          <SectionShell
            title="Agricultura"
            description="Resumo executivo da operação agrícola consolidada."
          >
            {agricolaQuery.isLoading ? (
              <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
            ) : agricolaQuery.isError ? (
              <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-destructive text-sm">
                  <AlertTriangle className="size-4" />
                  <span>Não foi possível carregar os dados agrícolas no momento.</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => agricolaQuery.refetch()} className="gap-1.5 h-7 text-xs rounded-sm">
                  <RotateCcw className="size-3.5" />
                  Tentar novamente
                </Button>
              </div>
            ) : agricolaData && hasAgricolaData(agricolaData) ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Safras ativas"
                  value={formatCount(agricolaData.kpis.total_safras_ativas)}
                  description={`${formatCount(agricolaData.kpis.total_safras_encerradas)} encerradas`}
                  icon={<Sprout className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
                <MetricCard
                  label="Área cultivada"
                  value={formatArea(agricolaData.kpis.area_total_ha)}
                  description="Área agrícola consolidada"
                  icon={<MapPinned className="size-5 text-amber-600" />}
                  tone="bg-amber-500/10"
                />
                <MetricCard
                  label="Custo acumulado"
                  value={formatCurrency(agricolaData.kpis.custo_acumulado)}
                  description="Operações consolidadas"
                  icon={<Wallet className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Alertas agrícolas"
                  value={formatCount(agricolaData.kpis.total_alertas)}
                  description="Pendências e desvios de manejo"
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
              </div>
            ) : (
              <div className="rounded-sm border border-border/50 bg-muted/10 p-4 text-center text-xs text-muted-foreground">
                Nenhuma safra ou área cultivada registrada no contexto atual.
              </div>
            )}
          </SectionShell>
        )}

        {profile.hasLivestock && (
          <SectionShell
            title="Pecuária"
            description="Resumo executivo do rebanho, sanidade e áreas de pastejo."
          >
            {pecuariaQuery.isLoading ? (
              <SectionSkeleton cards={6} columnsClassName="md:grid-cols-2 xl:grid-cols-3" />
            ) : pecuariaQuery.isError ? (
              <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-destructive text-sm">
                  <AlertTriangle className="size-4" />
                  <span>Não foi possível carregar os dados pecuários no momento.</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => pecuariaQuery.refetch()} className="gap-1.5 h-7 text-xs rounded-sm">
                  <RotateCcw className="size-3.5" />
                  Tentar novamente
                </Button>
              </div>
            ) : pecuariaData && hasPecuariaData(pecuariaData) ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <MetricCard
                  label="Animais ativos"
                  value={formatCount(pecuariaData.animais_ativos)}
                  description="Rebanho ativo"
                  icon={<Beef className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
                <MetricCard
                  label="Lotes ativos"
                  value={formatCount(pecuariaData.lotes_ativos)}
                  description="Lotes sob manejo"
                  icon={<Tractor className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
                <MetricCard
                  label="Piquetes ativos"
                  value={formatCount(pecuariaData.piquetes_ativos)}
                  description="Área de pastejo ativa"
                  icon={<MapPinned className="size-5 text-amber-600" />}
                  tone="bg-amber-500/10"
                />
              </div>
            ) : (
              <div className="rounded-sm border border-border/50 bg-muted/10 p-4 text-center text-xs text-muted-foreground">
                Nenhum lote ou animal ativo no contexto atual.
              </div>
            )}
          </SectionShell>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { tenant, user, token, _hasHydrated } = useAppStore();
  const needsTenantSelection = _hasHydrated && !!token && !tenant && !user?.is_superuser;

  if (!_hasHydrated) {
    return <DashboardPageSkeleton />;
  }

  if (needsTenantSelection) {
    return <TenantSelectionPrompt />;
  }

  return <DashboardContent />;
}
