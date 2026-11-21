"use client";

import { useMemo } from "react";
import Link from "next/link";

import { useQuery } from "@tanstack/react-query";
import { format, isValid, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Activity,
  Baby,
  Beef,
  ChevronRight,
  DollarSign,
  Layers,
  LayoutDashboard,
  List,
  MapPin,
  Plus,
  Scale,
  Shuffle,
  Skull,
  Syringe,
  TrendingUp,
  Upload,
  Weight,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";

import { apiFetch } from "@/lib/api";
import {
  fetchLotes,
  fetchPecuariaResumoExecutivo,
  fetchPiquetesAtivos,
  type LoteBovino,
  type PiqueteOption,
} from "@/lib/pecuaria/lotes-api";
import { useAppStore } from "@/lib/stores/app-store";
import { formatCurrency } from "@/lib/utils";

interface ManejoLote {
  id: string;
  lote_id: string;
  tipo_evento: string;
  data_evento: string;
  quantidade_cabecas?: number;
  peso_total_kg?: number;
  observacoes?: string;
}

const CATEGORIA_COLORS: Record<string, string> = {
  Bezerros: "#3b82f6",
  "Vacas Paridas": "#ec4899",
  Novilhas: "#8b5cf6",
  "Bois em Engorda": "#f59e0b",
  Reprodutores: "#ef4444",
  Touros: "#dc2626",
  Recria: "#10b981",
};
const DEFAULT_COLOR = "#6b7280";

const EVENTO_CONFIG: Record<
  string,
  { label: string; color: string; icon: React.ComponentType<{ className?: string }> }
> = {
  NASCIMENTO: { label: "Nascimento", color: "text-green-600", icon: Baby },
  COMPRA: { label: "Compra", color: "text-emerald-600", icon: Beef },
  MORTE: { label: "Morte", color: "text-red-600", icon: Skull },
  PESAGEM: { label: "Pesagem", color: "text-blue-600", icon: Weight },
  VACINACAO: { label: "Vacinação", color: "text-purple-600", icon: Syringe },
  TRANSFERENCIA: { label: "Transferência", color: "text-orange-600", icon: Shuffle },
};

function fmtDate(value?: string) {
  if (!value) return "—";
  try {
    const parsed = parseISO(value);
    return isValid(parsed) ? format(parsed, "dd/MM/yy", { locale: ptBR }) : "—";
  } catch {
    return "—";
  }
}

function getCategoriaColor(cat: string) {
  return CATEGORIA_COLORS[cat] ?? DEFAULT_COLOR;
}

export default function PecuariaDashboard() {
  const { activeFazendaId, isVisaoGrupo } = useAppStore();
  const contextoAtivo = isVisaoGrupo || Boolean(activeFazendaId);
  const fazendaFiltro = isVisaoGrupo ? null : activeFazendaId;

  const { data: lotes = [] } = useQuery<LoteBovino[]>({
    queryKey: ["lotes-bovinos", activeFazendaId, isVisaoGrupo],
    queryFn: () => fetchLotes(fazendaFiltro),
    enabled: contextoAtivo,
  });

  const { data: manejos = [] } = useQuery<ManejoLote[]>({
    queryKey: ["pecuaria-manejos"],
    queryFn: () => apiFetch<ManejoLote[]>("/pecuaria/manejos/"),
    enabled: contextoAtivo,
  });

  const { data: piquetes = [] } = useQuery<PiqueteOption[]>({
    queryKey: ["piquetes", activeFazendaId],
    queryFn: () => fetchPiquetesAtivos(activeFazendaId as string),
    enabled: Boolean(activeFazendaId) && !isVisaoGrupo,
  });

  const { data: resumo } = useQuery({
    queryKey: ["pecuaria-resumo-economico", activeFazendaId, isVisaoGrupo],
    queryFn: () => fetchPecuariaResumoExecutivo(fazendaFiltro),
    enabled: contextoAtivo,
  });

  const quickActions = [
    { href: "/dashboard/pecuaria/lotes", icon: Beef, label: "Lotes & Rebanho", desc: "Controle e pesagens" },
    { href: "/dashboard/pecuaria/manejo", icon: Syringe, label: "Manejo & Sanidade", desc: "Vacinas e tratamentos" },
    { href: "/dashboard/pecuaria/piquetes", icon: MapPin, label: "Piquetes & Pastos", desc: "Lotação e suporte" },
    { href: "/dashboard/pecuaria/genetica", icon: Activity, label: "Genética & Matrizes", desc: "Reprodução e IATF" },
    { href: "/dashboard/pecuaria/confinamento", icon: Layers, label: "Confinamento", desc: "Dietas e engorda" },
    { href: "/dashboard/pecuaria/leite", icon: TrendingUp, label: "Produção Leiteira", desc: "Ordenhas e tanques" },
    { href: "/dashboard/pecuaria/relatorios", icon: Scale, label: "Relatórios Zootécnicos", desc: "GMD e curva de peso" },
    { href: "/dashboard/pecuaria/importar", icon: Upload, label: "Importar Planilhas", desc: "Carga via Excel/CSV" },
  ];

  const categoriaData = useMemo(() => {
    const map = new Map<string, number>();
    for (const lote of lotes.filter((item) => item.ativo)) {
      const key = lote.categoria || "Sem categoria";
      map.set(key, (map.get(key) ?? 0) + lote.quantidade_cabecas);
    }
    return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
  }, [lotes]);

  const racaData = useMemo(() => {
    const map = new Map<string, number>();
    for (const lote of lotes.filter((item) => item.ativo)) {
      const key = lote.raca || "Sem raça";
      map.set(key, (map.get(key) ?? 0) + lote.quantidade_cabecas);
    }
    return Array.from(map.entries())
      .map(([raca, cabecas]) => ({ raca, cabecas }))
      .sort((a, b) => b.cabecas - a.cabecas)
      .slice(0, 6);
  }, [lotes]);

  const activePiquetes = useMemo(
    () =>
      piquetes.map((piq) => {
        const lotesPiquete = lotes.filter((lote) => lote.ativo && lote.piquete_id === piq.id);
        const cabecas = lotesPiquete.reduce((soma, lote) => soma + lote.quantidade_cabecas, 0);
        const pesoVivo = lotesPiquete.reduce(
          (soma, lote) => soma + lote.quantidade_cabecas * lote.peso_medio_kg,
          0
        );
        const ua = pesoVivo > 0 ? pesoVivo / 450 : cabecas * 0.5;
        const capacidade = piq.dados_extras?.capacidade_suporte_ua ?? null;
        const lotPct = capacidade ? Math.min(100, (ua / capacidade) * 100) : null;
        return { ...piq, cabecas, lotPct };
      }),
    [piquetes, lotes]
  );

  const recentManejos = useMemo(
    () =>
      [...manejos]
        .sort((a, b) => new Date(b.data_evento).getTime() - new Date(a.data_evento).getTime())
        .slice(0, 8),
    [manejos]
  );

  const investimentoTotal =
    (resumo?.custo_aquisicao_acumulado ?? 0) + (resumo?.custo_operacional_acumulado ?? 0);
  const margemPositiva = (resumo?.margem_bruta_estimada ?? 0) >= 0;

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Painel de Rebanhos"
        description="Painel zootécnico e econômico — rebanho híbrido, lotação, custo da arroba e valor de mercado"
        icon={<LayoutDashboard className="size-6 text-primary" />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Pecuária" }]}
        actions={
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm" className="h-8 text-xs rounded-sm">
              <Link href="/dashboard/pecuaria/lotes">
                <List className="size-3.5 mr-1.5" />
                Ver Lotes
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm" className="h-8 text-xs rounded-sm">
              <Link href="/dashboard/pecuaria/manejo">
                <Plus className="size-3.5 mr-1.5" />
                Registrar Manejo
              </Link>
            </Button>
          </div>
        }
      />

      <QuickActionGrid
        label="Ações & Comandos do Rebanho"
        columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-8"
        actions={quickActions.map((act) => ({
          title: act.label,
          description: act.desc,
          icon: act.icon,
          href: act.href,
        }))}
      />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          {
            label: "Total de Cabeças",
            value: (resumo?.animais_ativos ?? 0).toLocaleString("pt-BR"),
            sub: `${resumo?.lotes_ativos ?? 0} lotes ativos`,
            icon: Beef,
            color: "text-amber-600 dark:text-amber-400",
            bg: "bg-amber-500/10",
          },
          {
            label: "Lotes Ativos",
            value: resumo?.lotes_ativos ?? 0,
            sub: "Modo híbrido consolidado",
            icon: Layers,
            color: "text-blue-600 dark:text-blue-400",
            bg: "bg-blue-500/10",
          },
          {
            label: "Piquetes Ativos",
            value: resumo?.piquetes_ativos ?? 0,
            sub: `${(resumo?.area_pastagem_ha ?? 0).toFixed(1)} ha de pastagem`,
            icon: MapPin,
            color: "text-emerald-600 dark:text-emerald-400",
            bg: "bg-emerald-500/10",
          },
          {
            label: "Peso Médio (kg)",
            value: (resumo?.peso_medio_kg ?? 0).toFixed(1),
            sub: `Total: ${(resumo?.peso_total_kg ?? 0).toLocaleString("pt-BR")} kg`,
            icon: Scale,
            color: "text-purple-600 dark:text-purple-400",
            bg: "bg-purple-500/10",
          },
          {
            label: "UA Real (450 kg)",
            value: (resumo?.ua_total ?? 0).toFixed(2),
            sub: `Lotação: ${(resumo?.lotacao_ua_ha ?? 0).toFixed(2)} UA/ha`,
            icon: Activity,
            color: "text-orange-600 dark:text-orange-400",
            bg: "bg-orange-500/10",
          },
        ].map(({ label, value, sub, icon: Icon, color, bg }) => (
          <Card key={label} className="shadow-xs border border-border/70 rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-2xl font-bold leading-none tabular-nums">{value}</div>
                  <div className="text-xs text-muted-foreground mt-1.5 leading-tight font-medium">{label}</div>
                  <div className="text-[11px] text-muted-foreground/80 mt-1">{sub}</div>
                </div>
                <div className={`p-2 rounded-sm ${bg} ${color}`}>
                  <Icon className="size-4.5" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          {
            label: "Estoque em Arrobas (@)",
            value: `${(resumo?.arrobas_totais ?? 0).toLocaleString("pt-BR")} @`,
            sub: `${(resumo?.arrobas_por_hectare ?? 0).toFixed(2)} @/ha`,
          },
          {
            label: "Custo Operacional / @",
            value: formatCurrency(resumo?.custo_total_por_arroba ?? 0),
            sub: `Operacional: ${formatCurrency(resumo?.custo_operacional_acumulado ?? 0)}`,
          },
          {
            label: "Break-even (R$/@)",
            value: formatCurrency(resumo?.custo_break_even_por_arroba ?? 0),
            sub: `Aquisição + operacional`,
          },
          {
            label: "Manejos / Vacinas Pendentes",
            value: `${resumo?.manejos_pendentes ?? 0} / ${resumo?.vacinacoes_pendentes ?? 0}`,
            sub: "Tarefas abertas de campo",
          },
        ].map((item) => (
          <Card key={item.label} className="shadow-xs border border-border/70 rounded-sm">
            <CardContent className="p-4">
              <div className="text-xs text-muted-foreground font-medium">{item.label}</div>
              <div className="text-xl font-bold mt-1 tabular-nums">{item.value}</div>
              <div className="text-[11px] text-muted-foreground/80 mt-1">{item.sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="shadow-xs border border-border/70 rounded-sm">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-muted-foreground">Valor Estimado do Rebanho</span>
              {resumo?.fonte_cotacao ? (
                <Badge variant="outline" className="rounded-sm text-[10px]">
                  {resumo.fonte_cotacao}
                </Badge>
              ) : null}
            </div>
            <div className="text-2xl font-bold tabular-nums">
              {resumo?.valor_mercado_estimado != null
                ? formatCurrency(resumo.valor_mercado_estimado)
                : "Cotação indisponível"}
            </div>
            <p className="text-xs text-muted-foreground">
              {resumo?.cotacao_arroba_referencia != null
                ? `Referência: ${formatCurrency(resumo.cotacao_arroba_referencia)}/@`
                : "Configure cotação manual no lote se necessário."}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-xs border border-border/70 rounded-sm">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <DollarSign className="size-3.5" />
              Investimento Total no Rebanho
            </div>
            <div className="text-2xl font-bold tabular-nums">{formatCurrency(investimentoTotal)}</div>
            <p className="text-xs text-muted-foreground">
              Aquisição: {formatCurrency(resumo?.custo_aquisicao_acumulado ?? 0)} · Operacional:{" "}
              {formatCurrency(resumo?.custo_operacional_acumulado ?? 0)}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-xs border border-border/70 rounded-sm">
          <CardContent className="p-4 space-y-1">
            <div className="text-xs font-medium text-muted-foreground">Margem Bruta Estimada</div>
            <div
              className={`text-2xl font-bold tabular-nums ${
                margemPositiva ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"
              }`}
            >
              {resumo?.margem_bruta_estimada != null
                ? formatCurrency(resumo.margem_bruta_estimada)
                : "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              Sanidade: {formatCurrency(resumo?.custo_sanitario_acumulado ?? 0)} · Nutrição:{" "}
              {formatCurrency(resumo?.custo_nutricao_acumulado ?? 0)} · Outros:{" "}
              {formatCurrency(resumo?.custo_outros_acumulado ?? 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="rounded-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Composição do Rebanho</CardTitle>
          </CardHeader>
          <CardContent>
            {categoriaData.length === 0 ? (
              <div className="h-44 flex items-center justify-center text-muted-foreground text-sm">
                Nenhum lote ativo
              </div>
            ) : (
              <div className="flex gap-4 items-center">
                <ResponsiveContainer width="45%" height={170}>
                  <PieChart>
                    <Pie data={categoriaData} dataKey="value" cx="50%" cy="50%" innerRadius={36} outerRadius={68}>
                      {categoriaData.map((entry, idx) => (
                        <Cell key={idx} fill={getCategoriaColor(entry.name)} />
                      ))}
                    </Pie>
                    <ReTooltip formatter={(v: unknown, n: unknown) => [`${v} cab.`, `${n}`]} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-1.5">
                  {categoriaData.map((entry, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: getCategoriaColor(entry.name) }}
                        />
                        <span className="text-xs truncate max-w-[100px]">{entry.name}</span>
                      </div>
                      <span className="text-xs font-medium">{entry.value.toLocaleString("pt-BR")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Cabeças por Raça</CardTitle>
          </CardHeader>
          <CardContent>
            {racaData.length === 0 ? (
              <div className="h-44 flex items-center justify-center text-muted-foreground text-sm">
                Nenhum lote ativo
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={racaData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="raca" type="category" width={75} tick={{ fontSize: 11 }} />
                  <ReTooltip formatter={(v: unknown) => [`${v} cab.`, "Cabeças"]} />
                  <Bar dataKey="cabecas" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="rounded-sm">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base">Piquetes — Lotação</CardTitle>
            <Link
              href="/dashboard/pecuaria/piquetes"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors"
            >
              Ver todos <ChevronRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {activePiquetes.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                <MapPin className="h-8 w-8 mx-auto mb-2 opacity-40" />
                Nenhum piquete cadastrado
              </div>
            ) : (
              <div className="space-y-3">
                {activePiquetes.slice(0, 6).map((piq) => {
                  const pct = piq.lotPct ?? 0;
                  const barColor = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-green-500";
                  return (
                    <div key={piq.id}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-sm truncate">{piq.nome}</span>
                        <span className="text-xs text-muted-foreground shrink-0 ml-2">
                          {piq.cabecas} cab. · {piq.area_hectares ?? piq.area_hectares_manual ?? 0} ha
                        </span>
                      </div>
                      {piq.lotPct !== null ? (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-muted rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-muted-foreground w-8 text-right">
                            {pct.toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <div className="text-xs text-muted-foreground">Capacidade não definida</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base">Últimos Manejos</CardTitle>
            <Link
              href="/dashboard/pecuaria/manejo"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors"
            >
              Ver todos <ChevronRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {recentManejos.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                <Syringe className="h-8 w-8 mx-auto mb-2 opacity-40" />
                Nenhum manejo registrado
              </div>
            ) : (
              <div className="space-y-2.5">
                {recentManejos.map((manejo) => {
                  const cfg = EVENTO_CONFIG[manejo.tipo_evento] ?? {
                    label: manejo.tipo_evento,
                    color: "text-muted-foreground",
                    icon: Activity,
                  };
                  const Icon = cfg.icon;
                  const lote = lotes.find((item) => item.id === manejo.lote_id);
                  return (
                    <div key={manejo.id} className="flex items-start gap-3">
                      <div className={`mt-0.5 shrink-0 ${cfg.color}`}>
                        <Icon className="size-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-sm font-medium">{cfg.label}</span>
                          <span className="text-xs text-muted-foreground shrink-0">
                            {fmtDate(manejo.data_evento)}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {lote?.identificacao ?? "Lote desconhecido"}
                          {manejo.quantidade_cabecas ? ` — ${manejo.quantidade_cabecas} cab.` : ""}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
