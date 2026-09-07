"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CalendarClock, CheckCircle2, ShieldAlert, Tractor, Wrench } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

type StatusPreventivo = "EM_DIA" | "PROXIMO_VENCIMENTO" | "VENCIDO";

interface FrotaPreventivaResumo {
  planos_em_dia: number;
  planos_proximos_vencimento: number;
  planos_vencidos: number;
  os_preventivas_abertas: number;
}

interface FrotaPreventivaRegra {
  tipo: "DIAS" | "HORAS" | "KM";
  limite: number;
  leitura_atual: string | number | null;
  ultimo_registro: string | number | null;
  proxima_execucao: string | number | null;
  restante: number | null;
  vencido_por: number | null;
  status: StatusPreventivo;
}

interface FrotaPreventivaItem {
  plano_id: string;
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  unidade_produtiva_id: string | null;
  plano_descricao: string;
  tipo_regra: string;
  limite_resumo: string;
  leitura_atual_resumo: string;
  proxima_execucao_resumo: string;
  status: StatusPreventivo;
  regras: FrotaPreventivaRegra[];
  os_preventiva_aberta_id: string | null;
  os_preventiva_aberta_numero: string | null;
}

interface FrotaPreventivaResponse {
  resumo: FrotaPreventivaResumo;
  itens: FrotaPreventivaItem[];
  gerado_em: string;
}

interface GerarOsPreventivaResponse {
  criada: boolean;
  ordem_servico_id: string;
  numero_os: string;
  status: string;
  tipo: string;
  equipamento_id: string;
  plano_id: string;
  data_abertura: string;
  descricao_problema: string;
}

