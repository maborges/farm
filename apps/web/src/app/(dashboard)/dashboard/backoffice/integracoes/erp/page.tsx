import Link from "next/link";
import { Activity, ArrowLeftRight, ArrowRightLeft, Database, FileText, PlugZap, ShieldAlert } from "lucide-react";

import { ErpTimeline, type ErpTimelineItem } from "@/components/integracoes/erp-timeline";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetchServer } from "@/lib/api-server";

type ErpStatus = {
  configurado: boolean;
  ativo: boolean;
  ultimo_sync: string | null;
  proximo_sync: string | null;
  status_conexao: string;
  status_canonico?: string | null;
  status_origem: string;
  health_origem: string;
  lifecycle_state?: string | null;
  health_status?: string | null;
  health_summary?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  consecutive_failures: number;
  features_habilitadas: string[];
};

type ErpHealth = {
  origem: string;
  status: string;
  summary?: string | null;
  checked_at?: string | null;
};

type ErpJob = {
  id: string;
  feature_code?: string | null;
  job_status: string;
  trigger_type: string;
  started_at?: string | null;
  finished_at?: string | null;
  processados: number;
  sucessos: number;
  erros: number;
};

type ErpLog = {
  id: number;
  tipo: string;
  operacao: string;
  status: string;
  registros_processados: number;
  registros_sucesso: number;
  registros_erro: number;
  created_at: string;
  origem_dados?: string;
  integration_job_id?: string | null;
  job_status?: string | null;
};

type ErpDiagnosis = {
  origem: string;
  health_atual: string;
  status_degradacao: string;
  ultimo_sucesso_at?: string | null;
  ultima_falha_at?: string | null;
  falhas_consecutivas: number;
  feature_mais_problematica?: string | null;
  jobs_pendentes: number;
  jobs_falhos: number;
  recomendacao_operacional: string;
};

const CONNECTORS = [
  {
    label: "Pessoas",
    description: "Importação e atualização cadastral do ERP.",
  },
  {
    label: "Produtos",
    description: "Catálogo, NCM e atributos fiscais.",
  },
  {
    label: "NFe",
    description: "Documentos fiscais de entrada e saída.",
  },
  {
    label: "Financeiro",
    description: "Lançamentos, baixas e conciliações.",
  },
];

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pt-BR");
}

