"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardList, Lock, ShieldAlert, Tractor, Unlock, Wrench } from "lucide-react";
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

import { DisponibilidadeResponse, StatusOperacional, BloqueioResponse } from "./types";

interface DisponibilidadeClientProps {
  initialData: DisponibilidadeResponse | null;
  serverFazendaId: string;
}

const STATUS_LABELS: Record<StatusOperacional, string> = {
  DISPONIVEL: "Disponível",
  EM_USO: "Em uso",
  EM_MANUTENCAO: "Em manutenção",
  BLOQUEADO: "Bloqueado",
  CHECKLIST_PENDENTE: "Checklist pendente",
  NAO_CONFORME: "Não conforme",
  DOCUMENTO_VENCIDO: "Documento vencido",
};

export function DisponibilidadeClient({ initialData, serverFazendaId }: DisponibilidadeClientProps) {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const queryClient = useQueryClient();

  const isServerDataMatching = (!activeFazendaId && !serverFazendaId) || (activeFazendaId === serverFazendaId);

  const { data, isLoading, isError, error } = useQuery<DisponibilidadeResponse>({
    queryKey: ["frota", "disponibilidade", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/disponibilidade", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  const bloquearMutation = useMutation({
    mutationFn: (equipamentoId: string) =>
      apiFetch(`/frota/disponibilidade/equipamentos/${equipamentoId}/bloquear`, {
        method: "POST",
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
        body: JSON.stringify({ motivo: "Bloqueio operacional manual." }),
      }),
    onSuccess: (response: BloqueioResponse) => {
      queryClient.invalidateQueries({ queryKey: ["frota", "disponibilidade"] });
      queryClient.invalidateQueries({ queryKey: ["frota", "dashboard"] });
      toast.success(response.mensagem);
    },
    onError: (mutationError: Error) => toast.error(mutationError.message || "Erro ao bloquear equipamento."),
  });

  const liberarMutation = useMutation({
    mutationFn: (equipamentoId: string) =>
      apiFetch(`/frota/disponibilidade/equipamentos/${equipamentoId}/liberar`, {
        method: "POST",
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    onSuccess: (response: BloqueioResponse) => {
      queryClient.invalidateQueries({ queryKey: ["frota", "disponibilidade"] });
      queryClient.invalidateQueries({ queryKey: ["frota", "dashboard"] });
      toast.success(response.mensagem);
    },
    onError: (mutationError: Error) => toast.error(mutationError.message || "Erro ao liberar equipamento."),
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Disponibilidade Operacional"
        description="Status de liberação dos equipamentos com integração de checklist, documentos, manutenção e OS abertas."
        icon={<ShieldAlert className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/dashboard/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Disponibilidade" },
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
                Manutenções
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota/jornadas">
                <ClipboardList className="size-3.5" />
                Jornadas
              </Link>
            </Button>
          </>
        }
      />

      {!hasProfessionalTier ? (
        <TierUpgradeCard
          title="Disponibilidade operacional disponível no Profissional"
          description="Bloqueio manual, checklist e status operacional consolidado fazem parte da camada profissional da Frota."
          requiredTier="PROFISSIONAL"
          feature="frota_disponibilidade"
          surface="frota_disponibilidade_page"
        />
      ) : null}

      {isLoading ? <DisponibilidadeSkeleton /> : null}

      {hasProfessionalTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar a disponibilidade da frota"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasProfessionalTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <ResumoCard title="Disponíveis" value={data.resumo.disponiveis} icon={CheckCircle2} />
            <ResumoCard title="Em uso" value={data.resumo.em_uso} icon={ClipboardList} tone={data.resumo.em_uso > 0 ? "warning" : "default"} />
            <ResumoCard title="Em manutenção" value={data.resumo.em_manutencao} icon={Wrench} tone={data.resumo.em_manutencao > 0 ? "warning" : "default"} />
            <ResumoCard title="Bloqueados" value={data.resumo.bloqueados} icon={Lock} tone={data.resumo.bloqueados > 0 ? "danger" : "default"} />
            <ResumoCard title="Checklist pendente" value={data.resumo.checklist_pendente} icon={ClipboardList} tone={data.resumo.checklist_pendente > 0 ? "warning" : "default"} />
            <ResumoCard title="Não conformes" value={data.resumo.nao_conformes} icon={AlertTriangle} tone={data.resumo.nao_conformes > 0 ? "danger" : "default"} />
            <ResumoCard title="Docs vencidos" value={data.resumo.documentos_vencidos} icon={ShieldAlert} tone={data.resumo.documentos_vencidos > 0 ? "danger" : "default"} />
          </div>

          {data.equipamentos.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<Tractor />}
                  title="Nenhum equipamento encontrado"
                  description="Cadastre equipamentos para controlar disponibilidade operacional."
                />
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-sm shadow-sm">
              <CardHeader>
                <CardTitle>Disponibilidade por equipamento</CardTitle>
                <CardDescription>Visão operacional consolidada de checklist, bloqueios, documentos e manutenção.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Equipamento</TableHead>
                      <TableHead>Status operacional</TableHead>
                      <TableHead>Último checklist</TableHead>
                      <TableHead>Motivo do bloqueio</TableHead>
                      <TableHead>OS aberta</TableHead>
                      <TableHead>Documento vencido</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.equipamentos.map((item) => (
                      <TableRow key={item.equipamento_id}>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="font-medium">{item.equipamento_nome}</div>
                            <div className="text-xs text-muted-foreground">
                              {item.equipamento_tipo} • {item.equipamento_status}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="align-top">
                          <Badge variant="outline" className={getStatusClass(item.status_operacional)}>
                            {STATUS_LABELS[item.status_operacional]}
                          </Badge>
                        </TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">
                          {item.ultimo_checklist_em ? formatDateTime(item.ultimo_checklist_em) : "Sem checklist"}
                        </TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">
                          {item.motivo_status || item.motivo_bloqueio_manual || "—"}
                        </TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">
                          {item.os_aberta ? `${item.os_aberta.numero_os} • ${item.os_aberta.status}` : "—"}
                        </TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">
                          {item.documentos_vencidos.length > 0 ? `${item.documentos_vencidos.length} documento(s)` : "—"}
                        </TableCell>
                        <TableCell className="align-top text-right">
                          <div className="flex justify-end gap-2">
                            <Button asChild variant="ghost" size="sm">
                              <Link href={`/dashboard/operacional/frota/${item.equipamento_id}`}>
                                <Tractor className="size-3.5" />
                                Detalhe
                              </Link>
                            </Button>
                            {item.bloqueado_manual ? (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={liberarMutation.isPending}
                                onClick={() => liberarMutation.mutate(item.equipamento_id)}
                              >
                                <Unlock className="size-3.5" />
                                Liberar
                              </Button>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={bloquearMutation.isPending}
                                onClick={() => bloquearMutation.mutate(item.equipamento_id)}
                              >
                                <Lock className="size-3.5" />
                                Bloquear
                              </Button>
                            )}
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

function ResumoCard({
  title,
  value,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string | number;
  icon: typeof ShieldAlert;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card className={cn("rounded-sm shadow-sm", tone === "warning" && "border-amber-200", tone === "danger" && "border-red-200")}>
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
        </div>
      </CardContent>
    </Card>
  );
}

function DisponibilidadeSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-28 rounded-sm" />
        ))}
      </div>
      <Skeleton className="h-[520px] rounded-sm" />
    </div>
  );
}

function getStatusClass(status: StatusOperacional) {
  switch (status) {
    case "DISPONIVEL":
      return "border-emerald-200 text-emerald-700";
    case "EM_USO":
      return "border-blue-200 text-blue-700";
    case "EM_MANUTENCAO":
    case "CHECKLIST_PENDENTE":
      return "border-amber-200 text-amber-700";
    default:
      return "border-red-200 text-red-700";
  }
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}