export default function FrotaManutencaoPreventivaPage() {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<FrotaPreventivaResponse>({
    queryKey: ["frota", "manutencao-preventiva", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/manutencao-preventiva", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const gerarOsMutation = useMutation({
    mutationFn: (planoId: string) =>
      apiFetch(`/frota/manutencao-preventiva/${planoId}/gerar-os`, {
        method: "POST",
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    onSuccess: (response: GerarOsPreventivaResponse) => {
      queryClient.invalidateQueries({ queryKey: ["frota", "manutencao-preventiva"] });
      queryClient.invalidateQueries({ queryKey: ["frota", "dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["oficina"] });
      toast.success(
        response.criada
          ? `OS preventiva ${response.numero_os} gerada.`
          : `OS preventiva ${response.numero_os} já estava aberta.`
      );
    },
    onError: (mutationError: Error) => {
      toast.error(mutationError.message || "Erro ao gerar OS preventiva.");
    },
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Manutenção Preventiva"
        description="Controle operacional de vencimentos por dias, horas e km com geração assistida de OS preventiva."
        icon={<CalendarClock className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/dashboard/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Preventiva" },
        ]}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota">
                <Tractor className="size-3.5" />
                Dashboard Frota
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/manutencoes">
                <Wrench className="size-3.5" />
                Ordens de Serviço
              </Link>
            </Button>
          </>
        }
      />

      {!hasProfessionalTier ? (
        <TierUpgradeCard
          title="Manutenção preventiva disponível no Profissional"
          description="Planos preventivos, vencimentos automáticos e geração assistida de OS fazem parte da gestão operacional completa."
          requiredTier="PROFISSIONAL"
          feature="frota_manutencao_preventiva"
          surface="frota_manutencao_preventiva_page"
        />
      ) : null}

      {isLoading ? <PreventivaSkeleton /> : null}

      {hasProfessionalTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar a manutenção preventiva"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasProfessionalTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ResumoCard
              title="Planos em dia"
              value={data.resumo.planos_em_dia}
              description="Sem ação imediata"
              icon={CheckCircle2}
              tone="default"
            />
            <ResumoCard
              title="Próximos do vencimento"
              value={data.resumo.planos_proximos_vencimento}
              description="Preparar agenda preventiva"
              icon={CalendarClock}
              tone={data.resumo.planos_proximos_vencimento > 0 ? "warning" : "default"}
            />
            <ResumoCard
              title="Vencidos"
              value={data.resumo.planos_vencidos}
              description="Prioridade operacional"
              icon={AlertTriangle}
              tone={data.resumo.planos_vencidos > 0 ? "danger" : "default"}
            />
            <ResumoCard
              title="OS preventivas abertas"
              value={data.resumo.os_preventivas_abertas}
              description="Em andamento ou aguardando execução"
              icon={Wrench}
              tone={data.resumo.os_preventivas_abertas > 0 ? "warning" : "default"}
            />
          </div>

          {data.itens.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<CalendarClock />}
                  title="Nenhum plano preventivo encontrado"
                  description="Cadastre planos de manutenção para acompanhar vencimentos preventivos."
                />
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-sm shadow-sm">
              <CardHeader>
                <CardTitle>Planos preventivos por equipamento</CardTitle>
                <CardDescription>Resumo operacional com regra ativa, leitura atual, vencimento e ação de abertura de OS.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Equipamento</TableHead>
                      <TableHead>Plano</TableHead>
                      <TableHead>Tipo de regra</TableHead>
                      <TableHead>Limite</TableHead>
                      <TableHead>Leitura atual</TableHead>
                      <TableHead>Próxima execução</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.itens.map((item) => (
                      <TableRow key={item.plano_id}>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="font-medium">{item.equipamento_nome}</div>
                            <div className="text-xs text-muted-foreground">
                              {item.equipamento_tipo} • {item.equipamento_status}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="font-medium">{item.plano_descricao}</div>
                            {item.os_preventiva_aberta_numero ? (
                              <Badge variant="outline" className="border-blue-200 text-blue-700">
                                OS aberta {item.os_preventiva_aberta_numero}
                              </Badge>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell className="align-top">{formatTipoRegra(item.tipo_regra)}</TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">{item.limite_resumo}</TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">{item.leitura_atual_resumo}</TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">{item.proxima_execucao_resumo}</TableCell>
                        <TableCell className="align-top">
                          <div className="space-y-2">
                            <Badge variant="outline" className={getStatusClass(item.status)}>
                              {STATUS_LABELS[item.status]}
                            </Badge>
                            <div className="space-y-1">
                              {item.regras.map((regra) => (
                                <div key={`${item.plano_id}-${regra.tipo}`} className="text-[11px] text-muted-foreground">
                                  {formatRuleHint(regra)}
                                </div>
                              ))}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="align-top text-right">
                          <div className="flex justify-end gap-2">
                            <Button asChild variant="ghost" size="sm">
                              <Link href={`/dashboard/operacional/frota/${item.equipamento_id}`}>
                                <ArrowRight className="size-3.5" />
                                Equipamento
                              </Link>
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={gerarOsMutation.isPending}
                              onClick={() => gerarOsMutation.mutate(item.plano_id)}
                            >
                              <Wrench className="size-3.5" />
                              {item.os_preventiva_aberta_id ? "Reusar OS" : "Gerar OS"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}

const STATUS_LABELS: Record<StatusPreventivo, string> = {
  EM_DIA: "Em dia",
  PROXIMO_VENCIMENTO: "Próximo do vencimento",
  VENCIDO: "Vencido",
};

function ResumoCard({
  title,
  value,
  description,
  icon: Icon,
  tone,
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof CalendarClock;
  tone: "default" | "warning" | "danger";
}) {
  return (
    <Card
      className={cn(
        "rounded-sm shadow-sm",
        tone === "warning" && "border-amber-200",
        tone === "danger" && "border-red-200"
      )}
    >
      <CardContent className="flex items-start gap-4 p-5">
        <div
          className={cn(
            "flex size-10 items-center justify-center rounded-sm",
            tone === "default" && "bg-primary/10 text-primary",
            tone === "warning" && "bg-amber-100 text-amber-700",
            tone === "danger" && "bg-red-100 text-red-700"
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
          <div className="mt-0.5 text-2xl font-black tracking-tight">{value}</div>
          <div className="mt-1 text-xs text-muted-foreground">{description}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function PreventivaSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <Skeleton className="h-[520px] rounded-sm" />
    </div>
  );
}

function formatTipoRegra(tipo: string) {
  return tipo.split("_").join(" + ");
}

function getStatusClass(status: StatusPreventivo) {
  switch (status) {
    case "VENCIDO":
      return "border-red-200 text-red-700";
    case "PROXIMO_VENCIMENTO":
      return "border-amber-200 text-amber-700";
    default:
      return "border-emerald-200 text-emerald-700";
  }
}

function formatRuleHint(regra: FrotaPreventivaRegra) {
  if (regra.status === "VENCIDO") {
    const valor = regra.vencido_por ?? 0;
    return `Regra ${regra.tipo}: vencido por ${formatDelta(regra.tipo, valor)}.`;
  }
  if (regra.status === "PROXIMO_VENCIMENTO") {
    const valor = regra.restante ?? 0;
    return `Regra ${regra.tipo}: faltam ${formatDelta(regra.tipo, valor)}.`;
  }
  return `Regra ${regra.tipo}: dentro do limite.`;
}

function formatDelta(tipo: FrotaPreventivaRegra["tipo"], valor: number) {
  const numero = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(valor);

  if (tipo === "DIAS") return `${numero} dia(s)`;
  if (tipo === "HORAS") return `${numero} h`;
  return `${numero} km`;
}
