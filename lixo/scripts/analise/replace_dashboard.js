const fs = require('fs');
const file = 'apps/web/src/app/(dashboard)/dashboard/page.tsx';
let content = fs.readFileSync(file, 'utf8');

const importReplacement = `import { DomainMiniCard, MetricCard } from "@/components/dashboard/dashboard-metric-card";
import { SectionShell, SectionSkeleton } from "@/components/dashboard/dashboard-section";
import {
  ArrowRight,
  BarChart3,
  Beef,
  LayoutDashboard,
  Loader2,
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
  BookOpen
} from "lucide-react";`;

content = content.replace(
  /import { DomainMiniCard, MetricCard }.*?\n} from "lucide-react";/s,
  importReplacement
);

const oldReturnStr = `  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Painel Executivo"
        description={\`Visão consolidada da fazenda \${contextoLabel}. Financeiro, operação e domínios especializados em um só lugar.\`}
        icon={<LayoutDashboard className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Executivo" },
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

      {profile.hasFinance && (
        <SectionShell
          title="Financeiro"
          description="Resumo executivo de receitas, despesas, resultado e fluxo de caixa."
          action={
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/financeiro">
                Abrir financeiro
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          }
        >
          {financeiroQuery.isLoading ? (
            <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
          ) : financeiroQuery.isError ? (
            <EmptyState
              icon={<Wallet />}
              title="Não foi possível carregar o resumo financeiro"
              description="Tente recarregar a página para recuperar os indicadores financeiros consolidados."
              action={{ label: "Tentar novamente", onClick: () => financeiroQuery.refetch() }}
            />
          ) : !hasFinancialData(financeData) ? (
            <EmptyState
              icon={<Wallet />}
              title="Sem movimento financeiro consolidado"
              description="Quando houver lançamentos financeiros no contexto ativo, os cartões executivos aparecerão aqui."
              action={{ label: "Abrir financeiro", href: "/dashboard/financeiro" }}
            />
          ) : financeData ? (
            <>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Receitas"
                  value={formatCurrency(financeData.total_recebido_mes)}
                  description={\`\${formatCount(financeData.total_a_receber)} em aberto\`}
                  icon={<TrendingUp className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
                <MetricCard
                  label="Despesas"
                  value={formatCurrency(financeData.total_pago_mes)}
                  description={\`\${formatCount(financeData.total_a_pagar)} em aberto\`}
                  icon={<Wallet className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Resultado"
                  value={formatCurrency(financeValue)}
                  description={financeValue >= 0 ? "Saldo operacional positivo" : "Saldo operacional negativo"}
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
                <MetricCard
                  label="Saldo / Fluxo de caixa"
                  value={formatCurrency(financeData.saldo_mes)}
                  description={\`Atraso: \${formatCurrency(financeData.total_atrasado_despesas)}\`}
                  icon={<Waves className="size-5 text-primary" />}
                  tone="bg-primary/10"
                />
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Fonte oficial: <span className="font-semibold text-foreground">/relatorios/dashboard</span>.
              </p>
            </>
          ) : null}
        </SectionShell>
      )}

      <SectionShell
        title="Operacional"
        description="Visão transversal de tarefas pendentes, em execução, atrasadas e concluídas."
        action={
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/operacional">
              Abrir operacional
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        }
      >
        {operacionalQuery.isLoading ? (
          <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
        ) : operacionalQuery.isError ? (
          <EmptyState
            icon={<Tractor />}
            title="Não foi possível carregar o resumo operacional"
            description="Verifique a conectividade com a API e tente novamente."
            action={{ label: "Tentar novamente", onClick: () => operacionalQuery.refetch() }}
          />
        ) : operationalData ? (
          operationalData.pendentes === 0 &&
          operationalData.em_execucao === 0 &&
          operationalData.atrasadas === 0 &&
          operationalData.concluidas === 0 ? (
            <EmptyState
              icon={<Tractor />}
              title="Nenhuma tarefa operacional registrada"
              description="Quando existirem tarefas agrícolas ou pecuárias, os contadores executivos aparecerão aqui."
              action={{ label: "Abrir tarefas", href: "/dashboard/operacional/campo/tarefas" }}
            />
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Pendentes"
                  value={formatCount(operationalData.pendentes)}
                  description="Tarefas programadas"
                  icon={<Loader2 className="size-5 text-slate-600" />}
                  tone="bg-slate-500/10"
                />
                <MetricCard
                  label="Em execução"
                  value={formatCount(operationalData.em_execucao)}
                  description="Tarefas em andamento"
                  icon={<Tractor className="size-5 text-amber-600" />}
                  tone="bg-amber-500/10"
                />
                <MetricCard
                  label="Atrasadas"
                  value={formatCount(operationalData.atrasadas)}
                  description="Ações fora do prazo"
                  icon={<BarChart3 className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Concluídas"
                  value={formatCount(operationalData.concluidas)}
                  description="Tarefas finalizadas"
                  icon={<TrendingUp className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
              </div>
              {(profile.hasAgriculture || profile.hasLivestock) && (
                <div className="mt-4 grid gap-4 xl:grid-cols-2">
                  {profile.hasAgriculture && <DomainMiniCard title="Agricultura" resumo={operationalData.agricultura} />}
                  {profile.hasLivestock && <DomainMiniCard title="Pecuária" resumo={operationalData.pecuaria} />}
                </div>
              )}
              <p className="mt-4 text-xs text-muted-foreground">
                Resumo operacional consumido de <span className="font-semibold text-foreground">/operacional/dashboard/resumo-operacional</span>.
              </p>
            </>
          )
        ) : null}
      </SectionShell>

      <DashboardAlertsCard
        summary={alertSummaryQuery.data}
        isLoading={alertSummaryQuery.isLoading}
        isError={alertSummaryQuery.isError}
        onRetry={() => alertSummaryQuery.refetch()}
      />

      <DashboardCopilotCard
        subtitle={copilotSubtitle}
        highlights={copilotHighlights}
        ctaLabel="Ver análises"
        ctaHref="/dashboard/ia/resumo"
        isLoading={copilotIsLoading}
      />
      <p className="mt-1 px-1 text-xs text-muted-foreground">
        Leitura assistida baseada nos resumos já carregados nesta tela. Nenhuma ação automática é executada.
      </p>

      {profile.hasAgriculture && (
        <SectionShell
          title="Agricultura"
          description="Resumo executivo da operação agrícola consolidada."
          action={
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola">
                Abrir agrícola
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          }
        >
          {agricolaQuery.isLoading ? (
            <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
          ) : agricolaQuery.isError ? (
            <EmptyState
              icon={<Sprout />}
              title="Não foi possível carregar o resumo agrícola"
              description="Tente novamente para recuperar a consolidação agrícola."
              action={{ label: "Tentar novamente", onClick: () => agricolaQuery.refetch() }}
            />
          ) : agricolaData && hasAgricolaData(agricolaData) ? (
            <>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Safras ativas"
                  value={formatCount(agricolaData.kpis.total_safras_ativas)}
                  description={\`\${formatCount(agricolaData.kpis.total_safras_encerradas)} encerradas\`}
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
                  label="Alertas"
                  value={formatCount(agricolaData.kpis.total_alertas)}
                  description="Pendências e desvios oficiais"
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Indicadores executivos consumidos de <span className="font-semibold text-foreground">/agricola/dashboard/</span>.
              </p>
            </>
          ) : (
            <EmptyState
              icon={<Sprout />}
              title="Nenhuma consolidação agrícola disponível"
              description="Quando houver safras ou área cultivada, os indicadores executivos aparecerão aqui."
              action={{ label: "Abrir agrícola", href: "/dashboard/agricola" }}
            />
          )}
        </SectionShell>
      )}

      {profile.hasLivestock && (
        <SectionShell
          title="Pecuária"
          description="Resumo executivo do rebanho, sanidade e custo sanitário."
          action={
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/pecuaria">
                Abrir pecuária
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          }
        >
          {pecuariaQuery.isLoading ? (
            <SectionSkeleton cards={6} columnsClassName="md:grid-cols-2 xl:grid-cols-3" />
          ) : pecuariaQuery.isError ? (
            <EmptyState
              icon={<Beef />}
              title="Não foi possível carregar o resumo pecuário"
              description="Tente novamente para recuperar os indicadores do rebanho."
              action={{ label: "Tentar novamente", onClick: () => pecuariaQuery.refetch() }}
            />
          ) : pecuariaData && hasPecuariaData(pecuariaData) ? (
            <>
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
                <MetricCard
                  label="Manejos pendentes"
                  value={formatCount(pecuariaData.manejos_pendentes)}
                  description="Tarefas de rebanho abertas"
                  icon={<Loader2 className="size-5 text-slate-600" />}
                  tone="bg-slate-500/10"
                />
                <MetricCard
                  label="Vacinações pendentes"
                  value={formatCount(pecuariaData.vacinacoes_pendentes)}
                  description="Sanidade programada"
                  icon={<Sprout className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Custo sanitário acumulado"
                  value={formatCurrency(pecuariaData.custo_sanitario_acumulado)}
                  description={pecuariaData.peso_medio_kg > 0 ? \`Peso médio: \${formatKg(pecuariaData.peso_medio_kg)}\` : "Fonte sanitária consolidada"}
                  icon={<Wallet className="size-5 text-primary" />}
                  tone="bg-primary/10"
                />
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Fonte oficial: <span className="font-semibold text-foreground">/pecuaria/dashboard/resumo-executivo</span>.
              </p>
            </>
          ) : (
            <EmptyState
              icon={<Beef />}
              title="Nenhuma consolidação pecuária disponível"
              description="Quando houver animais, lotes ou custo sanitário, os indicadores executivos aparecerão aqui."
              action={{ label: "Abrir pecuária", href: "/dashboard/pecuaria" }}
            />
          )}
        </SectionShell>
      )}
    </div>
  );`;