function formatLabel(value: string | null | undefined) {
  if (!value) return "-";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function badgeVariant(status: string | null | undefined) {
  if (!status) return "secondary" as const;
  if (["CONNECTED", "SUCCESS", "sucesso"].includes(status)) return "default" as const;
  if (["DISCONNECTED", "AUTH_ERROR", "CONFIG_ERROR", "FAILED", "erro"].includes(status)) {
    return "destructive" as const;
  }
  return "secondary" as const;
}

export default async function ErpBridgePage() {
  let status: ErpStatus | null = null;
  let health: ErpHealth | null = null;
  let jobs: ErpJob[] = [];
  let logs: ErpLog[] = [];
  let timeline: ErpTimelineItem[] = [];
  let diagnosis: ErpDiagnosis | null = null;

  try {
    const [
      statusData,
      healthData,
      jobsData,
      logsData,
      timelineData,
      diagnosisData,
    ] = await Promise.all([
      apiFetchServer<ErpStatus>("/integracoes/erp/status"),
      apiFetchServer<ErpHealth>("/integracoes/erp/health"),
      apiFetchServer<ErpJob[]>("/integracoes/erp/jobs?limit=5"),
      apiFetchServer<ErpLog[]>("/integracoes/sankhya/logs?limit=5"),
      apiFetchServer<ErpTimelineItem[]>("/integracoes/erp/timeline?limit=20"),
      apiFetchServer<ErpDiagnosis>("/integracoes/erp/diagnostico"),
    ]);
    status = statusData;
    health = healthData;
    jobs = jobsData;
    logs = logsData;
    timeline = timelineData;
    diagnosis = diagnosisData;
  } catch {
    status = null;
    health = null;
    jobs = [];
    logs = [];
    timeline = [];
    diagnosis = null;
  }

  return (
    <div className="flex flex-col gap-6 p-4 md:p-8">
      <PageHeader
        title="Integrações ERP"
        description="Painel de apoio do backoffice para acompanhar a situação da integração, investigar falhas e orientar o produtor."
        icon={<ArrowLeftRight className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Acompanhamento das Integrações ERP" },
        ]}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-[3px] border-l-primary">
          <CardHeader className="pb-2">
            <CardDescription>Configuração</CardDescription>
            <CardTitle>{status?.configurado ? "Detectada" : "Não detectada"}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-l-[3px] border-l-primary">
          <CardHeader className="pb-2">
            <CardDescription>Situação da integração</CardDescription>
            <CardTitle className="text-base">
              {formatLabel(status?.health_status || health?.status)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-l-[3px] border-l-primary">
          <CardHeader className="pb-2">
            <CardDescription>Último sucesso</CardDescription>
            <CardTitle className="text-base">{formatDateTime(status?.last_success_at)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-l-[3px] border-l-primary">
          <CardHeader className="pb-2">
            <CardDescription>Falhas consecutivas</CardDescription>
            <CardTitle>{status?.consecutive_failures ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowRightLeft className="size-4 text-primary" />
              Funções acompanhadas
            </CardTitle>
            <CardDescription>Funções observadas no ERP conectado do produtor. ERP atual: Sankhya, como provider conectado nesta fase.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {CONNECTORS.map((connector) => (
              <div
                key={connector.label}
                className="flex items-center justify-between gap-4 rounded-sm border bg-muted/20 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{connector.label}</p>
                  <p className="text-xs text-muted-foreground">{connector.description}</p>
                </div>
                <Badge variant="secondary">pronto</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlert className="size-4 text-primary" />
              Governança e suporte
            </CardTitle>
            <CardDescription>O backoffice observa. O produtor configura a integração.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-sm border bg-muted/20 px-3 py-2">
              <div>
                <p className="text-sm font-medium">Origem do status</p>
                <p className="text-xs text-muted-foreground">
                  Indica se a informação veio do fluxo principal da integração ou de um registro legado.
                </p>
              </div>
              <Badge variant="outline">{status?.status_origem || "legacy"}</Badge>
            </div>
            <div className="flex items-center justify-between rounded-sm border bg-muted/20 px-3 py-2">
              <div>
              <p className="text-sm font-medium">Origem da situação</p>
                <p className="text-xs text-muted-foreground">
                  Usa a leitura principal da integração quando disponível, com alternativa segura para compatibilidade.
                </p>
              </div>
              <Badge variant="outline">{health?.origem || status?.health_origem || "legacy"}</Badge>
            </div>
            <div className="rounded-sm border bg-muted/20 px-3 py-3">
              <p className="text-sm font-medium">Governança</p>
              <p className="text-xs text-muted-foreground">
                O backoffice observa, diagnostica e apoia. A configuração principal do ERP do cliente fica na
                Administração do tenant; este painel não substitui o console primário de configuração.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard/settings/integracoes/erp">
                  <PlugZap className="mr-2 size-4" />
                  Abrir console do tenant
                </Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard/settings/integracoes/erp">
                  <FileText className="mr-2 size-4" />
                  Ver operação do tenant
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Diagnóstico para suporte</CardTitle>
          <CardDescription>
            Leitura rápida do estado operacional consolidado para atendimento e suporte.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          <div>
            <p className="text-sm text-muted-foreground">Situação atual</p>
            <Badge variant={badgeVariant(diagnosis?.health_atual)}>
              {formatLabel(diagnosis?.health_atual)}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Degradação</p>
            <p className="font-medium">{formatLabel(diagnosis?.status_degradacao)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Jobs pendentes</p>
            <p className="font-medium">{diagnosis?.jobs_pendentes ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Jobs falhos</p>
            <p className="font-medium">{diagnosis?.jobs_falhos ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Área com mais falhas</p>
            <p className="font-medium">{diagnosis?.feature_mais_problematica || "Nenhuma"}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Última falha</p>
            <p className="font-medium">{formatDateTime(diagnosis?.ultima_falha_at)}</p>
          </div>
          <div className="md:col-span-3 xl:col-span-6">
            <p className="text-sm text-muted-foreground">Recomendação operacional</p>
            <p className="font-medium">{diagnosis?.recomendacao_operacional || "-"}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="size-4 text-primary" />
              Processamentos oficiais
            </CardTitle>
            <CardDescription>Execuções registradas no fluxo principal da integração.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum job recente.</p>
            ) : (
              jobs.map((job) => (
                <div key={job.id} className="rounded-sm border bg-muted/20 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">{job.feature_code || "feature_indefinida"}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(job.started_at)} · origem {job.trigger_type}
                      </p>
                    </div>
                    <Badge variant={badgeVariant(job.job_status)}>{job.job_status}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {job.sucessos}/{job.processados} sucesso · {job.erros} erros
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Histórico complementar</CardTitle>
            <CardDescription>Visão combinada dos registros antigos com os jobs da integração principal.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {logs.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhum log recente encontrado.</p>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="grid gap-2 rounded-sm border bg-muted/20 px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">
                          {log.tipo} / {log.operacao}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDateTime(log.created_at)} · origem {log.origem_dados || "legacy"}
                        </p>
                      </div>
                      <Badge variant={badgeVariant(log.job_status || log.status)}>
                        {log.job_status || log.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {log.registros_sucesso}/{log.registros_processados} processados · {log.registros_erro} erros
                    </p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
        <CardTitle className="text-base">Linha do tempo consolidada</CardTitle>
        <CardDescription>
            Linha do tempo operacional com filtros por situação, origem e área da integração.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ErpTimeline items={timeline} enableFilters />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resumo operacional</CardTitle>
          <CardDescription>Dados úteis para suporte sem expor credenciais do cliente.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div>
            <p className="text-sm text-muted-foreground">Etapa atual</p>
            <p className="font-medium">{formatLabel(status?.lifecycle_state)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Última atualização legada</p>
            <p className="font-medium">{formatDateTime(status?.ultimo_sync)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Funções ativas</p>
            <p className="font-medium">{status?.features_habilitadas?.length || 0}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Resumo da situação</p>
            <p className="font-medium">{status?.health_summary || health?.summary || "-"}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