const newReturnStr = `  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Visão do Dia"
        description={\`Central operacional de \${contextoLabel}. O que precisa da sua atenção agora.\`}
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

      <div className="grid gap-6 lg:grid-cols-3">
        {/* PRECISA DE ATENÇÃO & PRÓXIMAS ATIVIDADES */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <SectionShell
            title="Precisa de atenção"
            description="Pendências críticas e alertas que exigem ação imediata."
          >
            <div className="grid gap-4 md:grid-cols-2">
              {operationalData && operationalData.atrasadas > 0 && (
                <div className="rounded-sm border border-rose-200 bg-rose-50/50 p-4 shadow-sm dark:bg-rose-950/20 dark:border-rose-900/50 flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold text-sm">
                    <AlertTriangle className="size-4" />
                    <span>Tarefas Vencidas</span>
                  </div>
                  <p className="text-2xl font-bold text-rose-700 dark:text-rose-400">{formatCount(operationalData.atrasadas)}</p>
                  <Button asChild size="sm" variant="outline" className="mt-2 w-fit bg-transparent border-rose-200 hover:bg-rose-100 text-rose-700 dark:border-rose-800 dark:hover:bg-rose-900/50 dark:text-rose-300">
                    <Link href="/dashboard/operacional/campo/tarefas">Ver tarefas atrasadas</Link>
                  </Button>
                </div>
              )}
              
              {financeData && financeData.vencendo_7d.length > 0 && (
                <div className="rounded-sm border border-amber-200 bg-amber-50/50 p-4 shadow-sm dark:bg-amber-950/20 dark:border-amber-900/50 flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold text-sm">
                    <Wallet className="size-4" />
                    <span>Financeiro a Vencer (7 dias)</span>
                  </div>
                  <p className="text-2xl font-bold text-amber-700 dark:text-amber-400">{financeData.vencendo_7d.length}</p>
                  <Button asChild size="sm" variant="outline" className="mt-2 w-fit bg-transparent border-amber-200 hover:bg-amber-100 text-amber-700 dark:border-amber-800 dark:hover:bg-amber-900/50 dark:text-amber-300">
                    <Link href="/dashboard/financeiro/contas-pagar">Ver contas a pagar</Link>
                  </Button>
                </div>
              )}
            </div>
            <DashboardAlertsCard
              summary={alertSummaryQuery.data}
              isLoading={alertSummaryQuery.isLoading}
              isError={alertSummaryQuery.isError}
              onRetry={() => alertSummaryQuery.refetch()}
            />
          </SectionShell>

          <SectionShell
            title="Próximas atividades"
            description="Tarefas planejadas para hoje ou em andamento."
          >
            <div className="grid gap-4 md:grid-cols-2">
              <MetricCard
                label="Tarefas de hoje"
                value={operationalData ? formatCount(operationalData.pendentes) : "0"}
                description="Tarefas programadas"
                icon={<CalendarDays className="size-5 text-slate-600" />}
                tone="bg-slate-500/10"
              />
              <MetricCard
                label="Operações em andamento"
                value={operationalData ? formatCount(operationalData.em_execucao) : "0"}
                description="Equipe em campo"
                icon={<Activity className="size-5 text-emerald-600" />}
                tone="bg-emerald-500/10"
              />
            </div>
          </SectionShell>
        </div>

        {/* AÇÕES RÁPIDAS */}
        <div className="flex flex-col gap-6">
          <SectionShell
            title="Ações rápidas"
            description="Atalhos para as operações mais frequentes."
          >
            <div className="flex flex-col gap-3">
              {profile.hasAgriculture && (
                <Button asChild variant="outline" className="justify-start gap-3 h-12 rounded-sm shadow-sm">
                  <Link href="/agricola/safras">
                    <div className="size-7 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                      <Sprout className="size-4 text-primary" />
                    </div>
                    <div className="flex flex-col items-start text-left">
                      <span className="font-semibold text-sm">Abrir Safras</span>
                      <span className="text-[10px] text-muted-foreground font-normal">Acessar painéis de safra</span>
                    </div>
                  </Link>
                </Button>
              )}
              <Button asChild variant="outline" className="justify-start gap-3 h-12 rounded-sm shadow-sm">
                <Link href="/dashboard/operacional/campo/tarefas">
                  <div className="size-7 rounded-sm bg-amber-500/10 flex items-center justify-center shrink-0">
                    <Loader2 className="size-4 text-amber-600" />
                  </div>
                  <div className="flex flex-col items-start text-left">
                    <span className="font-semibold text-sm">Ver Tarefas</span>
                    <span className="text-[10px] text-muted-foreground font-normal">Painel operacional geral</span>
                  </div>
                </Link>
              </Button>
              <Button asChild variant="outline" className="justify-start gap-3 h-12 rounded-sm shadow-sm">
                <Link href="/suprimentos/estoque">
                  <div className="size-7 rounded-sm bg-blue-500/10 flex items-center justify-center shrink-0">
                    <Package className="size-4 text-blue-600" />
                  </div>
                  <div className="flex flex-col items-start text-left">
                    <span className="font-semibold text-sm">Consultar Estoque</span>
                    <span className="text-[10px] text-muted-foreground font-normal">Inventário e insumos</span>
                  </div>
                </Link>
              </Button>
              {profile.hasFinance && (
                <Button asChild variant="outline" className="justify-start gap-3 h-12 rounded-sm shadow-sm">
                  <Link href="/dashboard/financeiro">
                    <div className="size-7 rounded-sm bg-emerald-500/10 flex items-center justify-center shrink-0">
                      <Wallet className="size-4 text-emerald-600" />
                    </div>
                    <div className="flex flex-col items-start text-left">
                      <span className="font-semibold text-sm">Financeiro Consolidado</span>
                      <span className="text-[10px] text-muted-foreground font-normal">DRE e fluxo de caixa</span>
                    </div>
                  </Link>
                </Button>
              )}
              {profile.hasLivestock && (
                <Button asChild variant="outline" className="justify-start gap-3 h-12 rounded-sm shadow-sm">
                  <Link href="/dashboard/pecuaria">
                    <div className="size-7 rounded-sm bg-indigo-500/10 flex items-center justify-center shrink-0">
                      <Beef className="size-4 text-indigo-600" />
                    </div>
                    <div className="flex flex-col items-start text-left">
                      <span className="font-semibold text-sm">Rebanho</span>
                      <span className="text-[10px] text-muted-foreground font-normal">Lotes e manejo</span>
                    </div>
                  </Link>
                </Button>
              )}
            </div>
          </SectionShell>

          <DashboardCopilotCard
            subtitle={copilotSubtitle}
            highlights={copilotHighlights}
            ctaLabel="Ver análises da IA"
            ctaHref="/dashboard/ia/resumo"
            isLoading={copilotIsLoading}
          />
        </div>
      </div>

      {/* INDICADORES RESUMIDOS */}
      <div className="mt-8 border-t pt-8 space-y-6">
        <h3 className="text-lg font-semibold tracking-tight">Indicadores Resumidos</h3>
        
        {profile.hasFinance && (
          <SectionShell
            title="Financeiro"
            description="Receitas, despesas, resultado e fluxo de caixa."
          >
            {financeiroQuery.isLoading ? (
              <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
            ) : financeData && hasFinancialData(financeData) ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Receitas"
                  value={formatCurrency(financeData.total_recebido_mes)}
                  description={\`\${formatCount(financeData.total_a_receber)} em aberto\`}
                  icon={<TrendingUp className="size-5 text-emerald-600" />}
                  tone="bg-emerald-500/10"
                />
                <MetricCard
                  label="Despesas"
                  value={formatCurrency(financeData.total_pago_mes)}
                  description={\`\${formatCount(financeData.total_a_pagar)} em aberto\`}
                  icon={<Wallet className="size-5 text-rose-600" />}
                  tone="bg-rose-500/10"
                />
                <MetricCard
                  label="Resultado"
                  value={formatCurrency(financeValue)}
                  description={financeValue >= 0 ? "Saldo operacional positivo" : "Saldo operacional negativo"}
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
                <MetricCard
                  label="Saldo / Fluxo de caixa"
                  value={formatCurrency(financeData.saldo_mes)}
                  description={\`Atraso: \${formatCurrency(financeData.total_atrasado_despesas)}\`}
                  icon={<Waves className="size-5 text-primary" />}
                  tone="bg-primary/10"
                />
              </div>
            ) : null}
          </SectionShell>
        )}

        {profile.hasAgriculture && (
          <SectionShell
            title="Agricultura"
            description="Resumo executivo da operação agrícola consolidada."
          >
            {agricolaQuery.isLoading ? (
              <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
            ) : agricolaData && hasAgricolaData(agricolaData) ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Safras ativas"
                  value={formatCount(agricolaData.kpis.total_safras_ativas)}
                  description={\`\${formatCount(agricolaData.kpis.total_safras_encerradas)} encerradas\`}
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
                  label="Alertas"
                  value={formatCount(agricolaData.kpis.total_alertas)}
                  description="Pendências e desvios oficiais"
                  icon={<BarChart3 className="size-5 text-sky-600" />}
                  tone="bg-sky-500/10"
                />
              </div>
            ) : null}
          </SectionShell>
        )}

        {profile.hasLivestock && (
          <SectionShell
            title="Pecuária"
            description="Resumo executivo do rebanho, sanidade e custo sanitário."
          >
            {pecuariaQuery.isLoading ? (
              <SectionSkeleton cards={6} columnsClassName="md:grid-cols-2 xl:grid-cols-3" />
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
            ) : null}
          </SectionShell>
        )}
      </div>
    </div>
  );`;

if (content.indexOf(oldReturnStr) === -1) {
    console.log("Could not find old return string exactly.");
} else {
    content = content.replace(oldReturnStr, newReturnStr);
    fs.writeFileSync(file, content);
    console.log("Replaced successfully.");
}
